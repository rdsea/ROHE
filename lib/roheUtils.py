import json, psutil, time, os, yaml, logging
from threading import Thread
import traceback,sys, pathlib, requests
import numpy as np

import logging

logging.basicConfig(format='%(asctime)s:%(levelname)s -- %(message)s', level=logging.INFO)



def merge_dict(f_dict, i_dict, prio=False):
    try:
        if isinstance(f_dict, dict) and isinstance(i_dict, dict):
            for key in f_dict:
                if key in i_dict:
                    f_dict[key] = merge_dict(f_dict[key],i_dict[key],prio)
                    i_dict.pop(key)
            f_dict.update(i_dict)
        else:
            if f_dict != i_dict:
                if prio:
                    return f_dict
                else:
                    return i_dict
    except Exception as e:
        print("[ERROR] - Error {} in merge_dict: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
    return f_dict

def get_dict_at(dict, i=0):
    try:
        keys = list(dict.keys())
        return  keys[i], dict[keys[i]]
    except Exception as e:
        traceback.print_exception(*sys.exc_info())

def get_file_dir(file, to_string=True):
    current_dir = pathlib.Path(file).parent.absolute()
    if to_string:
        return str(current_dir)
    else:
        return current_dir

def get_parent_dir(file, parent_level=1, to_string=True):
    current_dir = get_file_dir(file=file, to_string=False)
    for i in range(parent_level):
        current_dir = current_dir.parent.absolute()
    if to_string:
        return str(current_dir)
    else:
        return current_dir
    
def load_config(file_path:str)->dict:
    """
    file_path: file path to load config
    """
    try:
        if 'json' in file_path:
            with open(file_path, "r") as f:
                return json.load(f)
        if ('yaml' in file_path) or ('yml' in file_path):
            with open(file_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            return None
    except yaml.YAMLError as exc:
        print(exc)
    
def to_json(file_path:str, conf:dict):
    """
    file_path: file path to save config
    """
    with open(file_path, "w") as f:
        json.dump(conf, f)

def to_yaml(file_path:str, conf:dict):
    """
    file_path: file path to save config
    """
    with open(file_path, "w") as f:
        yaml.dump(conf, f)

def download_file_from_google_drive(id, destination,URL="https://docs.google.com/uc?export=download&confirm=1"):
    session = requests.Session()

    response = session.get(URL, params={"id": id}, stream=True)
    token = get_confirm_token(response)

    if token:
        params = {"id": id, "confirm": token}
        response = session.get(URL, params=params, stream=True)

    save_response_content(response, destination)


def get_confirm_token(response):
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            return value

    return None


def save_response_content(response, destination,CHUNK_SIZE = 32768):

    with open(destination, "wb") as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)


def load_yaml_config(file_path):
    with open(file_path, 'r') as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config


def message_serialize(dictionary) -> str:
    return json.dumps(dictionary)


def message_deserialize(string_object) -> dict:
    return json.loads(string_object.decode("utf-8"))


def json_to_yaml(file_path):
    config = load_config(file_path)
    yaml_path = str(file_path)[:-4]+"yaml"
    yaml_config = to_yaml(yaml_path,config)



def separate_ds_by_class(X, y):
    """
    Separates a multi-dimensional numpy array (X) and a 2D numpy array (y) into smaller arrays according to the class labels (y),
    creating a nested dictionary with the separated X and y for each class label.
    
    :param X: Multi-dimensional numpy array, representing the dataset to be separated. Can have shape
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
        class_datasets[label] = {
            'X': X[indices],
            'y': y[indices]
        }
        
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
    except:
        # To do:
        # Log event
        return False
    
def load_qoa_conf_env(qoa_conf):
    if "userID" not in qoa_conf:
        userID = os.environ.get('USER_ID')
        if not userID:
            userID = "rohe_test"
        qoa_conf["userID"] = userID

    instanceID = os.environ.get('INSTANCE_ID')
    if not instanceID:
        instanceID = "rohe_test_isntance"

    stageID = os.environ.get('STAGE_ID')
    if not stageID:
        stageID = "rohe_test_stage"

    method = os.environ.get('METHOD')
    if not method:
        method = "rohe_test_method"

    role = os.environ.get('ROLE')
    if not role:
        role = "rohe_test_role"

    
    qoa_conf["instanceID"] = instanceID
    qoa_conf["stageID"] = stageID
    qoa_conf["method"] = method
    qoa_conf["role"] = role

    return qoa_conf



def df_to_csv(file_path, df):
    df.to_csv(file_path, mode='a', header=not os.path.exists(file_path))

def get_file_dir(file, to_string=True):
    current_dir = pathlib.Path(file).parent.absolute()
    if to_string:
        return str(current_dir)
    else:
        return current_dir

def get_rohe_dir(file, level=1, to_string=True):
    current_dir = get_file_dir(file=file, to_string=False)
    for i in range(level):
        current_dir = current_dir.parent.absolute()
    if to_string:
        return str(current_dir)
    else:
        return current_dir