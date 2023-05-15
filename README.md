# openlimitHW

简单高效的 OpenAI API 速率限制器。它可以：

- 处理 _请求_ 和 _令牌_ 限制
- 用一行代码精确地执行速率限制
- 限制 _同步_ 和 _异步_ 请求
- 使用 Redis 跨多个线程或进程跟踪限制

## 安装

您可以使用 pip 安装 `openlimitHW`：

```bash
$ pip install openlimitHW
```

## 使用

### 定义速率限制

首先，为您使用的 OpenAI 模型定义速率限制。例如：

```python
from openlimit import ChatRateLimiter

rate_limiter = ChatRateLimiter(request_limit=20, token_limit=4000*20)
```
这为chat completion model（例如 gpt-4，gpt-3.5-turbo）设置了速率限制。`openlimit` 提供了不同的速率限制器对象，用于不同的 OpenAI 模型，所有对象都具有相同的参数：`request_limit` 和 `token_limit`。两种限制都是 每分钟 的量，可能因用户而异。

| Rate limiter | Supported models |
| --- | --- |
| `ChatRateLimiter` | gpt-4, gpt-4-0314, gpt-4-32k, gpt-4-32k-0314, gpt-3.5-turbo, gpt-3.5-turbo-0301 |
| `CompletionRateLimiter` | text-davinci-003, text-davinci-002, text-curie-001, text-babbage-001, text-ada-001 |
| `EmbeddingRateLimiter` | text-embedding-ada-002 |

### 应用速率限制

要应用速率限制，请在您的 API 调用中添加一个 `with` 语句：

```python
chat_params = { 
    "model": "gpt-4", 
    "messages": [{"role": "user", "content": "Hello!"}]
}

with rate_limiter.limit(**chat_params):
    response = openai.ChatCompletion.create(**chat_params)
```

确保 `rate_limiter.limit` 接收与实际 API 调用相同的参数。这对于计算预期的令牌使用量很重要。

或者，您可以装饰执行 API 调用的函数，只要被装饰的函数接收与 API 调用相同的参数：

```python
@rate_limiter.is_limited()
def call_openai(**chat_params):
    response = openai.ChatCompletion.create(**chat_params)
    return response
```

### 异步请求

速率限制也可以用于异步请求：

```python
async def call_openai():
    chat_params = { 
        "model": "gpt-4", 
        "messages": [{"role": "user", "content": "Hello!"}]
    }

    async with rate_limiter.limit(**chat_params):
        response = await openai.ChatCompletion.acreate(**chat_params)
```

### 分布式请求

默认情况下，`openlimit` 使用内存存储来跟踪速率限制。但是如果您的应用程序是分布式的，您可以轻松地插入一个 Redis 存储来管理跨多个线程或进程的限制。

```python
from openlimit import ChatRateLimiterWithRedis

rate_limiter = ChatRateLimiterWithRedis(
    request_limit=20,
    token_limit=4000*20,
    redis_url="redis://localhost:5050"
)

# 像平常一样使用 `rate_limiter` ...
```
所有 `RateLimiter` 对象都有 `RateLimiterWithRedis` 对应物。

## 贡献
如果您想为库做出贡献，请从[Adrenaline](https://useadrenaline.com/) 开始。只需将此存储库的链接粘贴到 Web 翻译器中，即可。