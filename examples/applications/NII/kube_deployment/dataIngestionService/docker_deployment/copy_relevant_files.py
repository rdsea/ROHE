import shutil
import os
import sys
import json 

import argparse


def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
        
def copy_folder(src_folder, dst_folder):
    if os.path.exists(dst_folder):
        shutil.rmtree(dst_folder)
    shutil.copytree(src_folder, dst_folder)

def copy_file(src_file, dst_file):
    ensure_directory_exists(os.path.dirname(dst_file))  # Make sure the parent directory exists
    shutil.copy(src_file, dst_file)

# set the ROHE to be in the system path
def get_parent_dir(file_path, levels_up=1):
    file_path = os.path.abspath(file_path)  # Get the absolute path of the running file
    parent_path = file_path
    for _ in range(levels_up):
        parent_path = os.path.dirname(parent_path)
    return parent_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument('--conf', type= str, help='configuration file', 
                        default= "dependencies.json")

    args = parser.parse_args()
    config_file = args.conf

    # load configuration file
    with open(config_file, 'r') as json_file:
        config = json.load(json_file)   

    # Absolute path to main project directory - ROHE
    up_level = 7
    root_path = get_parent_dir(__file__, up_level)
    print(root_path)
    current_path = os.getcwd()

    print(f"This is current path: {current_path}")

    # build_context = 'docker_build_context'
    build_context = current_path
    if not os.path.exists(build_context):
        os.mkdir(build_context)

    # Relevant folder information saved in .json file
    relevant_folders = config['relevant_folders']    
    relevant_files = config['relevant_files']

    for folder in relevant_folders:
        src = os.path.join(root_path, folder)
        dst = os.path.join(build_context, folder)
        

        print(f"this is root path: {root_path}")
        print(f"This is source: {src}")
        print(f"This is destination: {dst}\n\n")
        copy_folder(src, dst)


    for file in relevant_files:
        src = os.path.join(root_path, file)
        dst = os.path.join(build_context, file)

        print(f"This is destination: {dst}")
        # dst = build_context
        copy_file(src, dst)
        
        
    # root_model_folder = "/home/vtn/aalto-internship/test_model/VGG16"
    # src = os.path.join(root_model_folder)
    # dst = os.path.join("nii_models", "VGG16")
    # # model = "VGG16/3/6/repair"
    # # src = os.path.join(root_model_folder, model)
    # # dst = os.path.join("nii_models", model)
    # copy_folder(src, dst)