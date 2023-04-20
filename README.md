# openlimit

Rate limiter for the OpenAI API. Implements the [generic cell rate algorithm,](https://en.wikipedia.org/wiki/Generic_cell_rate_algorithm) an efficient variant of the leaky bucket pattern. 

`openlimit` can:

- Handle both _request_ and _token_ limits
- Apply rate limits with one line of code
- Limit _synchronous_ and _asynchronous_ requests
- Use Redis to track limits across multiple threads or processes

## Installation 

You can install `openlimit` with pip:

```bash
$ pip install openlimit
```

## Usage

Applying a rate limit is as simple as adding a `with` statement to your API calls. For example:

```python
from openlimit import ChatRateLimiter

rate_limiter = ChatRateLimiter(request_limit=200, token_limit=40000)
chat_params = { 
    "model": "gpt-4", 
    "messages": [{"role": "user", "content": "Hello!"}]
}

with rate_limiter.limit(**chat_params):
    response = openai.ChatCompletion.create(**chat_params)
```

Notice that `rate_limiter.limit` expects the same parameters as the actual API call. 

You can also decorate functions that make API calls, so long as the decorated function is passed the same parameters that are passed to the API call.

```python
@rate_limiter.is_limited()
def call_openai(**chat_params):
    response = openai.ChatCompletion.create(**chat_params)
    return response
```

`openlimit` provides different rate limiter classes for different OpenAI models, listed in the table below. Each have the same parameters: `request_limit` and `token_limit`.

| Rate limiter | Supported models |
| --- | --- |
| `ChatRateLimiter` | gpt-4, gpt-4-0314, gpt-4-32k, gpt-4-32k-0314, gpt-3.5-turbo, gpt-3.5-turbo-0301 |
| `CompletionRateLimiter` | text-davinci-003, text-davinci-002, text-curie-001, text-babbage-001, text-ada-001 |
| `EmbeddingRateLimiter` | text-embedding-ada-002 |

### Asynchronous requests

Rate limits can be enforced for asynchronous requests too.

```python
from openlimit import ChatRateLimiter

rate_limiter = ChatRateLimiter(request_limit=200, token_limit=40000)

async def call_openai():
    chat_params = { 
        "model": "gpt-4", 
        "messages": [{"role": "user", "content": "Hello!"}]
    }

    async with rate_limiter.limit(**chat_params):
        response = await openai.ChatCompletion.acreate(**chat_params)
```

### Distributed requests

By default, `openlimit` uses an in-memory store to track rate limits. But if your application is distributed, you can easily plug in a Redis store to manage limits across multiple threads or processes.

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

If you want to contribute to the library, get started with [Adrenaline.](https://useadrenaline.com/) Just paste in a link to this repository to familiarize yourself.