


import argparse
import os, sys
import qoa4ml.qoaUtils as qoa_utils
import h5py
import numpy as np


# set the ROHE to be in the system path
lib_level = os.environ.get('LIB_LEVEL')
if not lib_level:
    lib_level = 5
main_path = config_file = qoa_utils.get_parent_dir(__file__,lib_level)
sys.path.append(main_path)


import lib.roheUtils as roheUtils

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for choosing model to request")
    parser.add_argument('--test_ds', type=str, help='test dataset path',
                        default="/artifact/nii/datasets/BDD100K-Classification/test.h5")
    parser.add_argument('--save_dir', type=str, help='save folder',
                        default="/artifact/nii/datasets/BDD100K-Classification/test_set")

    args = parser.parse_args()
    test_ds = main_path+args.test_ds
    save_folder = main_path+args.save_dir

    if not os.path.isdir(save_folder):
        os.mkdir(save_folder)


    with h5py.File(test_ds, 'r') as f:
        X_test = np.array(f['images'])
        y_test = np.array(f['labels'])


    ds = roheUtils.separate_ds_by_class(X_test, y_test)

    # save each small ds into separate .h5 file in the chosen folder
    # Save each separated dataset by class to a .h5 file
    for class_label, class_data in ds.items():
        file_name = f"class_{class_label}.h5"
        file_path = os.path.join(save_folder, file_name)

        with h5py.File(file_path, 'w') as hf:
            hf.create_dataset('images', data=class_data['X'])
            hf.create_dataset('labels', data=class_data['y'])

        print(f"Saved {file_name} to {save_folder}")