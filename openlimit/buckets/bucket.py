# Standard library
import asyncio
import time


######
# MAIN
######


class Bucket(object):
    def __init__(self, rate_limit):
        # once Per-minute
        self._sec_per_tick = 60 / rate_limit
        # Last time the bucket capacity was checked
        self._last_checked = time.time()
        self._last_amount = 0

    def _has_capacity(self, amount):
        current_time = time.time()
        time_passed = current_time - self._last_checked

        if time_passed > (self._sec_per_tick * self._last_amount):
            self._last_checked = current_time
            self._last_amount = amount
            return True
        
        return False
    
    async def wait_for_capacity(self, amount):
        while not self._has_capacity(amount):
            await asyncio.sleep(1 / self._sec_per_tick)