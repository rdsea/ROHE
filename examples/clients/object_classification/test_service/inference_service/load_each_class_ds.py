import os, sys
import h5py
import numpy as np
import argparse

import qoa4ml.qoaUtils as qoa_utils


# set the ROHE to be in the system path
lib_level = os.environ.get('LIB_LEVEL')
if not lib_level:
    lib_level = 5
main_path = config_file = qoa_utils.get_parent_dir(__file__,lib_level)
sys.path.append(main_path)


def load_and_check(save_folder):
    # List all files in the save_folder
    files = os.listdir(save_folder)
    
    # Filter out the files that are not .h5
    h5_files = [file for file in files if file.endswith('.h5')]
    
    # Iterate over the .h5 files and load each one to check the data
    for file in h5_files:
        file_path = os.path.join(save_folder, file)
        
        with h5py.File(file_path, 'r') as hf:
            X = np.array(hf['images'])
            y = np.array(hf['labels'])
            
        # Extract the class name from the file name
        class_name = file.split("_")[1].split(".")[0]
        
        # Print class name and shapes of X and y
        print(f"{class_name}: {X.shape}, {y.shape}")
        # result is liike this
        # 0: (1220, 32, 32, 3), (1220, 13)
        # 7: (640, 32, 32, 3), (640, 13)
        # 6: (4522, 32, 32, 3), (4522, 13)
        # 8: (4679, 32, 32, 3), (4679, 13)
        # 2: (29169, 32, 32, 3), (29169, 13)
        # 1: (2026, 32, 32, 3), (2026, 13)
        # 3: (465, 32, 32, 3), (465, 13)
        # 12: (4423, 32, 32, 3), (4423, 13)
        # 9: (6002, 32, 32, 3), (6002, 13)
        
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for choosing model to request")
    parser.add_argument('--save_dir', type=str, help='save folder',
                        default="/artifact/nii/datasets/BDD100K-Classification/test_set")
    args = parser.parse_args()
    save_folder = main_path+args.save_dir

    load_and_check(save_folder)
