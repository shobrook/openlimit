from unittest.mock import patch

import pytest
from openlimit.buckets.model_bucket import ModelBucket


def test_model_bucket_initial_capacity():
    rate_limit_per_minute = 1200
    bucket_size_in_seconds = 600
    bucket = ModelBucket(rate_limit=rate_limit_per_minute, bucket_size_in_seconds=bucket_size_in_seconds)
    assert bucket.get_capacity() == rate_limit_per_minute / 60 * bucket_size_in_seconds

def test_model_bucket_set_capacity():
    simulated_timestamp = 123
    bucket = ModelBucket(rate_limit=120, bucket_size_in_seconds=60, last_checked=simulated_timestamp)
    bucket.set_capacity(5, current_time=simulated_timestamp)
    assert bucket.get_capacity(simulated_timestamp) == 5

def test_capacity_after_one_second():
    rate_limit_per_minute = 120
    bucket_size_in_seconds = 60
    bucket = ModelBucket(rate_limit=rate_limit_per_minute, bucket_size_in_seconds=bucket_size_in_seconds)
    bucket.set_capacity(0)
    with patch('time.time', return_value=bucket.last_checked + 1):
        assert bucket.get_capacity() == pytest.approx(rate_limit_per_minute / 60, 0.1)

def test_capacity_replenished_after_bucket_size_in_seconds():
    rate_limit_per_minute = 120
    bucket_size_in_seconds = 60
    bucket = ModelBucket(rate_limit=rate_limit_per_minute, bucket_size_in_seconds=bucket_size_in_seconds)
    bucket.set_capacity(0)
    with patch('time.time', return_value=bucket.last_checked + bucket_size_in_seconds):
        assert bucket.get_capacity() == pytest.approx(rate_limit_per_minute, 0.1)