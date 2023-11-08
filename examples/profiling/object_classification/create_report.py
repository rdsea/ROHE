import os, sys
import pandas as pd
import argparse

import qoa4ml.qoaUtils as qoa_utils

# set the ROHE to be in the system path
from dotenv import load_dotenv
load_dotenv()

main_path = os.getenv('ROHE_PATH')
print(f"This is main path: {main_path}")
sys.path.append(main_path)

# from utils import *
import profiling_utils

if __name__ == '__main__': 
    parser = argparse.ArgumentParser(description="Argument for Inference Service")

    parser.add_argument('--profile_folder', type= str, help='specify profile folder', 
            # default= "artifact/nii/profile_4")
            # default= "examples/profiling/object_classification/raw_data")
            default= "lib/modules/profiling/result/class_0")
            # default= "lib/modules/profiling/result/raw_data")

# lib/modules/profiling/result/class_0

    # Parse the parameters
    args = parser.parse_args()
    profile_folder_path = args.profile_folder
    profile_folder_path = os.path.join(main_path, profile_folder_path)

    client_file_name = 'client.csv'
    provider_file_name = 'provider.csv'

    subfolders = profiling_utils.get_subfolders(profile_folder_path)  
    folder_name = profiling_utils.get_target_folder_name(profile_folder_path)

    # create root save dir
    save_root_dir = f"result/{folder_name}_result"
    inference_root_dir = os.path.join(save_root_dir, 'inference_quality')
    if not os.path.exists(inference_root_dir):
        os.makedirs(inference_root_dir)
    # if not os.path.exists(save_root_dir):
    #     os.makedirs(save_root_dir)

    clients = []
    providers = []
    dict_object = {}
    for subfolder in subfolders:
        client_df_path = os.path.join(profile_folder_path, subfolder, client_file_name)
        provider_df_path = os.path.join(profile_folder_path, subfolder, provider_file_name)

        client = pd.read_csv(client_df_path)
        provider = pd.read_csv(provider_df_path)

        clients.append(client)
        providers.append(provider)
        dict_object[subfolder] = {'client': client,
                                'provider': provider,}
    
    # 
    combined_info = []
    class_label_dict = profiling_utils.get_class_label_dict()
    for model_id, data in dict_object.items():
        client = data['client']
        provider = data['provider']

        processed_client = profiling_utils.preprocess_df(client)
        processed_provider= profiling_utils.preprocess_df(provider)

        client_throughput_info = profiling_utils.get_throughtput_info(processed_client)

        risk_level_info = profiling_utils.get_risk_levels_info(dataframe= processed_client, 
                                            class_label_dict= class_label_dict)

        model_info = profiling_utils.get_model_info_from_provider(dataframe= processed_provider)
        label_dist = profiling_utils.get_label_distribution(dataframe= processed_client)

        inference_quality_info = profiling_utils.get_inference_quality_info(dataframe= processed_client,
                                                            class_label_dict= class_label_dict)

        overall_quality_info = profiling_utils.get_overall_inference_quality_info(dataframe= processed_client)                                                    
        save_dir = os.path.join(inference_root_dir, f"{model_id}.csv")
        
        print(f"this is the save dir: {save_dir}")
        inference_quality_info.to_csv(save_dir, index= False)

        identity = {'model_id': model_id}

        #  temporarily fixed now
        resource = profiling_utils.get_resource(hostname= "aaltosea-P620" )

        resource = {"resource": resource}
        # Combine dictionaries
        info = {**identity, **client_throughput_info, **model_info, **risk_level_info, **label_dist, **overall_quality_info, **resource}

        combined_info.append(info)

    # Convert to DataFrame
    service_report = pd.DataFrame(combined_info)
    save_dir = os.path.join(save_root_dir, "service_report.csv")
    service_report.to_csv(save_dir, index=False)

    print("\n\n\n")
    print(service_report.head())
    print("\n\n\n")