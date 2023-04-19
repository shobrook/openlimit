# Standard library
import asyncio
from contextlib import AbstractAsyncContextManager
from math import ceil


######
# MAIN
######


class RequestsBucket(AbstractAsyncContextManager):
    """
    A leaky bucket for handling request rate limits.

    Parameters:
    -----------
    request_limit : int
        Number of requests allowed within a minute
    """

    def __init__(self, request_limit=3500):
        self.request_limit = request_limit

        # Per-second rate limit
        self._rate_per_sec = ceil(request_limit / 60)
        
        # "Water level" (i.e. how full the bucket is)
        self._level = 0.0
        
        # When we last checked the capacity of the bucket
        self._last_checked = 0.0
        
        # Maps queued tasks to futures to signal capacity to
        self._task_to_future = {}

    def _leak(self):
        """
        "Leaks" out capacity from the bucket. Called whenever we check if the 
        bucket has capacity for another request.
        """

        loop = asyncio.get_running_loop()
        if self._level:
            elapsed = loop.time() - self._last_checked
            decrement = elapsed * self._rate_per_sec
            self._level = max(self._level - decrement, 0)

        self._last_checked = loop.time()

    def _has_capacity(self):
        """
        Checks if there's enough capacity in the bucket for a request.
        """

        self._leak()
        requested = self._level + 1

        if requested < self.rate_per_sec: # Bucket has capacity
            for future in self._task_to_future.values():
                if not future.done():
                    # Tell first task in queue that capacity is available
                    future.set_result(True)
                    break

        return requested <= self.rate_per_sec

    async def acquire(self):
        """
        Acquires capacity in the bucket. If the bucket is full, this blocks until
        enough capacity has been freed.
        """

        loop = asyncio.get_running_loop()
        task = asyncio.current_task(loop)

        assert task is not None

        while not self._has_capacity():
            # wait for the next drip to have left the bucket
            # add a future to the _task_to_future map to be notified
            # 'early' if capacity has come up

            future = loop.create_future()
            self._task_to_future[task] = future

            try:
                await asyncio.wait_for(
                    asyncio.shield(future), 
                    1 / self._rate_per_sec, 
                    loop=loop
                )
            except asyncio.TimeoutError:
                pass

            future.cancel()

        self._task_to_future.pop(task, None)
        self._level += 1

        return None

    async def __aenter__(self):
        return await self.acquire()

    async def __aexit__(self, exc_type, exc, tb):
        return None