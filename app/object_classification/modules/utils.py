import json
import re
import socket
import types
from datetime import datetime
from typing import Callable

import numpy as np
from core.serviceRegistry.consul import ConsulClient


def get_function_from_module(module: types.ModuleType, func_name: str) -> Callable:
    """
    Retrieves a function by name from a given module
    """
    try:
        func: Callable = getattr(module, func_name)
        return func
    except:
        return None


def decode_binary_image(binary_encoded_object: bytes, dtype: np.dtype, shape: tuple):
    """
    this function decode an binary object into a numpy array
    input:
    - binary_encoded (bytes): binary file-like object
    - dtype (np.dtype): data type of original array
    - shape (tuple): shape of numpy array
    output: a numpy array
    """
    try:
        image = np.frombuffer(binary_encoded_object, dtype=dtype)
        image = image.reshape(shape)
    except:
        image = None
    return image


def save_numpy_array(self, arr, file_path):
    """
    Saves a numpy array to a file at the specified file path.
    """
    np.save(file_path, arr)


def convert_str_to_datetime(str_time: str, option: str = None):
    time = datetime.strptime(str_time, "%Y-%m-%dT%H:%M:%SZ")
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
    """
    get current utc timestamp
    either date only (option='date_only')
    or both date and time (default)
    """
    if option == "date_only":
        return datetime.utcnow().strftime("%d-%m-%y")
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def message_serialize(dictionary) -> str:
    """
    convert object (dict) into string
    """
    return json.dumps(dictionary)


def message_deserialize(string_object) -> dict:
    """
    convert string to object (dict)
    """
    return json.loads(string_object.decode("utf-8"))


def extract_file_extension(url):
    """
    Extracts the file extension from a URL or file path
    """
    # Regular expression to match the file extension
    match = re.search(r"\.([^.\/]+)$", url)
    if match:
        return match.group(1)
    else:
        return ""


def convert_str_to_tuple(str_obj) -> tuple:
    return tuple(map(int, str_obj.split(",")))


def get_local_ip():
    try:
        # The following line creates a socket to connect to an external site
        # The IP address returned is the one of the network interface used for the connection
        # '8.8.8.8' is used here as it's a public DNS server by Google
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        return "Unable to get IP: " + str(e)


def parse_time(time_str) -> int:
    """
    Parses time strings into seconds.
    Supported formats: Xs (seconds), Xm (minutes), Xh (hours).
    """
    match = re.match(r"(\d+)([smh])", time_str)
    if not match:
        raise ValueError(f"Invalid time format: {time_str}")

    value, unit = int(match.group(1)), match.group(2)
    if unit == "s":
        return value
    elif unit == "m":
        return value * 60
    elif unit == "h":
        return value * 3600


def handle_service_query(
    consul_client: ConsulClient, service_name, query_type, tags=None
):
    if query_type == "all":
        return consul_client.getAllServiceInstances(service_name, tags)

    if query_type == "one":
        return consul_client.getNRandomServiceInstances(service_name, tags, n=1)

    if query_type == "quorum":
        return consul_client.getQuorumServiceInstances(service_name, tags)

    # raise ValueError(f"Unknown service type: {service_type}")
    return
