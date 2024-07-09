import asyncio
from dataclasses import dataclass
import time
from typing import Callable

# Local
from openlimit.buckets import ModelBucket
import openlimit.utilities as utils

# Rate limit per model
@dataclass
class ModelRateLimit:
    request_limit: int
    token_limit: int

############
# BASE CLASS
############

class ModelRateLimiter:
    def __init__(
        self,
        model_rate_limits: dict[str, ModelRateLimit],
        token_counter: Callable,
        bucket_size_in_seconds: int = 60,
        sleep_interval: float = 1,
    ):
        self.model_rate_limits = model_rate_limits
        self.token_counter = token_counter
        self.bucket_size_in_seconds = bucket_size_in_seconds
        self.sleep_interval = sleep_interval
        self.buckets = {
            model: [
                ModelBucket(rate_limit.request_limit, bucket_size_in_seconds),
                ModelBucket(rate_limit.token_limit, bucket_size_in_seconds),
            ]
            for model, rate_limit in model_rate_limits.items()
        }

    def get_rate_limit(self, model: str):
        if model not in self.model_rate_limits:
            raise ValueError(f"Rate limit not defined for model: {model}")
        return self.model_rate_limits[model]

    def limit(self, **kwargs):
        model = kwargs.get("model")
        if model is None:
            raise ValueError("Model name not provided in function parameters")
        num_tokens = self.token_counter(**kwargs)
        return utils.ModelContextManager(num_tokens, model, self)

    def is_limited(self):
        return utils.FunctionDecorator(self)

    async def wait_for_capacity(self, num_tokens, model):
        request_bucket, token_bucket = self.buckets[model]
        start_time = time.time()
        timeout = 10  # Timeout after 10 seconds
        while True:
            current_time = time.time()
            if current_time - start_time > timeout:
                raise TimeoutError("Timed out while waiting for capacity")

            # Acquire the locks for both buckets in a consistent order
            with request_bucket.lock, token_bucket.lock:
                request_capacity = request_bucket.get_capacity(current_time)
                token_capacity = token_bucket.get_capacity(current_time)

                if request_capacity >= 1 and token_capacity >= num_tokens:
                    request_bucket.set_capacity(request_capacity - 1, current_time)
                    token_bucket.set_capacity(token_capacity - num_tokens, current_time)
                    break
            await asyncio.sleep(self.sleep_interval)

    def wait_for_capacity_sync(self, num_tokens, model):
        request_bucket, token_bucket = self.buckets[model]
        start_time = time.time()
        timeout = 120  # Timeout after 2 minutes
        while True:
            current_time = time.time()

            if current_time - start_time > timeout:
                raise TimeoutError("Timed out while waiting for capacity")

            # Acquire the locks for both buckets in a consistent order
            with request_bucket.lock, token_bucket.lock:
                request_capacity = request_bucket.get_capacity(current_time)
                token_capacity = token_bucket.get_capacity(current_time)
                if request_capacity >= 1 and token_capacity >= num_tokens:
                    request_bucket.set_capacity(request_capacity - 1, current_time)
                    token_bucket.set_capacity(token_capacity - num_tokens, current_time)
                    break
            print(f'No tokens available, sleeping for {self.sleep_interval}')
            time.sleep(self.sleep_interval)
