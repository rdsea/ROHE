from mqttPublisher import MqttPublisher
import time
import os
import base64
from datetime import datetime
import time

def get_file_extension(file_path):
    return os.path.splitext(file_path)[1][1:]

broker_info = {
    "url": "localhost",
    "port": 1883,
    "keep_alive": 60
}
client_id = "publisher_001"
# topic = "rohe/nii_case_2"
topic = "shared_topic/rohe/nii_case/test"


image_path = "./01.jpg"
# Read the image file and Base64 encode it
with open(image_path, "rb") as image_file:
    image_data = image_file.read()
    image_b64 = base64.b64encode(image_data).decode('utf-8')

file_extension = get_file_extension(image_path)
shape = None
dtype = None

payload = {
    'timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    'device_id': "camera01",
    'image': image_b64,
    'file_extension': file_extension,
    'shape': None,
    'dtype': None,
}

publisher = MqttPublisher(broker_info= broker_info, client_id= client_id, pub_topic= topic)


time.sleep(5)
for i in range(1, 2):
    # time.sleep(2)
    publisher.send_data(payload)


publisher.stop()