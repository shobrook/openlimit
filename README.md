# openlimit

Efficient rate limiter for the OpenAI API. Implements the [leaky bucket pattern](https://en.wikipedia.org/wiki/Leaky_bucket) to manage both request and token-based rate limits. Features:

- Manage rate limits with one line of code
- Supports synchronous and asynchronous requests
- Supports a Redis backend, which can be used to track limits across multiple threads or processes

## Installation 

You can install openlimit with pip:

```bash
$ pip install openlimit
```

## Usage

openlimit provides rate limiters for the main OpenAI APIs. Applying a rate limit is as simple as adding a `with` statement to your API calls. For example:

```python
from openlimit import ChatRateLimiter

rate_limiter = ChatRateLimiter(request_limit=200, token_limit=40000)
chat_params = { 
    "model": "gpt-4", 
    "messages": [{"role": "user", "content": "Hello!"}]
}

with rate_limiter.acquire(**chat_params):
    response = openai.ChatCompletion.create(**chat_params)
```

Notice that `rate_limiter.acquire` expects the same parameters as the actual API call. openlimit also lets you decorate functions that make API calls, so long as the decorated function is passed the same parameters that are passed to the API call.


```python
@rate_limiter.acquire
def call_gpt4(chat_params):
    response = openai.ChatCompletion.create(**chat_params)
    return response
```

openlimit supports the most popular OpenAI models, and support for secondary models (e.g. Edit & Insert) is coming soon.

| Rate limiter | Supported models |
| --- | --- |
| `ChatRateLimiter` | gpt-4, gpt-4-0314, gpt-4-32k, gpt-4-32k-0314, gpt-3.5-turbo, gpt-3.5-turbo-0301 |
| `CompletionRateLimiter` | text-davinci-003, text-davinci-002, text-curie-001, text-babbage-001, text-ada-001 |
| `EmbeddingRateLimiter` | text-embedding-ada-002 |

### Asynchronous requests

openlimit supports asynchronous requests too.

```python
from openlimit import ChatRateLimiter

rate_limiter = ChatRateLimiter(request_limit=200, token_limit=40000)

async def call_gpt4():
    chat_params = { 
        "model": "gpt-4", 
        "messages": [{"role": "user", "content": "Hello!"}]
    }

    async with rate_limiter.acquire(**chat_params):
        response = await openai.ChatCompletion.acreate(**chat_params)
```

### Distributed requests

By default, openlimit uses an in-memory queue to track rate limits. But if your application is distributed, you can plug in a Redis queue to manage limits across multiple threads or processes.

```python
from openlimit import ChatRateLimiterWithRedis

rate_limiter = ChatRateLimiterWithRedis(
    request_limit=200,
    token_limit=40000,
    redis_url="redis://localhost:5050"
)

# Use `rate_limiter` like you would normally ...
```

## Contributing

If you want to contribute to the library, I recommend learning your way around the codebase with [Adrenaline.](https://useadrenaline.com/) Simply plug in a link to this repository and start asking questions to ramp up.