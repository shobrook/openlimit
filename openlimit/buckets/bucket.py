# Standard library
import asyncio
import time


######
# MAIN
######


class Bucket(object):
    def __init__(self, rate_limit):
        # Per-second rate limit
        self._rate_per_sec = rate_limit / 60

        # Capacity of the bucket
        self._capacity = rate_limit / 60

        # Last time the bucket capacity was checked
        self._last_checked = time.time()

    def _has_capacity(self, amount):
        current_time = time.time()
        time_passed = current_time - self._last_checked

        self._last_checked = current_time
        self._capacity += time_passed * self._rate_per_sec

        if self._capacity > self._rate_per_sec:
            self._capacity = self._rate_per_sec
        
        if self._capacity < amount:
            return False
        
        self._capacity -= amount
        return True
    
    async def wait_for_capacity(self, amount):
        while not self._has_capacity(amount):
            await asyncio.sleep(1 / self._rate_per_sec)