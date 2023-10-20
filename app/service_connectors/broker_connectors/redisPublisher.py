import threading
import redis

class RedisPublisher:
    def __init__(self, host='localhost', port=6379, db=0):
        self.redis_client = redis.Redis(host=host, port=port, db=db)
        self.lock = threading.Lock()  # Thread lock

    def publish(self, channel, message):
        with self.lock:  # Make sure only one thread publishes at a time
            self.redis_client.publish(channel, message)
