import paho.mqtt.client as mqtt
import json
import numpy as np
import base64
from datetime import datetime
import argparse
import sys, os

# set the ROHE to be in the system path
def get_parent_dir(file_path, levels_up=1):
    file_path = os.path.abspath(file_path)  # Get the absolute path of the running file
    parent_path = file_path
    for _ in range(levels_up):
        parent_path = os.path.dirname(parent_path)
    return parent_path

up_level = 6
root_path = get_parent_dir(__file__, up_level)
sys.path.append(root_path)

class IoTDevice:
    def __init__(self, device_id, broker_info, topic):
        self.device_id = device_id
        self.broker_info = broker_info
        self.topic = broker_info['topic']
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect

    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected with result code {rc}")

    def connect(self):
        self.client.connect(self.broker_address['url'], self.broker_info['port'], 
                            self.broker_info['keep_alive'])

    def disconnect(self):
        self.client.disconnect()

    def send_message(self, image):
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        # Convert the NumPy array to bytes and then to a base64 string
        image_bytes = image.tobytes()
        image_b64 = base64.b64encode(image_bytes).decode()

        payload = {
            'device_id': self.device_id,
            'timestamp': timestamp,
            'image': image_b64,
            'shape': str(image.shape),
            'dtype': str(image.dtype),
            'is_compressed': False 
        }

        self.client.publish(self.topic, json.dumps(payload))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Inference Service")
    parser.add_argument('--conf', type= str, help='configuration file', 
    default= "examples/applications/NII/kube_deployment/inferenceService/configuration/iot_device.json")
    parser.add_argument('--relative_path', type= bool, help='specify whether it is a relative path', default=True)

    # Parse the parameters
    args = parser.parse_args()
    config_file = args.conf
    relative_path = args.relative_path
    
    if relative_path:
        config_file = os.path.join(root_path, config_file)

    # load configuration file
    with open(config_file, 'r') as json_file:
        config = json.load(json_file)    

    device = IoTDevice(device_id=config['device_id'], 
                       broker_address=config['mqtt_config']['url'], 
                       topic=config['mqtt_config']['topic'])

    # Connect to MQTT broker
    device.connect()

    # Create a dummy 32x32x3 image
    dummy_image = np.random.randint(0, 256, (32, 32, 3), dtype=np.uint8)

    # Send the message
    device.send_message(dummy_image)

    # Disconnect from MQTT broker
    device.disconnect()
