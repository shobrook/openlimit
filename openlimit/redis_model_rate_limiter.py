import asyncio
from dataclasses import dataclass
import time
from typing import Callable, Dict, List
import redis

from openlimit.buckets.redis_model_bucket import RedisModelBucket
import openlimit.utilities as utils
from openlimit.redis_lock import RedisLock

@dataclass
class ModelRateLimit:
    request_limit: int
    token_limit: int

class RedisModelRateLimiter:
    def __init__(
        self,
        redis_url: str,
        prefix: str,
        model_rate_limits: Dict[str, ModelRateLimit],
        token_counter: Callable,
        bucket_size_in_seconds: int = 60,
        sleep_interval: float = 1,
    ):
        self.redis: redis.Redis = redis.from_url(redis_url)
        self.prefix: str = prefix
        self.model_rate_limits: Dict[str, ModelRateLimit] = model_rate_limits
        self.token_counter: Callable = token_counter
        self.bucket_size_in_seconds: int = bucket_size_in_seconds
        self.sleep_interval: float = sleep_interval
        self.buckets: Dict[str, List[RedisModelBucket]] = {
            model: [
                RedisModelBucket(self.redis, self.prefix, model, "request", rate_limit.request_limit, bucket_size_in_seconds),
                RedisModelBucket(self.redis, self.prefix, model, "token", rate_limit.token_limit, bucket_size_in_seconds),
            ]
            for model, rate_limit in model_rate_limits.items()
        }

    def get_rate_limit(self, model: str) -> ModelRateLimit:
        if model not in self.model_rate_limits:
            raise ValueError(f"Rate limit not defined for model: {model}")
        return self.model_rate_limits[model]

    def limit(self, **kwargs) -> utils.ModelContextManager:
        model: str = kwargs.get("model")
        if model is None:
            raise ValueError("Model name not provided in function parameters")
        num_tokens: int = self.token_counter(**kwargs)
        return utils.ModelContextManager(num_tokens, model, self)

    def is_limited(self) -> utils.FunctionDecorator:
        return utils.FunctionDecorator(self)

    async def wait_for_capacity(self, num_tokens: int, model: str) -> None:
        request_bucket, token_bucket = self.buckets[model]
        start_time: float = time.time()
        timeout: int = 120  # Timeout after 2 minutes
        while True:
            current_time: float = time.time()
            if current_time - start_time > timeout:
                raise TimeoutError("Timed out while waiting for capacity")

            with RedisLock(self.redis, f"{self.prefix}:{model}:rate_limit_lock", expire_time=5):
                request_capacity: float = request_bucket.get_capacity(current_time)
                token_capacity: float = token_bucket.get_capacity(current_time)

                if request_capacity >= 1 and token_capacity >= num_tokens:
                    request_bucket.set_capacity(request_capacity - 1, current_time)
                    token_bucket.set_capacity(token_capacity - num_tokens, current_time)
                    break
            await asyncio.sleep(self.sleep_interval)

    def wait_for_capacity_sync(self, num_tokens: int, model: str) -> None:
        request_bucket, token_bucket = self.buckets[model]
        start_time: float = time.time()
        timeout: int = 10  # Reduce timeout to 10 seconds for testing
        while True:
            current_time: float = time.time()

            if current_time - start_time > timeout:
                raise TimeoutError("Timed out while waiting for capacity")

            with RedisLock(self.redis, f"{self.prefix}:{model}:rate_limit_lock", expire_time=5):
                request_capacity: float = request_bucket.get_capacity(current_time)
                token_capacity: float = token_bucket.get_capacity(current_time)
                print(f"Debug: request_capacity={request_capacity}, token_capacity={token_capacity}, num_tokens={num_tokens}")  # Debug print

                if request_capacity >= 1 and token_capacity >= num_tokens:
                    request_bucket.set_capacity(request_capacity - 1, current_time)
                    token_bucket.set_capacity(token_capacity - num_tokens, current_time)
                    break
            print(f'No tokens available, sleeping for {self.sleep_interval}')
            time.sleep(self.sleep_interval)
