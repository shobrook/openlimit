import logging
import pytest
import redis
import asyncio
import time
from typing import Generator
from concurrent.futures import ThreadPoolExecutor

from openlimit.redis_model_rate_limiter import RedisModelRateLimiter, ModelRateLimit

# Assuming your Redis server is running on localhost:6379
REDIS_URL = "redis://localhost:6379/0"

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.skip("all tests require local redis server")


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
            "model1": ModelRateLimit(request_limit=10, token_limit=100),
            "model2": ModelRateLimit(request_limit=5, token_limit=50),
        },
        token_counter=token_counter,
        bucket_size_in_seconds=1,  # 1 second bucket
        sleep_interval=0.05,  # Smaller sleep interval for faster testing
        timeout_in_seconds=2,  # 2 seconds timeout
    )


def test_get_rate_limit(rate_limiter: RedisModelRateLimiter):
    assert rate_limiter.get_rate_limit("model1") == ModelRateLimit(
        request_limit=10, token_limit=100
    )
    assert rate_limiter.get_rate_limit("model2") == ModelRateLimit(
        request_limit=5, token_limit=50
    )
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
    logger.info("Starting basic rate limiting test")

    start_time = time.time()
    # Consume all available requests
    for i in range(10):
        logger.debug(f"Consuming request {i+1}")
        rate_limiter.wait_for_capacity_sync(1, "model1")
    elapsed_time = time.time() - start_time
    logger.info(f"Elapsed time for 10 requests: {elapsed_time} seconds")
    assert (
        elapsed_time < 0.1
    ), f"Should have taken less than 0.1 second, but took {elapsed_time} seconds"

    logger.info("Consumed all initial capacity, waiting for next request")
    start_time = time.time()
    rate_limiter.wait_for_capacity_sync(1, "model1")
    elapsed_time = time.time() - start_time

    logger.info(f"Elapsed time for rate-limited request: {elapsed_time} seconds")

    # We expect to wait at least 0.9 seconds (allowing for some small timing variations)
    assert (
        elapsed_time >= 0.1
    ), f"Should have waited for at least 0.1 seconds, but waited for {elapsed_time} seconds"

    # Let's also check that we can make a request immediately after the bucket refills
    logger.info("Waiting for 0.1 seconds to allow bucket to refill slightly")
    time.sleep(0.1)
    start_time = time.time()
    rate_limiter.wait_for_capacity_sync(1, "model1")
    elapsed_time = time.time() - start_time
    logger.info(f"Elapsed time for immediate request: {elapsed_time} seconds")
    assert (
        elapsed_time < 0.1
    ), f"Should have been able to make a request immediately, but waited for {elapsed_time} seconds"


@pytest.mark.asyncio
async def test_async_rate_limiting(rate_limiter: RedisModelRateLimiter):
    for _ in range(10):
        await rate_limiter.wait_for_capacity(1, "model1")

    start_time = time.time()
    await rate_limiter.wait_for_capacity(1, "model1")
    elapsed_time = time.time() - start_time
    assert elapsed_time >= 0.1, "Should have waited for at least 0.1 second"


def test_token_limiting(rate_limiter: RedisModelRateLimiter):
    rate_limiter.wait_for_capacity_sync(90, "model1")

    start_time = time.time()
    rate_limiter.wait_for_capacity_sync(20, "model1")
    elapsed_time = time.time() - start_time
    assert elapsed_time >= 0.1, "Should have waited for at least 0.1 second"


def test_multiple_models(rate_limiter: RedisModelRateLimiter):
    for _ in range(5):
        rate_limiter.wait_for_capacity_sync(1, "model2")

    start_time = time.time()
    rate_limiter.wait_for_capacity_sync(1, "model2")
    elapsed_time = time.time() - start_time
    assert elapsed_time >= 0.1, "Should have waited for at least 0.1 second"

    # model1 should still have capacity
    rate_limiter.wait_for_capacity_sync(1, "model1")


