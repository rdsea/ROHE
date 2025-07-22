import os
import sys
parent_dir = os.path.abspath(os.path.join(os.getcwd(), '..', '..'))
sys.path.append(parent_dir)
import argparse
from rohe.common.rohe_utils import find_all_files_in_mmact
import random
import numpy as np
import pandas as pd
from sktime.transformations.panel.rocket import MiniRocket
from sklearn.linear_model import RidgeClassifierCV
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
import joblib
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# load environment variables
DATA_PATH = os.getenv('DATA_PATH')

CSV_DIR = os.path.join(DATA_PATH, 'mmact/trimmed_sensor/')
print(f"CSV directory: {CSV_DIR}")

DEVICE_LIST = ["acc_phone_clip", "acc_watch_clip", "gyro_clip", "orientation_clip"]
TIME_SERIES_LENGTH = 200  # Adjust this value based on your data
NUM_VERSIONS = 5  # Number of versions to train


def load_data_from_csv(file_info_list, device, time_series_length, min_length=100):
    X = []
    y = []
    label_mapping = {}
    label_counter = 0
   
    for info in file_info_list:
        if info["device"] != device:
            continue
        try:
            label = info["file_name"]  # Use the file name (without extension) as the label
            if label not in label_mapping:
                label_mapping[label] = label_counter
                label_counter += 1
            file_path = info["file_path"]
            df = pd.read_csv(file_path)
            # drop the first column 
            df = df.drop(df.columns[0], axis=1)
            # convert to numpy array float 32
            time_series_data = df.to_numpy(dtype=np.float32)
            
            # Skip time series data that are shorter than time_series_length
            if time_series_data.shape[0] < time_series_length:
                continue
            
            # Truncate or sample the time series data to the fixed length
            if time_series_data.shape[0] > time_series_length:
                indices = np.linspace(0, time_series_data.shape[0] - 1, time_series_length).astype(int)
                time_series_data = time_series_data[indices]
            
            # Transpose the time series data to have shape (3, 200)
            time_series_data = time_series_data.T
            
            X.append(time_series_data)
            y.append(label_mapping[label])
        except Exception as e:
            logging.error(f"Error processing {file_path}: {e}")

    X = np.array(X)
    logging.info(f"Shape of X: {X.shape}")
    y = np.array(y)
    logging.info(f"Shape of y: {y.shape}")
    return X, y, label_mapping

if __name__ == "__main__":
    # Argument parser for command line execution
    parser = argparse.ArgumentParser(description="Train MiniRocket model on time series data.")
    parser.add_argument('--csv_dir', type=str, default=CSV_DIR, help='Directory containing CSV files.')
    parser.add_argument('--time_series_length', type=int, default=TIME_SERIES_LENGTH, help='Length of the time series data.')
    parser.add_argument('--num_versions', type=int, default=NUM_VERSIONS, help='Number of versions to train.')
    args = parser.parse_args()
    
    csv_dir = args.csv_dir
    time_series_length = args.time_series_length
    num_versions = args.num_versions
    csv_file_path_list, csv_file_info_list = find_all_files_in_mmact(csv_dir, '.csv')

    for device in DEVICE_LIST:
        X, y, label_mapping = load_data_from_csv(file_info_list=csv_file_info_list, device=device, time_series_length=time_series_length)
        logging.info(f"Loaded data for device: {device} with shape {X.shape} and labels {len(label_mapping)}")

        for i in range(num_versions):
            logging.info(f"Starting training for {device}_v{i}")
            try:
                # Randomly shuffle the data
                indices = np.random.permutation(X.shape[0])
                X = X[indices]
                y = y[indices]
                logging.info("Split data set")
                # Split the data into training and test sets
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=random.randint(0, 1000))

                # Initialize MiniRocket transformer
                minirocket = MiniRocket()

                # # Fit MiniRocket on the training data
                minirocket.fit(X_train)

                # Transform the training and test data
                X_train_transform = minirocket.transform(X_train)
                X_test_transform = minirocket.transform(X_test)

                # Initialize and train the classifier
                classifier = RidgeClassifierCV(alphas=np.logspace(-3, 3, 10))
                logging.info("Training classifier")
                classifier.fit(X_train_transform, y_train)

                # Make predictions
                logging.info("Testing predictions")
                y_pred = classifier.predict(X_test_transform)

                # Evaluate the model
                accuracy = accuracy_score(y_test, y_pred)
                logging.info(f"Accuracy: {accuracy:.4f}")

                # Example of making a prediction on a new time series
                new_time_series = X_test[0:1]  # Take the first instance from the test set as an example
                new_time_series_transform = minirocket.transform(new_time_series)
                new_prediction = classifier.predict(new_time_series_transform)
                logging.info(f"Prediction for new time series: {new_prediction[0]}")

                # check if folder exists, if not create it
                folder = f"./{device}/"
                if not os.path.exists(folder):
                    os.makedirs(folder)
                folder = f"./{device}/v{i}/"
                if not os.path.exists(folder):
                    os.makedirs(folder)
                
                joblib.dump(minirocket, f'{folder}minirocket.pkl', protocol=4)
                joblib.dump(classifier, f'{folder}classifier.pkl', protocol=4)
                joblib.dump(label_mapping, f'{folder}label_mapping.pkl', protocol=4)
                print(f"Model {device}_v{i} saved to minirocket.pkl, classifier.pkl, and label_mapping.pkl")
            except Exception as e:
                print(f"Error processing {device}: {e}")
                continue
            
