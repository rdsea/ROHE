import json
import logging
import threading

import paho.mqtt.client as mqtt

logging.getLogger(__name__)


class MqttPublisher:
    def __init__(self, broker_info, client_id, pub_topic):
        self.client_id = client_id
        self.pub_topic = pub_topic
        self.connect_event = threading.Event()  # Create an event object

        self.client = mqtt.Client(client_id=self.client_id, clean_session=False)

        # Set callback function
        self.client.on_connect = self.on_connect
        self.client.on_publish = self.on_publish

        self.client.connect(
            broker_info["url"], broker_info["port"], broker_info["keep_alive"]
        )
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"Connected successfully to broker with client ID: {self.client_id}")
            self.connect_event.set()  # Signal that we've connected
        else:
            print(f"Failed to connect, return code {rc}")

    def on_publish(self, client, userdata, mid):
        print(f"Message published with mid: {mid}")

    def send_data(self, body_mess):
        self.connect_event.wait()  # Wait for connection to complete
        # print(f"sending message: {body_mess}")
        result = self.client.publish(self.pub_topic, json.dumps(body_mess), qos=1)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            print(f"Failed to send message, return code {result.rc}")

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()


class MqttSubscriber:
    def __init__(self, host_object, broker_info, client_id, sub_topic):
        self.host_object = host_object
        self.client_id = client_id
        self.sub_topic = sub_topic

        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.client.connect(
            broker_info["url"], broker_info["port"], broker_info["keep_alive"]
        )

        self.client.loop_forever()

    def on_connect(self, client, userdata, flags, rc):
        logging.info("Connected with result code " + str(rc))
        self.client.subscribe(self.sub_topic, qos=1)

    def on_message(self, client, userdata, msg):
        self.host_object.message_processing(client, userdata, msg)

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
