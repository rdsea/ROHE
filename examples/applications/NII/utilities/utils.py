import os
import json

def get_parent_dir(file_path, levels_up=1):
    file_path = os.path.abspath(file_path)  # Get the absolute path

    parent_path = file_path
    for _ in range(levels_up):
        parent_path = os.path.dirname(parent_path)
    return parent_path

def print_hello():
    print("Hello from examples.application.NII.utils")

def serialize(dictionary) -> str:
    return json.dumps(dictionary)

def deserialize(string_object) -> dict:
    return json.loads(string_object.decode("utf-8"))

def get_image_dim_from_str(str_obj) -> tuple:
    return tuple(map(int, str_obj.split(',')))