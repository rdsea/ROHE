import os
import shutil
import json
import argparse

def delete_folder(folder_path):
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    else:
        print(f"Folder {folder_path} does not exist.")

def delete_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
    else:
        print(f"File {file_path} does not exist.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete folders and files listed in the configuration file.")
    parser.add_argument('--conf', type=str, help='Configuration file', default="dependencies.json")
    args = parser.parse_args()
    config_file = args.conf

    # Load the configuration file
    with open(config_file, 'r') as json_file:
        config = json.load(json_file)

    # Get the list of relevant folders and files from the configuration
    relevant_folders = config['relevant_folders']
    relevant_files = config['relevant_files']

    current_path = os.getcwd()

    # Delete relevant folders
    for folder in relevant_folders:
        folder_path = os.path.join(current_path, folder)
        delete_folder(folder_path)

    # Delete relevant files
    for file in relevant_files:
        file_path = os.path.join(current_path, file)
        delete_file(file_path)
