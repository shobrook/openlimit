import pytest
import redis
from openlimit.redis_lock import RedisLock
import threading
import time

pytestmark = pytest.mark.skip("all tests require local redis server")  

@pytest.fixture(scope="module")
def redis_client():
    return redis.Redis(host='localhost', port=6379, db=0)

@pytest.fixture(scope="function")
def lock_name(request):
    name = f"test_lock_{request.node.name}"
    yield name
    request.getfixturevalue("redis_client").delete(name)

def test_acquire_and_release(redis_client, lock_name):
    lock = RedisLock(redis_client, lock_name)
    assert lock.acquire()
    assert lock.release()

def test_acquire_twice(redis_client, lock_name):
    lock1 = RedisLock(redis_client, lock_name)
    lock2 = RedisLock(redis_client, lock_name)
    assert lock1.acquire()
    assert not lock2.acquire(max_retries=1)
    assert lock1.release()

def test_release_unowned_lock(redis_client, lock_name):
    lock1 = RedisLock(redis_client, lock_name)
    lock2 = RedisLock(redis_client, lock_name)
    assert lock1.acquire()
    assert not lock2.release()
    assert lock1.release()

def test_context_manager(redis_client, lock_name):
    with RedisLock(redis_client, lock_name) as lock:
        assert not RedisLock(redis_client, lock_name).acquire(max_retries=1)
    assert RedisLock(redis_client, lock_name).acquire(max_retries=1)

def test_context_manager_exception(redis_client, lock_name):
    with pytest.raises(Exception):
        with RedisLock(redis_client, lock_name):
            raise Exception("Test exception")
    assert RedisLock(redis_client, lock_name).acquire(max_retries=1)

def test_multithreading(redis_client, lock_name):
    shared_resource = 0
    num_threads = 10
    iterations_per_thread = 1000

    def worker():
        nonlocal shared_resource
        for _ in range(iterations_per_thread):
            with RedisLock(redis_client, lock_name, expire_time=5):
                current_value = shared_resource
                time.sleep(0.0001)  # Simulate some work
                shared_resource = current_value + 1

    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=worker)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    assert shared_resource == num_threads * iterations_per_thread