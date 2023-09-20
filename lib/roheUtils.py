import json, psutil, time, os, yaml, logging
from threading import Thread
import traceback,sys, pathlib, requests

import logging

logging.basicConfig(format='%(asctime)s:%(levelname)s -- %(message)s', level=logging.INFO)

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

def download_file_from_google_drive(id, destination):
    URL = "https://docs.google.com/uc?export=download&confirm=1"

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


def save_response_content(response, destination):
    CHUNK_SIZE = 32768

    with open(destination, "wb") as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)

def message_serialize(dictionary) -> str:
    return json.dumps(dictionary)

def message_deserialize(string_object) -> dict:
    return json.loads(string_object.decode("utf-8"))

def json_to_yaml(file_path):
    config = load_config(file_path)
    yaml_path = str(file_path)[:-4]+"yaml"
    yaml_config = to_yaml(yaml_path,config)