


import argparse
import os, sys
import qoa4ml.qoaUtils as qoa_utils
import h5py
import numpy as np


# set the ROHE to be in the system path
from dotenv import load_dotenv
load_dotenv()

main_path = os.getenv('ROHE_PATH')
print(f"This is main path: {main_path}")
sys.path.append(main_path)


import lib.roheUtils as roheUtils

import argparse
import os, sys
import qoa4ml.qoaUtils as qoa_utils
import h5py
import numpy as np
import pandas as pd



def create_subset(ds, min_samples_per_class=450, subset_frac_range=(0.2, 0.4), total_size=None):
    subset = {'X': [], 'y': []}
    
    for class_label, class_data in ds.items():
        samples_to_pick = min(len(class_data['X']), min_samples_per_class)
        indices = np.random.choice(len(class_data['X']), samples_to_pick, replace=False)
        
        subset['X'].extend(class_data['X'][indices])
        subset['y'].extend(class_data['y'][indices])
    
    # Shuffle the intermediate subset
    indices = np.random.permutation(len(subset['X']))
    subset['X'] = np.array(subset['X'])[indices]
    subset['y'] = np.array(subset['y'])[indices]
    
    # Determine how many samples we need to add based on fraction range
    subset_size_min = int(subset_frac_range[0] * total_size)
    subset_size_max = int(subset_frac_range[1] * total_size)
    final_subset_size = np.random.randint(subset_size_min, subset_size_max + 1)
    
    additional_samples_required = final_subset_size - len(subset['X'])
    
    if additional_samples_required > 0:
        all_X = []
        all_y = []
        for class_data in ds.values():
            all_X.extend(class_data['X'])
            all_y.extend(class_data['y'])
        
        all_X = np.array(all_X)
        all_y = np.array(all_y)
        
        additional_indices = np.random.choice(len(all_X), additional_samples_required, replace=False)
        subset['X'] = np.concatenate([subset['X'], all_X[additional_indices]])
        subset['y'] = np.concatenate([subset['y'], all_y[additional_indices]])
    
    # Shuffle the final subset
    final_indices = np.random.permutation(len(subset['X']))
    
    return {'X': subset['X'][final_indices], 'y': subset['y'][final_indices]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for choosing model to request")
    parser.add_argument('--test_ds', type=str, help='test dataset path',
                        default="/artifact/nii/datasets/BDD100K-Classification/test.h5")
    parser.add_argument('--save_dir', type=str, help='save folder',
                        default="/artifact/nii/datasets/BDD100K-Classification/test_set/subset")

    parser.add_argument('--no_subset', type=int, default=3)

    args = parser.parse_args()
    test_ds = main_path+args.test_ds
    save_folder = main_path+args.save_dir

    if not os.path.isdir(save_folder):
        os.mkdir(save_folder)


    with h5py.File(test_ds, 'r') as f:
        X_test = np.array(f['images'])
        y_test = np.array(f['labels'])
    
    ds = roheUtils.separate_ds_by_class(X_test, y_test)
    total_size = len(X_test)
    
    metadata = []
    for subset_idx in range(args.no_subset):
        subset = create_subset(ds, total_size=total_size)
        file_name = f"subset_{subset_idx}.h5"
        file_path = os.path.join(save_folder, file_name)
        
        with h5py.File(file_path, 'w') as hf:
            print(f"This is the len of the ds: {len(subset['X'])}")
            hf.create_dataset('images', data=subset['X'])
            hf.create_dataset('labels', data=subset['y'])
        
        print(f"Saved {file_name} to {save_folder}")
        

        from collections import Counter
        label_predictions = np.argmax(subset['y'], axis=1) 
        label_counts = dict(Counter(label_predictions))

        metadata.append(label_counts)
    
    # Save metadata to CSV
    df = pd.DataFrame(metadata)
    df.to_csv(os.path.join(save_folder, 'metadata.csv'), index=False)
