

class HostObject:
    def message_processing(self, client, userdata, msg):
        print(f"Received message: {msg.payload.decode('utf-8')} from topic: {msg.topic}")

from mqttSubscriber import MqttSubscriber
import logging

# Enable logging
logging.basicConfig(level=logging.DEBUG)

broker_info = {
    "url": "localhost",
    "port": 1883,
    "keep_alive": 60
}
client_id = "subscriber_001"
# topic = "test/shared_topic/rohe/nii_case"
topic = "$share/name/rohe/nii_case_2"

# Initialize host object
host_object = HostObject()

# Initialize subscriber
subscriber = MqttSubscriber(host_object=host_object, broker_info=broker_info, client_id=client_id, sub_topic=topic)

# try:
#     print("Subscriber is running. Press Ctrl+C to exit.")
#     while True:
#         pass  # Keep the program running
# except KeyboardInterrupt:
#     print("Stopping subscriber.")
#     subscriber.stop()
while True:
    pass