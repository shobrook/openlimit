# Standard library
import asyncio
import time
import typing

# Third party
import redis
######
# MAIN
######


class RedisBucket(object):
    def __init__(
        self,
        rate_limit,
        bucket_key,
        redis: redis.asyncio.Redis,
        bucket_size_in_seconds: float = 1,
    ):
        # Per-second rate limit
        self._rate_per_sec = rate_limit / 60

        # The integration time of the bucket
        self._bucket_size_in_seconds = bucket_size_in_seconds

        # Redis
        self._redis = redis
        self._bucket_key = bucket_key

    def _lock(self, **kwargs):

        return redis.asyncio.lock.Lock(self._redis, f"{self._bucket_key}:lock", **kwargs)

    async def _get_capacity(
        self,
        pipeline: typing.Optional[redis.asyncio.client.Pipeline] = None,
        current_time: typing.Optional[float] = None,
    ):

        if pipeline is None:
            pipeline = self._redis.pipeline()

        pipeline.get(f"{self._bucket_key}:last_checked")
        pipeline.get(f"{self._bucket_key}:capacity")

        if current_time is None:
            current_time = asyncio.get_event_loop().time()

        last_checked, capacity = await pipeline.execute()

        if not last_checked or not capacity:
            last_checked = current_time
            capacity = self._rate_per_sec * self._bucket_size_in_seconds

        time_passed = current_time - float(last_checked)
        new_capacity = min(
            self._rate_per_sec * self._bucket_size_in_seconds,
            float(capacity) + time_passed * self._rate_per_sec,
        )

        return new_capacity

    async def _set_capacity(
        self,
        new_capacity: float,
        pipeline: typing.Optional[redis.asyncio.client.Pipeline] = None,
        current_time: typing.Optional[float] = None,
        execute: bool = True,
    ):

        if pipeline is None:
            pipeline = self._redis.pipeline()

        if current_time is None:
            current_time = asyncio.get_event_loop().time()

        pipeline.set(f"{self._bucket_key}:last_checked", current_time)
        pipeline.set(f"{self._bucket_key}:capacity", new_capacity)

        if execute:
            await pipeline.execute()
