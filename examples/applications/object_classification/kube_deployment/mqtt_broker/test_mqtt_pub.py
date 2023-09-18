import paho.mqtt.client as mqtt
import json
import datetime
import base64
import os

def on_publish(client, userdata, result):
    print(f"Message Published with result {result}")

def get_file_extension(file_path):
    return os.path.splitext(file_path)[1][1:]

image_path = "./01.jpg"
# Read the image file and Base64 encode it
with open(image_path, "rb") as image_file:
    image_data = image_file.read()
    image_b64 = base64.b64encode(image_data).decode('utf-8')

file_extension = get_file_extension(image_path)
shape = None
dtype = None
# if file_extension == "npy":
#     shape = image_data    

client = mqtt.Client()
client.on_publish = on_publish
client.connect("localhost", 1883, 60)

for i in range(1):
    payload = {
        'timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'device_id': "camera01",
        'image': image_b64,
        'file_extension': file_extension,
        'shape': None,
        'dtype': None,
    }
    client.publish("test/shared_topic/rohe/nii_case", json.dumps(payload))

client.disconnect()
