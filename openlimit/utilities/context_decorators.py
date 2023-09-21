# Standard library
import asyncio
from functools import wraps
from inspect import iscoroutinefunction

######
# MAIN
######


class FunctionDecorator(object):
    """
    Converts rate limiter into a function decorator.
    """

    def __init__(self, rate_limiter):
        self.rate_limiter = rate_limiter

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self.rate_limiter.limit(**kwargs):
                return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            async with self.rate_limiter.limit(**kwargs):
                return await func(*args, **kwargs)

        # Return either an async or normal wrapper, depending on the type of the wrapped function
        return async_wrapper if iscoroutinefunction(func) else wrapper


class ContextManager(object):
    """
    Converts rate limiter into context manager.
    """

    def __init__(self, num_tokens, rate_limiter):
        self.num_tokens = num_tokens
        self.rate_limiter = rate_limiter

    def __enter__(self):
        self.rate_limiter.wait_for_capacity_sync(self.num_tokens)

    def __exit__(self, *exc):
        return False

    async def __aenter__(self):
        await self.rate_limiter.wait_for_capacity(self.num_tokens)

    async def __aexit__(self, *exc):
        return False
