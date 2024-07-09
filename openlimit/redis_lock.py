import uuid

import redis
import time
import uuid

class RedisLock:
    def __init__(self, redis_client, lock_name, expire_time=10):
        self.redis = redis_client
        self.lock_name = lock_name
        self.expire_time = expire_time
        self.owner = str(uuid.uuid4())
    
    def acquire(self, retry_interval=0.1, max_retries=50):
        for _ in range(max_retries):
            if self.redis.set(self.lock_name, self.owner, nx=True, ex=self.expire_time):
                return True
            time.sleep(retry_interval)
        return False
    
    def release(self):
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        return bool(self.redis.eval(script, 1, self.lock_name, self.owner))

    def __enter__(self):
        if not self.acquire():
            raise TimeoutError("Unable to acquire lock")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()