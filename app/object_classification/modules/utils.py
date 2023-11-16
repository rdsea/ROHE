
from datetime import datetime
import numpy as np
import json
import os
import re


def decode_binary_image(binary_encoded_object: bytes, dtype: np.dtype, shape: tuple):
    '''
    this function decode an binary object into a numpy array
    input:
    - binary_encoded (bytes): binary file-like object
    - dtype (np.dtype): data type of original array
    - shape (tuple): shape of numpy array
    output: a numpy array
    '''
    try:
        image = np.frombuffer(binary_encoded_object, dtype=dtype)
        image = image.reshape(shape)
    except:
        image = None
    return image

def save_numpy_array(self, arr, file_path):
    '''
    Saves a numpy array to a file at the specified file path.
    '''
    np.save(file_path, arr)

    
def convert_str_to_datetime(str_time: str, option: str = None):
    time = datetime.strptime(str_time, '%Y-%m-%dT%H:%M:%SZ')
    if option == "date_only":
        # Extract day, month, and year
        day = time.day
        month = time.month
        year = time.year
        # Format as d-m-y
        formatted_date = f"{day}-{month}-{year}"
        return formatted_date
    else:
        return time

                             
def get_current_utc_timestamp(option: str = None):
    '''
    get current utc timestamp 
    either date only (option='date_only')
    or both date and time (default)
    '''
    if option == "date_only":
        return datetime.utcnow().strftime('%d-%m-%y')
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

def message_serialize(dictionary) -> str:
    '''
    convert object (dict) into string
    '''
    return json.dumps(dictionary)

def message_deserialize(string_object) -> dict:
    '''
    convert string to object (dict)
    '''
    return json.loads(string_object.decode("utf-8"))


def extract_file_extension(url):
    # Regular expression to match the file extension
    match = re.search(r'\.([^.\/]+)$', url)
    if match:
        return match.group(1)  # Returns the file extension without the leading period
    else:
        return ""  # No extension found


def convert_str_to_tuple(str_obj) -> tuple:
    return tuple(map(int, str_obj.split(',')))