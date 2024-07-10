import pytest
import redis
import asyncio
import time
from typing import Generator
from concurrent.futures import ThreadPoolExecutor

from openlimit.redis_model_rate_limiter import RedisModelRateLimiter, ModelRateLimit

# Assuming your Redis server is running on localhost:6379
REDIS_URL = "redis://localhost:6379/0"

@pytest.fixture(scope="module")
def redis_client() -> Generator[redis.Redis, None, None]:
    client = redis.from_url(REDIS_URL)
    try:
        client.ping()
    except redis.ConnectionError:
        pytest.skip("Redis server is not available")
    yield client
    # Clean up all keys after tests
    client.flushall()

@pytest.fixture(scope="function")
def rate_limiter(redis_client: redis.Redis) -> RedisModelRateLimiter:
    def token_counter(**kwargs):
        return kwargs.get("tokens", 1)

    return RedisModelRateLimiter(
        redis_url=REDIS_URL,
        prefix="test",
        model_rate_limits={
            "model1": ModelRateLimit(request_limit=100, token_limit=1000),
            "model2": ModelRateLimit(request_limit=50, token_limit=500),
        },
        token_counter=token_counter,
        bucket_size_in_seconds=1,  # Small bucket size for faster testing
        sleep_interval=0.1,  # Smaller sleep interval for faster testing
    )

def test_get_rate_limit(rate_limiter: RedisModelRateLimiter):
    assert rate_limiter.get_rate_limit("model1") == ModelRateLimit(request_limit=10, token_limit=100)
    assert rate_limiter.get_rate_limit("model2") == ModelRateLimit(request_limit=5, token_limit=50)
    with pytest.raises(ValueError):
        rate_limiter.get_rate_limit("non_existent_model")

def test_limit_decorator(rate_limiter: RedisModelRateLimiter):
    @rate_limiter.is_limited()
    def test_function(model: str, tokens: int):
        return f"Called with {model} and {tokens} tokens"

    print("Debug: Before calling test_function")  # Debug print
    result = test_function(model="model1", tokens=10)
    print(f"Debug: After calling test_function, result={result}")  # Debug print
    assert result == "Called with model1 and 10 tokens"

    with pytest.raises(ValueError):
        test_function(tokens=10)  # Missing model parameter

def test_basic_rate_limiting(rate_limiter: RedisModelRateLimiter):
    for _ in range(10):
        rate_limiter.wait_for_capacity_sync(1, "model1")
    
    start_time = time.time()
    rate_limiter.wait_for_capacity_sync(1, "model1")
    elapsed_time = time.time() - start_time
    assert elapsed_time >= 1.0, "Should have waited for at least 1 second"

@pytest.mark.asyncio
async def test_async_rate_limiting(rate_limiter: RedisModelRateLimiter):
    for _ in range(10):
        await rate_limiter.wait_for_capacity(1, "model1")
    
    start_time = time.time()
    await rate_limiter.wait_for_capacity(1, "model1")
    elapsed_time = time.time() - start_time
    assert elapsed_time >= 1.0, "Should have waited for at least 1 second"

def test_token_limiting(rate_limiter: RedisModelRateLimiter):
    rate_limiter.wait_for_capacity_sync(90, "model1")
    
    start_time = time.time()
    rate_limiter.wait_for_capacity_sync(20, "model1")
    elapsed_time = time.time() - start_time
    assert elapsed_time >= 1.0, "Should have waited for at least 1 second"

def test_multiple_models(rate_limiter: RedisModelRateLimiter):
    for _ in range(5):
        rate_limiter.wait_for_capacity_sync(1, "model2")
    
    start_time = time.time()
    rate_limiter.wait_for_capacity_sync(1, "model2")
    elapsed_time = time.time() - start_time
    assert elapsed_time >= 1.0, "Should have waited for at least 1 second"

    # model1 should still have capacity
    rate_limiter.wait_for_capacity_sync(1, "model1")

def test_race_condition(rate_limiter: RedisModelRateLimiter):
    def make_requests():
        for _ in range(20):
            rate_limiter.wait_for_capacity_sync(1, "model1")

    with ThreadPoolExecutor(max_workers=5) as executor:
        start_time = time.time()
        futures = [executor.submit(make_requests) for _ in range(5)]
        for future in futures:
            future.result()
        elapsed_time = time.time() - start_time

    assert 4.0 <= elapsed_time < 5.0, f"Expected time between 4 and 5 seconds, got {elapsed_time}"

@pytest.mark.asyncio
async def test_async_race_condition(rate_limiter: RedisModelRateLimiter):
    async def make_requests():
        for _ in range(20):
            await rate_limiter.wait_for_capacity(1, "model1")

    start_time = time.time()
    await asyncio.gather(*[make_requests() for _ in range(5)])
    elapsed_time = time.time() - start_time

    assert 4.0 <= elapsed_time < 5.0, f"Expected time between 4 and 5 seconds, got {elapsed_time}"

def test_timeout(rate_limiter: RedisModelRateLimiter):
    # Consume all tokens
    rate_limiter.wait_for_capacity_sync(100, "model1")
    
    with pytest.raises(TimeoutError):
        rate_limiter.wait_for_capacity_sync(1, "model1")

@pytest.mark.asyncio
async def test_async_timeout(rate_limiter: RedisModelRateLimiter):
    # Consume all tokens
    await rate_limiter.wait_for_capacity(100, "model1")
    
    with pytest.raises(TimeoutError):
        await rate_limiter.wait_for_capacity(1, "model1")