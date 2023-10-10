import os
import pandas as pd


def get_class_label_dict() -> dict:
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
    return class_label_dict

def get_subfolders(path) -> list:
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

def get_target_folder_name(folder_path) -> str:
    return os.path.basename(folder_path)

def preprocess_df(df: pd.DataFrame) -> pd.DataFrame:
    processed_df = df
    # Drop rows where 'role' column has missing values
    # indicate the row contain error in recording process
    # processed_df.dropna(subset=['class_object','role', 'accuracy', 'confidence', 'responseTime'], inplace=True)
    processed_df.dropna(how= 'any', inplace= True)

    if 'class_object' in processed_df.columns:
        processed_df['class_object'] = processed_df['class_object'].astype(int)

    if 'confidence' in processed_df.columns:
        # ensure all field is numberic and not null
        processed_df['confidence'] = pd.to_numeric(processed_df['confidence'], errors='coerce')
        # Drop rows where 'confidence' is not between 0 and 1
        processed_df = processed_df[processed_df['confidence'].between(0, 1, inclusive=True)]

    # Convert to appropriate data types
    processed_df['timestamp'] = pd.to_numeric(processed_df['timestamp'], errors='coerce')

    # Reset the index after dropping rows
    processed_df.reset_index(drop=True, inplace=True)
    
    return processed_df


def get_throughtput_info(dataframe: pd.DataFrame,
                           window_size: int = 100,
                           step_size: int = 1) -> dict:
    dataframe = dataframe.copy(deep= True)

    # Sort the dataframe by 'timestamp'
    dataframe.sort_values(by='timestamp', inplace=True)

    # Calculate runtime in seconds
    start_time = dataframe.iloc[0]['timestamp']
    end_time = dataframe.iloc[-1]['timestamp']
    runtime = end_time - start_time

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
    report = {
        'avg_throughput(req/s)': avg_throughput,
        'min_throughput(req/s)': min_throughput,
        'max_throughput(req/s)': max_throughput,
        'runtime': runtime,
    }

    return report


def get_risk_levels_info(dataframe: pd.DataFrame,
                         class_label_dict: dict) -> dict:
    dataframe = dataframe.copy(deep= True)


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
            'risk_level_1(%)': risk_level_1 * 100,
            'risk_level_2(%)': risk_level_2 * 100, 
            'risk_level_3(%)': risk_level_3 * 100
        }
    
    report = calculate_risk_level(dataframe)

    return report

def get_model_info_from_provider(dataframe: pd.DataFrame) -> dict:
    '''
    return:
         - no_layer, 
         - no_param, 
         - image_height,
         - image_width,
    '''

    dataframe = dataframe.copy(deep= True)

    no_layer = dataframe['no_layer'].iloc[0]
    no_param = dataframe['no_parameters'].iloc[0]
    image_height = dataframe['image_height'].iloc[0]
    image_width = dataframe['image_width'].iloc[0]

    result =  {
     'no_layer': int(no_layer),
     'no_param': int(no_param),
     'image_height': int(image_height),
     'image_width': int(image_width)
     }
    
    return result


def get_label_distribution(dataframe: pd.DataFrame, separator: str = "-") -> dict:
    label_dist = dataframe['class_object'].value_counts().to_dict()

    label_dist_value = separator.join(map(str, label_dist.values()))
    label_dist = {"total_sample": len(dataframe),
                "label_dist": label_dist_value, }
    return label_dist

def get_inference_quality_info(dataframe: pd.DataFrame,
                          class_label_dict: dict) -> pd.DataFrame:
    dataframe = dataframe.copy(deep= True)


    grouped = dataframe.groupby('class_object')

    # For avg_confidence_correct_prediction
    correct_predictions = dataframe[dataframe['accuracy'] == 1]
    avg_confidence_correct = correct_predictions.groupby('class_object')['confidence'].mean()

    # For avg_confidence_incorrect_prediction
    incorrect_predictions = dataframe[dataframe['accuracy'] == 0]
    avg_confidence_incorrect = incorrect_predictions.groupby('class_object')['confidence'].mean()

    # For percentage_confidence_over_50
    conf_over_50 = dataframe[dataframe['confidence'] > 0.5].groupby('class_object').size()
    total_counts = dataframe.groupby('class_object').size()
    percent_conf_over_50 = (conf_over_50 / total_counts)

    # Create a new DataFrame to hold the calculated metrics
    model_quality = pd.DataFrame({
        'accuracy': grouped['accuracy'].sum() / grouped['accuracy'].count(),  
        'min_confidence': grouped['confidence'].min(),
        'avg_confidence': grouped['confidence'].mean(), 
        'percentage_confidence_over_50': percent_conf_over_50,
        'avg_confidence_correct_prediction': avg_confidence_correct,
        'avg_confidence_incorrect_prediction': avg_confidence_incorrect,
        'min_response_time': grouped['responseTime'].min(),
        'avg_response_time': grouped['responseTime'].mean(), 
        'max_response_time': grouped['responseTime'].max(),
    }).reset_index()


    model_quality.rename(columns={'class_object': 'class'}, inplace=True)

    model_quality.head()


    model_quality['class_label'] = model_quality['class'].map(class_label_dict)

    return model_quality