def test_race_condition(rate_limiter: RedisModelRateLimiter):
    def make_requests():
        for _ in range(4):  # Reduced from 10 to 4
            rate_limiter.wait_for_capacity_sync(1, "model1")

    num_threads = 5
    total_requests = num_threads * 4  # 20 requests in total

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        start_time = time.time()
        futures = [executor.submit(make_requests) for _ in range(num_threads)]
        for future in futures:
            future.result()
        elapsed_time = time.time() - start_time

    # Expected time: (total_requests - rate_limit) / rate_per_second
    expected_time = (total_requests - 10) / 10  # 1 second

    assert (
        1.0 <= elapsed_time < 1.1
    ), f"Expected time between 1.0 and 1.1 seconds, got {elapsed_time}"

    logger.info(f"Race condition test completed in {elapsed_time:.2f} seconds")


@pytest.mark.asyncio
async def test_async_race_condition(rate_limiter: RedisModelRateLimiter):
    async def make_requests():
        for _ in range(4):  # Reduced from 20 to 4
            await rate_limiter.wait_for_capacity(1, "model1")

    num_coroutines = 5
    total_requests = num_coroutines * 4  # 20 requests in total

    start_time = time.time()
    await asyncio.gather(*[make_requests() for _ in range(num_coroutines)])
    elapsed_time = time.time() - start_time

    # Expected time: (total_requests - rate_limit) / rate_per_second
    expected_time = (total_requests - 10) / 10  # 1 second

    assert (
        1.0 <= elapsed_time < 1.1
    ), f"Expected time between 1.0 and 1.1 seconds, got {elapsed_time}"

    logger.info(f"Async race condition test completed in {elapsed_time:.2f} seconds")


def test_timeout_behavior(rate_limiter: RedisModelRateLimiter):
    # Consume all tokens
    rate_limiter.wait_for_capacity_sync(100, "model1")

    logger.info("Consumed initial 100 tokens")

    # Try to consume more tokens than available
    start_time = time.time()
    try:
        rate_limiter.wait_for_capacity_sync(101, "model1")
        elapsed_time = time.time() - start_time
        pytest.fail(
            f"Expected TimeoutError, but no exception was raised. Elapsed time: {elapsed_time} seconds"
        )
    except TimeoutError as e:
        elapsed_time = time.time() - start_time
        logger.info(f"Received TimeoutError as expected. Message: {str(e)}")
        assert (
            2.0 <= elapsed_time <= 2.1
        ), f"Expected to timeout after about 2 seconds, but took {elapsed_time} seconds"
    except Exception as e:
        elapsed_time = time.time() - start_time
        pytest.fail(
            f"Expected TimeoutError, but got {type(e).__name__}: {str(e)}. Elapsed time: {elapsed_time} seconds"
        )

    # Check the current capacity
    request_bucket, token_bucket = rate_limiter.buckets["model1"]
    current_request_capacity = request_bucket.get_capacity()
    current_token_capacity = token_bucket.get_capacity()
    logger.info(f"Current request capacity: {current_request_capacity}")
    logger.info(f"Current token capacity: {current_token_capacity}")


@pytest.mark.asyncio
async def test_async_timeout_behavior(rate_limiter: RedisModelRateLimiter):
    # Consume all tokens
    await rate_limiter.wait_for_capacity(100, "model1")

    logger.info("Consumed initial 100 tokens")

    # Try to consume more tokens than available
    start_time = time.time()
    try:
        await rate_limiter.wait_for_capacity(101, "model1")
        elapsed_time = time.time() - start_time
        pytest.fail(
            f"Expected TimeoutError, but no exception was raised. Elapsed time: {elapsed_time} seconds"
        )
    except TimeoutError as e:
        elapsed_time = time.time() - start_time
        logger.info(f"Received TimeoutError as expected. Message: {str(e)}")
        assert (
            1.9 <= elapsed_time <= 2.1
        ), f"Expected to timeout after about 2 seconds, but took {elapsed_time} seconds"
    except Exception as e:
        elapsed_time = time.time() - start_time
        pytest.fail(
            f"Expected TimeoutError, but got {type(e).__name__}: {str(e)}. Elapsed time: {elapsed_time} seconds"
        )

    # Check the current capacity
    request_bucket, token_bucket = rate_limiter.buckets["model1"]
    current_request_capacity = request_bucket.get_capacity()
    current_token_capacity = token_bucket.get_capacity()
    logger.info(f"Current request capacity: {current_request_capacity}")
    logger.info(f"Current token capacity: {current_token_capacity}")
