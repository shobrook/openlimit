# Standard library
import asyncio

# Third party
from redis import asyncio as aioredis

# Local
import token_counters as tc
from buckets import Bucket


############
# BASE CLASS
############


class RateLimiter(object):
    def __init__(self, request_limit, token_limit):
        # Rate limits
        self.request_limit = request_limit
        self.token_limit = token_limit

        # Buckets
        self._request_bucket = Bucket(request_limit)
        self._token_bucket = Bucket(token_limit)
    
    async def _multi_acquire(self, num_tokens):
        await asyncio.gather(
            self._request_bucket.acquire(1),
            self._token_bucket.acquire(num_tokens)
        )

        return


######
# MAIN
######


class ChatRateLimiter(RateLimiter):
    async def acquire(self, messages, max_tokens=15, n=1, **kwargs):
        num_tokens = tc.num_tokens_consumed_by_chat_request(messages, max_tokens, n)
        await self._multi_acquire(num_tokens)

        return


class CompletionRateLimiter(RateLimiter):
    async def acquire(self, prompt, max_tokens=15, n=1, **kwargs):
        num_tokens = tc.num_tokens_consumed_by_completion_request(prompt, max_tokens, n)
        await self._multi_acquire(num_tokens)

        return


class EmbeddingRateLimiter(RateLimiter):
    async def acquire(self, input, **kwargs):
        num_tokens = tc.num_tokens_consumed_by_embedding_request(input)
        await self._multi_acquire(num_tokens)

        return