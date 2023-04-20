# Standard library
import asyncio

# Local
import openlimit.utilities.token_counters as tc
import openlimit.utilities.context_decorators as cd
from openlimit.buckets import Bucket


############
# BASE CLASS
############


class RateLimiter(object):
    def __init__(self, request_limit, token_limit, token_counter):
        # Rate limits
        self.request_limit = request_limit
        self.token_limit = token_limit

        # Token counter
        self.token_counter = token_counter

        # Buckets
        self._request_bucket = Bucket(request_limit)
        self._token_bucket = Bucket(token_limit)
    
    async def wait_for_capacity(self, num_tokens):
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


class ChatRateLimiter(RateLimiter):
    def __init__(self, request_limit, token_limit):
        super().__init__(
            request_limit, 
            token_limit, 
            tc.num_tokens_consumed_by_chat_request
        )


class CompletionRateLimiter(RateLimiter):
    def __init__(self, request_limit, token_limit):
        super().__init__(
            request_limit, 
            token_limit, 
            tc.num_tokens_consumed_by_completion_request
        )


class EmbeddingRateLimiter(RateLimiter):
    def __init__(self, request_limit, token_limit):
        super().__init__(
            request_limit, 
            token_limit, 
            tc.num_tokens_consumed_by_embedding_request
        )