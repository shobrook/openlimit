# Standard library
import asyncio


######
# MAIN
######


class RedisBucket(object):
    def __init__(self, rate_limit, bucket_key, redis):
        # Per-second rate limit
        self._rate_per_sec = rate_limit / 60

        # Redis bucket keys
        self._level_key = f"{bucket_key}_level"
        self._last_checked_key = f"{bucket_key}_last_checked"

        # Redis connection
        self._redis = redis
    
    async def _leak(self):
        current_level = float(await self._redis.get(self._level_key) or 0)
        last_checked = float(await self._redis.get(self._last_checked_key) or 0)

        loop = asyncio.get_running_loop()

        if current_level:
            elapsed = loop.time() - last_checked
            decrement = elapsed * self._rate_per_sec
            new_level = max(current_level - decrement, 0)

            await self._redis.set(self._level_key, new_level)

        await self._redis.set(self._last_checked_key, loop.time())
    
    async def _has_capacity(self, amount):
        await self._leak()

        current_level = float(await self._redis.get(self._level_key) or 0)
        requested = current_level + amount

        if requested < self._rate_per_sec:
            new_level = current_level + amount
            await self._redis.set(self._level_key, new_level)

            return True

        return False
    
    async def acquire(self, amount):
        while not await self._has_capacity(amount):
            await asyncio.sleep(amount / self._rate_per_sec)

        return