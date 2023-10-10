import os, sys
from typing import List, Callable
import pandas as pd
import argparse

import qoa4ml.qoaUtils as qoa_utils

# set the ROHE to be in the system path
lib_level = os.environ.get('LIB_LEVEL')
if not lib_level:
    lib_level = 3
main_path = config_file = qoa_utils.get_parent_dir(__file__,lib_level)
sys.path.append(main_path)


def get_subfolders(path):
    """
    This function returns a list of all subfolders in the specified folder.
    :param path: Path of the folder to list subfolders.
    :return: List of subfolders.
    """
    try:
        folders = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
        return folders
    except FileNotFoundError:
        print(f"Error: {path} does not exist.")
        return []
    except PermissionError:
        print(f"Error: Do not have permission to access {path}.")
        return []

def get_target_folder_name(folder_path):
    return os.path.basename(folder_path)

def preprocess_df(df: pd.DataFrame):
    processed_df = df
    # Drop rows where 'role' column has missing values
    # indicate the row contain error in recording process
    processed_df.dropna(subset=['class_object','role', 'accuracy', 'confidence', 'responseTime'], inplace=True)
    processed_df['class_object'] = processed_df['class_object'].astype(int)

    # ensure all field is numberic and not null
    processed_df['confidence'] = pd.to_numeric(processed_df['confidence'], errors='coerce')

    # Drop rows where 'confidence' is not between 0 and 1
    processed_df = processed_df[processed_df['confidence'].between(0, 1, inclusive=True)]

    # Reset the index after dropping rows
    processed_df.reset_index(drop=True, inplace=True)

    return processed_df

def make_inference_report(dataframe: pd.DataFrame, model_id: str):
    dataframe = dataframe.copy(deep= True)
    # # Drop rows where 'role' column has missing values
    # # indicate the row contain error in recording process
    # dataframe.dropna(subset=['role', 'class_object'], inplace=True)
    
    # dataframe['class_object'] = dataframe['class_object'].astype(int)
    
    # # ensure all field is numberic and not null
    # dataframe['confidence'] = pd.to_numeric(dataframe['confidence'], errors='coerce')

    # # Drop rows where 'confidence' is not between 0 and 1
    # dataframe = dataframe[dataframe['confidence'].between(0, 1, inclusive=True)]

    # # Reset the index after dropping rows
    # dataframe.reset_index(drop=True, inplace=True)

    # # Drop rows containing NaN values in essential columns
    # dataframe.dropna(subset=['accuracy', 'confidence', 'responseTime'], inplace=True)

    grouped = dataframe.groupby('class_object')


    # Create a new DataFrame to hold the calculated metrics
    model_quality = pd.DataFrame({
        'accuracy': grouped['accuracy'].sum() / grouped['accuracy'].count(),  
        'avg_confidence': grouped['confidence'].mean(), 
        'min_confidence': grouped['confidence'].min(),
        'avg_response_time': grouped['responseTime'].mean(), 
        'min_response_time': grouped['responseTime'].min(),
        'max_response_time': grouped['responseTime'].max(),
    }).reset_index()


    model_quality.rename(columns={'class_object': 'class'}, inplace=True)

    model_quality.head()

    # Define a dictionary to map class labels
    class_dict = {
        0: "bicycle",
        1: "bus",
        2: "car",
        3: "motorcycle",
        4: "other person",
        5: "other vehicle",
        6: "pedestrian",
        7: "rider",
        8: "traffic light",
        9: "traffic sign",
        10: "trailer",
        11: "train",
        12: "truck"
    }

    # Assuming 'result_df' is the DataFrame you are working with.
    # Map the 'class' column with the dictionary and create a new column, e.g., 'class_id'
    model_quality['class_label'] = model_quality['class'].map(class_dict)

    return model_quality


