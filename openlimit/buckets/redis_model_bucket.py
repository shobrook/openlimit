import time
import redis
from typing import Optional


class RedisModelBucket:
    def __init__(
        self,
        redis_client: redis.Redis,
        prefix: str,
        model: str,
        rate_type: str,
        rate_limit: int,
        bucket_size_in_seconds: int = 60,
    ):
        self.redis: redis.Redis = redis_client
        self.prefix: str = prefix
        self.key: str = f"{prefix}:{model}:{rate_type}"
        self.rate_per_sec: float = rate_limit / bucket_size_in_seconds
        self.max_capacity: float = rate_limit
        self.bucket_size_in_seconds: int = bucket_size_in_seconds

    def get_capacity(self, current_time: Optional[float] = None) -> float:
        if current_time is None:
            current_time = time.time()

        last_checked, capacity = self.redis.mget(
            f"{self.key}:last_checked", f"{self.key}:capacity"
        )

        if last_checked is None or capacity is None:
            self.redis.mset(
                {
                    f"{self.key}:last_checked": current_time,
                    f"{self.key}:capacity": self.max_capacity,
                }
            )
            return self.max_capacity

        last_checked = float(last_checked)
        capacity = float(capacity)

        time_passed: float = current_time - last_checked
        new_capacity: float = min(
            self.max_capacity, capacity + time_passed * self.rate_per_sec
        )

        return new_capacity

    def set_capacity(
        self, new_capacity: float, current_time: Optional[float] = None
    ) -> None:
        if current_time is None:
            current_time = time.time()

        self.redis.mset(
            {
                f"{self.key}:last_checked": current_time,
                f"{self.key}:capacity": max(
                    0, new_capacity
                ),  # Ensure capacity doesn't go negative
            }
        )
