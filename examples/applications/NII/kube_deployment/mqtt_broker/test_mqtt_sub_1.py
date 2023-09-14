import paho.mqtt.client as mqtt
import json
import base64

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe("$share/group_name/test/shared_topic/rohe/nii_case")


def on_message(client, userdata, message):
    payload_str = message.payload.decode("utf-8")
    payload = json.loads(payload_str)

    # Extract and decode the image
    image_b64 = payload.get('image', '')
    image_data = base64.b64decode(image_b64)
    file_extension = payload.get('file_extension')
    print(f"receive image with extension: {file_extension}")
    # Save the image or process it further
    with open(f"received_image.{file_extension}", "wb") as image_file:
        image_file.write(image_data)

    # # Display the image using OpenCV
    # image_np = cv2.imdecode(np.frombuffer(image_data, np.uint8), -1)
    # cv2.imshow('Received Image', image_np)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    print("Image received and saved.")

client = mqtt.Client()
client.on_message = on_message
client.on_connect = on_connect

print("About to connect")
client.connect("localhost", 1883, 60)
client.loop_forever()
