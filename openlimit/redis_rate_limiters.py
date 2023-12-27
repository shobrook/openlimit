# Standard library
import asyncio

# Third party
import redis

# Local
import openlimit.utilities as utils
from openlimit.buckets import RedisBucket, RedisBuckets

############
# BASE CLASS
############


class RateLimiterWithRedis(object):
    def __init__(
        self,
        request_limit,
        token_limit,
        token_counter,
        bucket_key,
        redis_url="redis://localhost:5050",
        bucket_size_in_seconds: float = 1,
    ):
        # Rate limits
        self.request_limit = request_limit
        self.token_limit = token_limit
        self.sleep_interval = 1 / (self.request_limit / 60)

        # Token counter
        self.token_counter = token_counter

        # Redis
        self._redis_url = redis_url

        # Bucket size in seconds
        self._bucket_size_in_seconds = bucket_size_in_seconds

        # Buckets
        self._buckets = None

        # Bucket prefix (for Redis)
        self._bucket_key = bucket_key

    async def _init_buckets(self):
        if self._buckets:
            return

        db = await redis.asyncio.from_url(
            self._redis_url, encoding="utf-8", decode_responses=True
        )

        self._buckets = RedisBuckets(
            redis=db,
            buckets=[
                RedisBucket(
                    self.request_limit,
                    bucket_key=f"{self._bucket_key}_requests",
                    redis=db,
                    bucket_size_in_seconds=self._bucket_size_in_seconds,
                ),
                RedisBucket(
                    self.token_limit,
                    bucket_key=f"{self._bucket_key}_tokens",
                    redis=db,
                    bucket_size_in_seconds=self._bucket_size_in_seconds,
                ),
            ],
        )

    async def wait_for_capacity(self, num_tokens):
        await self._init_buckets()
        await self._buckets.wait_for_capacity(
            amounts=[1, num_tokens], sleep_interval=self.sleep_interval
        )

    def limit(self, **kwargs):
        num_tokens = self.token_counter(**kwargs)
        return utils.ContextManager(num_tokens, self)

    def is_limited(self):
        return utils.FunctionDecorator(self)


######
# MAIN
######


class ChatRateLimiterWithRedis(RateLimiterWithRedis):
    def __init__(
        self,
        request_limit=3500,
        token_limit=90000,
        redis_url="redis://localhost:5050",
        bucket_size_in_seconds: float = 1,
        bucket_key="chat",
    ):
        super().__init__(
            request_limit=request_limit,
            token_limit=token_limit,
            token_counter=utils.num_tokens_consumed_by_chat_request,
            bucket_key=bucket_key,
            redis_url=redis_url,
            bucket_size_in_seconds=bucket_size_in_seconds,
        )


class CompletionRateLimiterWithRedis(RateLimiterWithRedis):
    def __init__(
        self,
        request_limit=3500,
        token_limit=350000,
        redis_url="redis://localhost:5050",
        bucket_size_in_seconds: float = 1,
        bucket_key="completion",
    ):
        super().__init__(
            request_limit=request_limit,
            token_limit=token_limit,
            token_counter=utils.num_tokens_consumed_by_completion_request,
            bucket_key=bucket_key,
            redis_url=redis_url,
            bucket_size_in_seconds=bucket_size_in_seconds,
        )


class EmbeddingRateLimiterWithRedis(RateLimiterWithRedis):
    def __init__(
        self,
        request_limit=3500,
        token_limit=70000000,
        redis_url="redis://localhost:5050",
        bucket_size_in_seconds: float = 1,
        bucket_key="embedding",
    ):
        super().__init__(
            request_limit=request_limit,
            token_limit=token_limit,
            token_counter=utils.num_tokens_consumed_by_embedding_request,
            bucket_key=bucket_key,
            redis_url=redis_url,
            bucket_size_in_seconds=bucket_size_in_seconds,
        )