def make_throughput_report(dataframe: pd.DataFrame, model_id):
    dataframe = dataframe.copy(deep= True)

    # Drop rows where 'role' column has missing values
    # indicate the row contain error in recording process
    dataframe.dropna(subset=['role'], inplace=True)
    
    dataframe['class_object'] = dataframe['class_object'].astype(int)
    
    # Convert to appropriate data types
    dataframe['timestamp'] = pd.to_numeric(dataframe['timestamp'], errors='coerce')

    # Drop rows where 'timestamp' is NaN
    dataframe.dropna(subset=['timestamp'], inplace=True)

    # Sort the dataframe by 'timestamp'
    dataframe.sort_values(by='timestamp', inplace=True)

    window_size = 100  # define your window size
    step_size = 1  # define your step size; 1 for sliding the window by 1 record at a time

    throughputs = []

    for i in range(0, len(dataframe) - window_size + 1, step_size):
        window = dataframe.iloc[i:i + window_size]
        
        if len(window) == window_size:
            first_record_time = window.iloc[0]['timestamp']
            last_record_time = window.iloc[-1]['timestamp']
            
            time_window = last_record_time - first_record_time
            if time_window > 0:  # Ensure time_window is not zero to avoid division by zero
                throughput = window_size / time_window
                throughputs.append(throughput)

    throughput_df = pd.DataFrame(throughputs, columns=['Throughput'])


    # Calculate average, min, and max throughput
    avg_throughput = throughput_df['Throughput'].mean()
    min_throughput = throughput_df['Throughput'].min()
    max_throughput = throughput_df['Throughput'].max()

    # Create a final DataFrame with the calculated metrics
    # final_df = pd.DataFrame({
    report = {
        'model_id': model_id,
        'avg_throughput(req/s)': avg_throughput,
        'min_throughput(req/s)': min_throughput,
        'max_throughput(req/s)': max_throughput
    }

    return report


def make_risk_levels_report(dataframe: pd.DataFrame, model_id):
    # dataframe = pd.read_csv(file_path)
    dataframe = dataframe.copy(deep= True)
    # Drop rows where 'role' column has missing values
    # indicate the row contain error in recording process
    dataframe.dropna(subset=['role'], inplace=True)

    dataframe['class_object'] = dataframe['class_object'].astype(int)


    class_label_dict = {
        0: "bicycle",
        1: "bus",
        2: "car",
        3: "motorcycle",
        4: "other person",
        5: "other vehicle",
        6: "pedestrian",
        7: "rider",
        8: "traffic light",
        9: "traffic sign",
        10: "trailer",
        11: "train",
        12: "truck"
    }

    def map_label(class_object):
        return class_label_dict.get(class_object, "Unknown")
    
    def misclassification_num(df, true_label, false_label=None):
        subset = df[df['label'] == true_label]
        if false_label:
            misclassified = subset[subset['predict_label'] == false_label]
        else:
            misclassified = subset[subset['predict_label'] != true_label]
        if len(subset) == 0:
            return 0
        return len(misclassified)

    def calculate_risk_level(df):
        df['label'] = df['class_object'].map(map_label)
        df['predict_label'] = df['predict_object'].map(map_label)
        
        # Risk Level 1
        miss_ped_num = misclassification_num(df, "pedestrian")
        miss_car_as_rider_num = misclassification_num(df, "car", "rider")
        total_ped = len(df[df['label'] == "pedestrian"])
        total_car = len(df[df['label'] == "car"])
        risk_level_1 = (miss_ped_num + miss_car_as_rider_num) / (total_ped + total_car)
        print(f"risk level 1: {risk_level_1}")
        print(f"This is total missclassify number for risk level 1: {miss_ped_num + miss_car_as_rider_num} and total object is : {total_ped + total_car}")
        
        # Risk Level 2
        miss_rider_num = misclassification_num(df, "rider")
        miss_car_as_truck_num = misclassification_num(df, "car", "truck")
        miss_bicycle_num = misclassification_num(df, "bicycle")
        total_rider = len(df[df['label'] == "rider"])
        total_truck = len(df[df['label'] == "truck"])
        total_bicycle = len(df[df['label'] == "bicycle"])
        risk_level_2 = (miss_rider_num + miss_car_as_truck_num + miss_bicycle_num) / (total_rider + total_truck + total_bicycle)
        print(f"risk level 2: {risk_level_2}")

        print(f"This is total missclassify number for risk level 2: {miss_rider_num + miss_car_as_truck_num + miss_bicycle_num} and total object is {total_rider + total_truck + total_bicycle}")
        
        # Risk Level 3
        miss_ped_num_rider = misclassification_num(df, "pedestrian", "rider")
        miss_rider_as_ped_num = misclassification_num(df, "rider", "pedestrian")
        miss_motor_as_ped_num = misclassification_num(df, "motorcycle", "pedestrian")
        total_motorcycle = len(df[df['label'] == "motorcycle"])
        risk_level_3 = (miss_ped_num_rider + miss_rider_as_ped_num + miss_motor_as_ped_num) / (total_ped + total_rider + total_motorcycle)
        print(f"risk level 3: {risk_level_3}")

        print(f"This is total missclassify number for risk level 3: {miss_ped_num_rider + miss_rider_as_ped_num + miss_motor_as_ped_num} and total object is {total_ped + total_rider + total_motorcycle}")
        
        return {
            'model_id': model_id,
            'risk_level_1(%)': risk_level_1 * 100,
            'risk_level_2(%)': risk_level_2 * 100, 
            'risk_level_3(%)': risk_level_3 * 100
        }
    report = calculate_risk_level(dataframe)

    return report

