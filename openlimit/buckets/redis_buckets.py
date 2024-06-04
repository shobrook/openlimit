import time
from contextlib import AsyncExitStack, ExitStack
from typing import Optional
import asyncio
import redis
from openlimit.buckets.redis_bucket import RedisBucket


class RedisBuckets(object):
    def __init__(self, buckets: list[RedisBucket], redis: redis.asyncio.Redis) -> None:
        self.buckets = buckets
        self._redis = redis

    async def _lock(self, **kwargs):

        stack = AsyncExitStack()

        for bucket in self.buckets:
            await stack.enter_async_context(bucket._lock(**kwargs))

        return stack

    async def _get_capacities(
        self,
        pipeline: Optional[redis.asyncio.client.Pipeline] = None,
        current_time: Optional[float] = None,
    ):

        if pipeline is None:
            pipeline = self._redis.pipeline()

        if current_time is None:
            current_time = time.time()

        new_capacities = [
            await bucket._get_capacity(pipeline=pipeline, current_time=current_time)
            for bucket in self.buckets
        ]

        return new_capacities

    async def _set_capacities(
        self,
        new_capacities: list[float],
        pipeline: Optional[redis.asyncio.client.Pipeline] = None,
        current_time: Optional[float] = None,
    ):

        if pipeline is None:
            pipeline = self._redis.pipeline()

        if current_time is None:
            current_time = time.time()

        for new_capacity, bucket in zip(new_capacities, self.buckets):

            await bucket._set_capacity(
                new_capacity,
                pipeline=pipeline,
                current_time=current_time,
                execute=False,
            )

        await pipeline.execute()

    async def _has_capacity_async(self, amounts: list[float]):

        # Lock all the buckets
        async with await self._lock(timeout=2):

            # Create the pipeline and current time
            pipeline = self._redis.pipeline()
            current_time = time.time()

            # Get the new capacities
            new_capacities = await self._get_capacities(
                pipeline=pipeline, current_time=current_time
            )

            # Determine if we have sufficient capacity
            has_capacity = min(
                [
                    amount <= new_capacity
                    for amount, new_capacity in zip(amounts, new_capacities)
                ]
            )

            # If there is enough capacity, remove the amount
            if has_capacity:
                new_capacities = [
                    new_capacity - amount
                    for new_capacity, amount in zip(new_capacities, amounts)
                ]

            # Set the new capacities
            await self._set_capacities(
                new_capacities, pipeline=pipeline, current_time=current_time
            )

        return has_capacity

    async def wait_for_capacity(
        self, amounts: list[float], sleep_interval: float = 1e-1
    ):

        while not await self._has_capacity_async(amounts):
            await asyncio.sleep(sleep_interval)

    def wait_for_capacity_sync(
        self, amounts: list[float], sleep_interval: float = 1e-1
    ):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.wait_for_capacity(amounts, sleep_interval=sleep_interval))
