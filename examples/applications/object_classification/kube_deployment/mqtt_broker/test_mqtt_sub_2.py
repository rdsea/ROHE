# subscriber.py
import paho.mqtt.client as mqtt


def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe("$share/group_name/test/shared_topic/rohe/nii_case")

def on_message(client, userdata, msg):
    print(f"Received message '{msg.payload.decode()}' on topic '{msg.topic}'")

    # # Display the image using OpenCV
    # image_np = cv2.imdecode(np.frombuffer(image_data, np.uint8), -1)
    # cv2.imshow('Received Image', image_np)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

client = mqtt.Client()

client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost", 1883, 60)

client.loop_forever()