def make_report(dfs: List [pd.DataFrame], model_ids: List [str], process_function: Callable, 
                    save_path: List[str], unify_report: bool = True):
    all_reports = []
    
    for dataframe, model_id in zip(dfs, model_ids):
        try:
            report_dict = process_function(dataframe, model_id)
            all_reports.append(report_dict)

            # print(f"This is all report: {all_reports}")
        
        except Exception as e:
            print(f"Encounter error {e} while trying to process")

    if not unify_report:
        print("About to save serveral reports")
        for report, path in zip(all_reports, save_path):
            df = pd.DataFrame(report)
            print(f"{df.head()}")
            # Save the final report to CSV
            print(f"about to save the report to path: {path}")
            df.to_csv(path, index=False)
        return None
    
    # Convert list of dictionaries to DataFrame
    final_report = pd.DataFrame(all_reports)
    # print(final_report.head())

    # Save the final report to CSV
    save_path = save_path[0]
    print(f"about to save the report to path: {save_path}")
    final_report.to_csv(save_path, index=False)


if __name__ == '__main__': 
    parser = argparse.ArgumentParser(description="Argument for Inference Service")

    parser.add_argument('--profile_folder', type= str, help='specify profile folder', 
            default= "artifact/nii/profile_4")
    parser.add_argument('--file_name', type= str, help="specify profiling file name",
                        default= "client.csv")
    # Parse the parameters
    args = parser.parse_args()
    file_name = args.file_name
    profile_folder_path = args.profile_folder
    profile_folder_path = os.path.join(main_path, profile_folder_path)

    subfolders = get_subfolders(profile_folder_path)
    folder_name = get_target_folder_name(profile_folder_path)

    dfs = []
    for subfolder in subfolders:
        df_path = os.path.join(profile_folder_path, subfolder, file_name)
        df = pd.read_csv(df_path)
        dfs.append(preprocess_df(df))
    
    # create root save dir
    save_root_dir = f"result/{folder_name}_result"
    if not os.path.exists(save_root_dir):
        os.makedirs(save_root_dir)

    # make risk level report
    save_path = f'{save_root_dir}/risk_levels_report.csv'
    make_report(dfs= dfs, model_ids= subfolders, save_path= [save_path],
                    process_function= make_risk_levels_report)
    
    # make throughput report
    save_path = f'{save_root_dir}/service_quality.csv'
    make_report(dfs= dfs, model_ids= subfolders, save_path= [save_path],
                    process_function= make_throughput_report)
    
    # make_inference_reports
    inference_quality_root_dir = os.path.join(save_root_dir, "inference_quality")
    if not os.path.exists(inference_quality_root_dir):
        os.mkdir(inference_quality_root_dir)

    save_dirs = [os.path.join(inference_quality_root_dir, f"{subfolder}.csv") for subfolder in subfolders]
    make_report(dfs= dfs, model_ids= subfolders, 
                save_path= save_dirs, unify_report= False,
                process_function= make_inference_report)