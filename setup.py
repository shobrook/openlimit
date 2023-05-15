import sys
from setuptools import setup

setup(
    name="openlimitHW",
    description="Rate limiter for the OpenAI API (modified by HW)",
    version="v0.3.0",
    packages=["openlimit", "openlimit.utilities", "openlimit.buckets"],
    python_requires=">=3",
    url="https://github.com/williamxhero/openlimitHW",
    author="williamxhero",
    author_email="williamxhero@gmail.com",
    # classifiers=[],
    install_requires=["redis", "tiktoken"],
    keywords=["openai", "rate-limit", "limit", "api", "request", "token", "leaky-bucket", "gcra", "redis", "asyncio"],
    license="MIT"
)
