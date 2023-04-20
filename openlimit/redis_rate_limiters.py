# Standard library
import asyncio

# Third party
from redis import asyncio as aioredis

# Local
import openlimit.utilities.token_counters as tc
import openlimit.utilities.context_decorators as cd
from openlimit.buckets import RedisBucket


############
# BASE CLASS
############


class RateLimiterWithRedis(object):
    def __init__(self, request_limit, token_limit, token_counter, bucket_key, redis_url="redis://localhost:5050"):
        # Rate limits
        self.request_limit = request_limit
        self.token_limit = token_limit

        # Token counter
        self.token_counter = token_counter

        # Redis
        self._redis_url = redis_url

        # Buckets
        self._request_bucket = None
        self._token_bucket = None

        # Bucket prefix (for Redis)
        self._bucket_key = bucket_key
    
    async def _init_buckets(self):
        if self._request_bucket and self._token_bucket:
            return

        redis = await aioredis.from_url(self._redis_url, encoding="utf-8", decode_responses=True)

        self._request_bucket = RedisBucket(
            self.request_limit,
            bucket_key=f"{self._bucket_key}_requests",
            redis=redis
        )
        self._token_bucket = RedisBucket(
            self.token_limit,
            bucket_key=f"{self._bucket_key}_tokens",
            redis=redis
        )
    
    async def wait_for_capacity(self, num_tokens):
        await self._init_buckets()
        await asyncio.gather(
            self._request_bucket.wait_for_capacity(1),
            self._token_bucket.wait_for_capacity(num_tokens)
        )
    
    def limit(self, **kwargs):
        num_tokens = self.token_counter(**kwargs)
        return cd.AsyncContextManager(num_tokens, self)
    
    def is_limited(self):
        return cd.FunctionDecorator(self)


######
# MAIN
######


class ChatRateLimiterWithRedis(RateLimiterWithRedis):
    def __init__(self, request_limit, token_limit, redis_url="redis://localhost:5050"):
        super().__init__(
            request_limit, 
            token_limit, 
            tc.num_tokens_consumed_by_chat_request,
            "chat", 
            redis_url
        )


class CompletionRateLimiterWithRedis(RateLimiterWithRedis):
    def __init__(self, request_limit, token_limit, redis_url="redis://localhost:5050"):
        super().__init__(
            request_limit, 
            token_limit, 
            tc.num_tokens_consumed_by_completion_request,
            "completion", 
            redis_url
        )


class EmbeddingRateLimiterWithRedis(RateLimiterWithRedis):
    def __init__(self, request_limit, token_limit, redis_url="redis://localhost:5050"):
        super().__init__(
            request_limit, 
            token_limit, 
            tc.num_tokens_consumed_by_embedding_request,
            "embedding", 
            redis_url
        )