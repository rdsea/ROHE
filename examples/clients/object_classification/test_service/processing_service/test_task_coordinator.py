import requests
import json

# Prepare the data
data = {
    'command': 'add',
    'timestamp': '2023-09-13T20:19:13Z',
    'device_id': 'device_123',
    'image_url': 'minio/sample/vxho.npy',
    'request_id': "2423fkjsadf238",
}

# # Convert the dictionary to form-data
# data = {key: str(value) for key, value in data.items()}

print(f"This is the format of the data: {type(data)}")
# Make the POST request
response = requests.post('http://localhost:5000/task_coordinator', data=data)


# Check if the request was successful
if response.status_code == 200:
    print(f"Success to add message to queue: {response.json()}")

    # response = requests.get('http://localhost:5000/task_coordinator')
    # print(f"This is a pure response: {response}")
    # print(f"This is to use json.load: {json.loads(response.text)}")
    # print(f"This is the reponse when claiming image: {response.json()}")

    
else:
    print(f"Failed: {response.json()}")


