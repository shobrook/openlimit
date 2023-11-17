# Standard library
import asyncio
import time
from typing import Optional

from openlimit.buckets.bucket import Bucket

######
# MAIN
######


class Buckets(object):
    def __init__(self, buckets: list[Bucket]) -> None:
        self.buckets = buckets

    def _get_capacities(
        self,
        current_time: Optional[float] = None,
    ):

        if current_time is None:
            current_time = time.time()

        new_capacities = [
            bucket._get_capacity(current_time=current_time) for bucket in self.buckets
        ]

        return new_capacities

    def _set_capacities(
        self,
        new_capacities: list[float],
        current_time: Optional[float] = None,
    ):

        if current_time is None:
            current_time = time.time()

        for new_capacity, bucket in zip(new_capacities, self.buckets):

            bucket._set_capacity(
                new_capacity,
                current_time=current_time,
            )

    def _has_capacity(self, amounts: list[float]):

        # Create the current time
        current_time = time.time()

        # Get the new capacities
        new_capacities = self._get_capacities(current_time=current_time)

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
        self._set_capacities(new_capacities, current_time=current_time)

        return has_capacity

    def wait_for_capacity_sync(
        self, amounts: list[float], sleep_interval: float = 1e-1
    ):

        while not self._has_capacity(amounts):
            time.sleep(sleep_interval)

    async def wait_for_capacity(
        self, amounts: list[float], sleep_interval: float = 1e-1
    ):

        while not self._has_capacity(amounts):
            await asyncio.sleep(sleep_interval)
