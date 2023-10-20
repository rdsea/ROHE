import os
import pandas as pd


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
def get_class_label_dict() -> dict:
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
        'avg_throughput': avg_throughput,
        'min_throughput': min_throughput,
        'max_throughput': max_throughput,
        'runtime': runtime,
    }

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


def get_label_distribution(dataframe: pd.DataFrame, class_label_dict: dict) -> dict:
    label_dist = dataframe['class_object'].value_counts().to_dict()

    label_dist = {class_label_dict[key]: value for key, value in label_dist.items()}

    print(f"\n\n\nThis is label dict: {label_dist}")
    
    label_dist = {"total_sample": len(dataframe),
                "label_dist": label_dist}
    return label_dist


def get_inference_quality_info(dataframe: pd.DataFrame,
                          class_label_dict: dict) -> pd.DataFrame:
    dataframe = dataframe.copy(deep= True)


    grouped = dataframe.groupby('class_object')

    # For avg_confidence_correct_prediction
    correct_predictions = dataframe[dataframe['accuracy'] == 1]
    # print(f"\n\n\nThis is the average not by class: {correct_predictions['confidence'].mean()}, this is the type: {type(correct_predictions['confidence'].mean())}")

    avg_confidence_correct = correct_predictions.groupby('class_object')['confidence'].mean()

    # For avg_confidence_incorrect_prediction
    incorrect_predictions = dataframe[dataframe['accuracy'] == 0]
    avg_confidence_incorrect = incorrect_predictions.groupby('class_object')['confidence'].mean()

    # For percentage_confidence_over_50
    conf_over_50 = dataframe[dataframe['confidence'] > 0.5].groupby('class_object').size()
    total_counts = dataframe.groupby('class_object').size()
    percent_conf_over_50 = (conf_over_50 / total_counts)


    print(f"\n\n\nThis is percent conf over 50: {percent_conf_over_50}, the type is: {type(percent_conf_over_50)}")    # Create a new DataFrame to hold the calculated metrics
    print(f"\n\n\nThis is confidence metric: {grouped['confidence'].min()}, the type is: {type(grouped['confidence'].min())}")    # Create a new DataFrame to hold the calculated metrics

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


def get_overall_inference_quality_info(dataframe: pd.DataFrame) -> dict:
    dataframe = dataframe.copy(deep= True)

    # For avg_confidence_correct_prediction
    correct_predictions = dataframe[dataframe['accuracy'] == 1]
    avg_confidence_correct = correct_predictions['confidence'].mean()

    # For avg_confidence_incorrect_prediction
    incorrect_predictions = dataframe[dataframe['accuracy'] == 0]
    avg_confidence_incorrect = incorrect_predictions['confidence'].mean()


    # For percentage_confidence_over_50
    conf_over_50 = len(dataframe[dataframe['confidence'] > 0.5])
    total_counts = len(dataframe)
    percent_conf_over_50 = (conf_over_50 / total_counts)

    result = {
        'accuracy': dataframe['accuracy'].sum() / dataframe['accuracy'].count(),  
        'min_confidence': dataframe['confidence'].min(),
        'avg_confidence': dataframe['confidence'].mean(), 
        'percentage_confidence_over_50': percent_conf_over_50,
        'avg_confidence_correct_prediction': avg_confidence_correct,
        'avg_confidence_incorrect_prediction': avg_confidence_incorrect,
        'min_response_time': dataframe['responseTime'].min(),
        'avg_response_time': dataframe['responseTime'].mean(), 
        'max_response_time': dataframe['responseTime'].max(),
    }


    return result