import requests
import numpy as np
import io
import time

# The URL of the HTTP server's ingestion endpoint
# ingestion_service_url = 'http://localhost:5000/ingestion'
ingestion_service_url = 'http://localhost:3000/ingestion_service'


# Generate a dummy numpy array (for example, a 100x100 red image)
array_data = np.full((320, 320, 3), fill_value=[0, 120, 0], dtype=np.uint8)

# Convert the numpy array to a bytes object directly without converting to an image
image_bytes = io.BytesIO(array_data.tobytes())  # Use tobytes() to get the raw array bytes

# Prepare the data to send
data = {
    'timestamp': str(time.time()),
    'device_id': 'aaltosea-cam-test',
    'image_extension': 'npy',
    'shape': ','.join(map(str, array_data.shape)),  # Example: '100,100,3'
    'dtype': str(array_data.dtype)  # Example: 'uint8'
}

# Prepare the files to send
files = {
    'image': ('image.npy', image_bytes, 'application/octet-stream')
}

# Send the POST request
response = requests.post(ingestion_service_url, data=data, files=files)

# Check the response
print(response.status_code)
print(response.json())
