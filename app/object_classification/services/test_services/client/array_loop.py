import argparse, requests, time
import sys, os, io
import numpy as np
import h5py
import random, base64
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)

def decode_image_file(image_path):
    # Read the image file and Base64 encode it
    with open(image_path, "rb") as image_file:
        image_data = image_file.read()

        image_b64 = base64.b64encode(image_data).decode('utf-8')
        return image_b64

def get_file_extension(file_path):
    return os.path.splitext(file_path)[1][1:]

def load_h5_data_set(data_path):
    with h5py.File(data_path, 'r') as f:
        X_test = np.array(f['images'])
        # y_test = np.array(f['labels'])
        return X_test
    
def load_numpy_image(data_path) -> np.ndarray:
    numpy_array= np.load(data_path)
    return numpy_array

def decode_numy_array(array: np.ndarray):
    # decoded_array = array.tobytes()
    # decoded_array = base64.b64encode(array.tobytes()).decode('utf-8')
    return io.BytesIO(array.tobytes())

def send_request(config):
    rate = config['rate']
    data_path = config['test_ds']
    file_extension = get_file_extension(data_path)
    print(f"This is file extension: {file_extension}")
    for i in range(1, 10000000000000):
        if file_extension == 'h5' or file_extension == 'npy':
            print("decode numpy array type")
            if file_extension == 'h5':
                X_test = load_h5_data_set(data_path=data_path)
                index = random.randint(0, 50000)
                x = X_test[index]
            else:
                x = load_numpy_image(data_path=data_path)
        

            image_b64 = decode_numy_array(x)
            shape = ','.join(map(str, x.shape))
            dtype = x.dtype
        else:
            print("decode other format")
            # print("Data type is image")
            image_b64 = decode_image_file(data_path)

            shape = None
            dtype = None

        data = {
            'timestamp': str(time.time()),
            'device_id': config['device_id'],
            'image_extension': 'npy',
            'shape': str(shape),
            'dtype': str(dtype),
        }
        print(f"shape of dtype: {shape}, {dtype}")

        files = {
            'image': ('image.npy', image_b64, 'application/octet-stream')
        }
    
        response = requests.post(config['url'], data=data, files=files)

        # Check the response
        print(response.status_code)
        print(response.json())
        # time.sleep(0.2)

if __name__ == '__main__':
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for choosingg model to request")
    # parser.add_argument('--test_ds', type= str, help='default test dataset path', 
    #             default= "01.jpg")
    parser.add_argument('--test_ds', type= str, help='test dataset path', 
                default= "/artifact/nii/datasets/BDD100K-Classification/test.h5")
    parser.add_argument('--rate', type= int, help='number of requests per second', default= 20)
    parser.add_argument('--device_id', type= str, help='specify device id', default= "aaltosea_cam_01")
    parser.add_argument('--url', type= str, help='request url', default= "http://localhost:3000/ingestion_service")

    # Parse the parameters
    args = parser.parse_args()
    device_id = args.device_id
    test_ds = ROHE_PATH + args.test_ds
    req_rate = args.rate

    config = {
        'device_id': device_id,
        'test_ds': test_ds,
        'rate': args.rate,
        'url': args.url
    }
    send_request(config)