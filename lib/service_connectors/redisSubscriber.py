import redis

class RedisSubscriber:
    def __init__(self, host='localhost', port=6379, db=0):
        self.r = redis.Redis(host=host, port=port, db=db)

    def subscribe(self, channel):
        pubsub = self.r.pubsub()
        pubsub.subscribe(channel)
        return pubsub

    def listen(self, pubsub):
        for message in pubsub.listen():
            if message['type'] == 'message':
                print(f"Received: {message['data']}")
