import importlib.util
import json
import logging
import os
import pathlib
import random
import sys
import traceback
import types
from typing import Callable
import datetime
import numpy as np
import requests
import yaml
import re
import socket

logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)


def get_function_from_module(
    module: types.ModuleType, func_name: str
) -> Callable | None:
    """Retrieves a function by name from a given module"""
    try:
        func: Callable = getattr(module, func_name)
        return func
    except Exception:
        return None


def merge_dict(f_dict, i_dict, prio=False):
    try:
        if isinstance(f_dict, dict) and isinstance(i_dict, dict):
            for key in f_dict:
                if key in i_dict:
                    f_dict[key] = merge_dict(f_dict[key], i_dict[key], prio)
                    i_dict.pop(key)
            f_dict.update(i_dict)
        elif f_dict != i_dict:
            if prio:
                return f_dict
            else:
                return i_dict
    except Exception as e:
        print(f"[ERROR] - Error {type(e)} in merge_dict: {e.__traceback__}")
        traceback.print_exception(*sys.exc_info())
    return f_dict


def get_dict_at(dict, i=0):
    try:
        keys = list(dict.keys())
        return keys[i], dict[keys[i]]
    except Exception:
        traceback.print_exception(*sys.exc_info())


def get_parent_dir(file, parent_level=1, to_string=True):
    current_dir = get_file_dir(file=file, to_string=False)
    for _i in range(parent_level):
        current_dir = current_dir.parent.absolute()
    if to_string:
        return str(current_dir)
    else:
        return current_dir


def load_config(file_path: str) -> dict | None:
    """
    file_path: file path to load config
    """
    try:
        if "json" in file_path:
            with open(file_path) as f:
                return json.load(f)
        if ("yaml" in file_path) or ("yml" in file_path):
            with open(file_path) as f:
                return yaml.safe_load(f)
        else:
            return None
    except yaml.YAMLError as exc:
        print(exc)


def to_json(file_path: str, conf: dict):
    """
    file_path: file path to save config
    """
    with open(file_path, "w") as f:
        json.dump(conf, f)


def to_yaml(file_path: str, conf: dict):
    """
    file_path: file path to save config
    """
    with open(file_path, "w") as f:
        yaml.dump(conf, f)


def download_file_from_google_drive(
    id, destination, url="https://docs.google.com/uc?export=download&confirm=1"
):
    session = requests.Session()

    response = session.get(url, params={"id": id}, stream=True)
    token = get_confirm_token(response)

    if token:
        params = {"id": id, "confirm": token}
        response = session.get(url, params=params, stream=True)

    save_response_content(response, destination)


def get_confirm_token(response):
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            return value

    return None


def save_response_content(response, destination, chunk_size=32768):
    with open(destination, "wb") as f:
        for chunk in response.iter_content(chunk_size):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)


def load_yaml_config(file_path):
    with open(file_path) as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config


def message_serialize(dictionary) -> str:
    return json.dumps(dictionary)


def message_deserialize(string_object) -> dict:
    return json.loads(string_object.decode("utf-8"))


# def json_to_yaml(file_path):
#     config = load_config(file_path)
#     yaml_path = str(file_path)[:-4] + "yaml"
#     # yaml_config = to_yaml(yaml_path, config)


def separate_ds_by_class(x, y):
    """
    Separates a multi-dimensional numpy array (X) and a 2D numpy array (y) into smaller arrays according to the class labels (y),
    creating a nested dictionary with the separated X and y for each class label.

    :param x: Multi-dimensional numpy array, representing the dataset to be separated. Can have shape
              (num_samples, height, width, channels) for RGB images or (num_samples, height, width) for grayscale images.
    :param y: 2D numpy array of shape (num_samples, num_classes), representing the one-hot encoded class labels corresponding to the samples in X.
    :return: dict, a nested dictionary where the outer keys are class labels, and the values are dictionaries with keys 'X' and 'y'
             representing subsets of X and corresponding rows of y belonging to each class.
    """

    class_datasets = {}
    class_labels = np.argmax(y, axis=1)
    unique_class_labels = np.unique(class_labels)

    for label in unique_class_labels:
        indices = np.where(class_labels == label)
        class_datasets[label] = {"x": x[indices], "y": y[indices]}

    return class_datasets


def make_folder(temp_path):
    try:
        if os.path.exists(temp_path):
            # To do:
            # Log event
            pass
        else:
            # To do:
            # Log event
            os.makedirs(temp_path)
        return True
    except Exception:
        # To do:
        # Log event
        return False


def load_qoa_conf_env(qoa_conf):
    if "user_id" not in qoa_conf:
        user_id = os.environ.get("USER_ID")
        if not user_id:
            user_id = "rohe_test"
        qoa_conf["user_id"] = user_id

    instance_id = os.environ.get("INSTANCE_ID")
    if not instance_id:
        instance_id = "rohe_test_isntance"

    stage_id = os.environ.get("STAGE_ID")
    if not stage_id:
        stage_id = "rohe_test_stage"

    method = os.environ.get("METHOD")
    if not method:
        method = "rohe_test_method"

    role = os.environ.get("ROLE")
    if not role:
        role = "rohe_test_role"

    qoa_conf["instance_id"] = instance_id
    qoa_conf["stage_id"] = stage_id
    qoa_conf["functionality"] = method
    qoa_conf["role"] = role

    return qoa_conf


def df_to_csv(file_path, df):
    df.to_csv(file_path, mode="a", header=not os.path.exists(file_path))


def get_file_dir(file, to_string=True):
    current_dir = pathlib.Path(file).parent.absolute()
    if to_string:
        return str(current_dir)
    else:
        return current_dir


def get_rohe_dir(file, level=1, to_string=True):
    current_dir = get_file_dir(file=file, to_string=False)
    for _i in range(level):
        current_dir = current_dir.parent.absolute()
    if to_string:
        return str(current_dir)
    else:
        return current_dir


def load_module(file_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def list_files(folder_path):
    print(folder_path)
    file_list = {}
    for _root, _dirs, files in os.walk(folder_path):
        for item in files:
            file_path = os.path.abspath(os.path.join(folder_path, item))
            file = {item: file_path}
            file_list.update(file)
    return file_list


def get_n_sample_in_range(n, start, end):
    numbers = list(range(start, end))
    random_numbers = []

    while len(random_numbers) < n:
        num = random.choice(numbers)
        if num not in random_numbers:
            random_numbers.append(num)

    return random_numbers


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


def handle_service_query(consul_client, service_name, query_type, tags=None):
    try:
        if query_type == "all":
            return consul_client.get_all_service_instances(service_name, tags)

        if query_type == "one":
            return consul_client.get_n_random_service_instances(service_name, tags, n=1)

        if query_type == "quorum":
            return consul_client.get_quorum_service_instances(service_name, tags)

        logging.error(f"Invalid query type: {query_type}")
        return None
    except Exception as e:
        logging.error(f"Error in handle_service_query: {e}")
        return None
