# Standard library
import time
import threading

######
# MAIN
######


class ModelBucket:
    def __init__(self, rate_limit, bucket_size_in_seconds: int = 60, last_checked = time.time()):
        self.rate_per_sec = rate_limit / 60
        self.capacity = rate_limit * bucket_size_in_seconds / 60
        self.bucket_size_in_seconds = bucket_size_in_seconds
        self.last_checked = last_checked or time.time()
        self.lock = threading.Lock()
        print(f"Rate per sec: {self.rate_per_sec}, Capacity: {self.capacity}")

    def get_capacity(self, current_time: float = None) -> float:
        # Assuming the caller has already acquired the lock
        if current_time is None:
            current_time = time.time()
        time_passed = current_time - self.last_checked
        new_capacity = min(
            self.rate_per_sec * self.bucket_size_in_seconds,
            self.capacity + time_passed * self.rate_per_sec,
        )
        return new_capacity

    def set_capacity(self, new_capacity: float, current_time: float = None) -> None:
        # Assuming the caller has already acquired the lock
        self.last_checked = current_time or time.time()
        self.capacity = new_capacity
