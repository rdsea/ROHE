import paho.mqtt.client as mqtt
import json
import threading

class MqttPublisher:

    def __init__(self, broker_info, client_id, pub_topic):
        self.client_id = client_id
        self.pub_topic = pub_topic
        self.connect_event = threading.Event()  # Create an event object

        self.client = mqtt.Client(client_id=self.client_id, clean_session=False)

        # Set callback function
        self.client.on_connect = self.on_connect
        self.client.on_publish = self.on_publish

        self.client.connect(broker_info['url'], broker_info['port'], broker_info['keep_alive'])
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

