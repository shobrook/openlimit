import time

import asyncio
import pytest

from openlimit import ChatRateLimiterWithRedis

@pytest.fixture(scope="module")
def chat_params():
    return {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Who won the world series in 2020?"}
        ],
        "max_tokens": 1,
        "n": 1
    }

@pytest.mark.asyncio
async def test_rate_limiter_with_redis(chat_params):
    rate_limiter_async = ChatRateLimiterWithRedis(
        request_limit=200,
        token_limit=4000,
        redis_url="redis://localhost:6379"  # Update this to your Redis URL
    )

    async def rate_limited_function_async(**chat_params):
        async with rate_limiter_async.limit(**chat_params):
            return "success"

    start_time = asyncio.get_event_loop().time()
    duration = 5  # seconds
    successful_calls = 0

    while (asyncio.get_event_loop().time() - start_time) < duration:
        result = await rate_limited_function_async(**chat_params)
        if result == "success":
            successful_calls += 1

    # Check if the number of successful calls is within the rate limits
    assert 0 < successful_calls <= rate_limiter_async.request_limit * (duration / 60)