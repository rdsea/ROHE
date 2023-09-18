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
    
def load_config(file_path:str, format=0)->dict:
    """
    file_path: file path to load config
    format:
        0 - json
        1 - yaml
        other - To Do
    """
    try:
        if format == 0:
            with open(file_path, "r") as f:
                return json.load(f)
        elif format == 1:
            with open('file_path', 'r') as f:
                return yaml.safe_load(f)
        else:
            return None
    except Exception as e:
        return None
    
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