# Standard library
import asyncio
from contextlib import AbstractAsyncContextManager
from math import ceil

# Third party
import aioredis


######
# MAIN
######


class RedisRequestsBucket(AbstractAsyncContextManager):
    """
    A leaky bucket for handling request rate limits using Redis.

    Parameters:
    -----------
    request_limit : int
        Number of requests allowed within a minute
    redis_url : str
        Redis server URL
    redis_key : str
        Redis key to store the bucket level
    """

    def __init__(self, request_limit=3500, redis_url="redis://localhost:6379"):
        self.request_limit = request_limit

        self._level_key = "requests_level"
        self._last_checked_key = "requests_last_checked"

        self._rate_per_sec = ceil(request_limit / 60)
        self._redis_url = redis_url
        self._redis_key = redis_key
        self._redis = None

    async def _get_redis(self):
        if not self._redis:
            self._redis = await aioredis.create_redis_pool(self._redis_url)

        return self._redis

    async def _leak(self):
        redis = await self._get_redis()
        current_level = float(await redis.get(self._level_key) or 0)
        last_checked = float(await redis.get(self._last_checked_key) or 0)

        if current_level:
            elapsed = asyncio.get_running_loop().time() - last_checked
            decrement = elapsed * self._rate_per_sec
            new_level = max(current_level - decrement, 0)

            await redis.set(self._redis_key, new_level)

        await redis.set(self._last_checked_key, asyncio.get_running_loop().time())

    async def _has_capacity(self):
        await self._leak()

        redis = await self._get_redis()
        current_level = float(await redis.get(self._level_key) or 0)
        requested = current_level + 1

        if requested < self._rate_per_sec:
            new_level = current_level + 1
            await redis.set(self._level_key, new_level)

            return True

        return False

    async def acquire(self):
        while not await self._has_capacity():
            await asyncio.sleep(1 / self._rate_per_sec)

        return None

    async def __aenter__(self):
        return await self.acquire()

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def close(self):
        if self._redis:
            self._redis.close()
            await self._redis.wait_closed()
