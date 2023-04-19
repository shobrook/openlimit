# Standard library
import asyncio


######
# MAIN
######


class Bucket(object):
    def __init__(self, rate_limit):
        # Per-second rate limit
        self._rate_per_sec = rate_limit / 60

        # Capacity of the bucket (e.g. "water level")
        self._level = 0.0

        # Last time the bucket capacity was checked
        self._last_checked = 0.0
    
    def _leak(self):
        loop = asyncio.get_running_loop()

        if self._level:
            elapsed = loop.time() - self._last_checked
            decrement = elapsed * self._rate_per_sec
            self._level = max(self._level - decrement, 0)

        self._last_checked = loop.time()
    
    def _has_capacity(self, amount):
        self._leak()

        requested = self._level + amount

        if requested < self._rate_per_sec:
            self._level += amount
            return True

        return False
    
    async def acquire(self, amount):
        while not self._has_capacity(amount):
            await asyncio.sleep(amount / self._rate_per_sec)

        return