import redis
from datetime import datetime 
import json


# Configuration for the Redis client
redis_config = {
    'host': 'localhost',
    'port': 6379,
    'db': 0
}

# Initialize the Redis client
client = redis.Redis(host=redis_config['host'], port=redis_config['port'], db=redis_config['db'])

# Test Connection
try:
    response = client.ping()
    print("Connected to Redis:", response)
except Exception as ex:
    print("Cannot connect to Redis:", ex)
    exit(1)

# Create Queues
queue_names = ['unprocessed_image', 'processing_images', 'processed_images']


# for queue in queue_names:
#     try:
#         # Use Redis lists as queues
#         # Right push an initial element and then remove it, to make sure the list exists.
#         client.rpush(queue, "initial_element")
#         client.lpop(queue)
#         print(f"Queue {queue} is ready.")
#     except Exception as ex:
#         print(f"Cannot create queue {queue}: {ex}")


timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
sample = {
    "timestamp": timestamp,
    "device_id": "device_123",
    "image_url": "minio/sample/vxho.npy"
}
image_info = {
    'timestamp': sample['timestamp'],
    'device_id': sample['device_id'],
    'image_url': sample['image_url']
}

def serialize(dictionary) -> str:
    return json.dumps(dictionary)

def deserialize(string_object) -> dict:
    return json.loads(string_object.decode("utf-8"))

def enqueue(image_info):
    if all(image_info.values()):
        serialized_image_info = serialize(image_info)
        client.lpush("unprocessed_images", serialized_image_info)
        print("Successfully send info to the queue")

def dequeue():
    serialized_image_info = client.rpoplpush("unprocessed_images", "processing_images")
    if serialized_image_info:
        image_info = deserialize(serialized_image_info)
        print(f"Successfully get the info: {image_info}")

def get_processing_queue():
    serialized_image_info = serialize(image_info)
    # serialized_image_info = client.lpop("processing_images")
    # print(f"This is what inside the processing queue: {serialized_image_info}")
    result = client.lrem("processing_images", 0, serialized_image_info)
    print(f"Try to destroy the element in process image queue: {result}")

    serialized_image_info = client.lpop("processing_images")
    print(f"try to pop up again: {serialized_image_info}")

    # serialized_image_info = client.lpop("processing_images")
    # print(f"try to pop up again: {serialized_image_info}")

enqueue(image_info= image_info)
dequeue()
get_processing_queue()