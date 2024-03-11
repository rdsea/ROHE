import pymongo
import sys, os
import pandas as pd
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)



def estimate_miss_rate(model_name,mdb_client, db_name, coll_name, main_class, sub_class = None, window = 1000):
    db = mdb_client[db_name]
    collection = db[coll_name]
    filter_criteria = {"label_class": main_class, "model": model_name}
    sort_criteria = [("timestamp", pymongo.ASCENDING)]
    results = collection.find(filter_criteria).sort(sort_criteria).limit(window)
    result_list = list(results)
    df = pd.DataFrame(result_list, columns=result_list[0].keys())
    if sub_class == None:
        filtered_df = df[(df['accuracy'] == 0)]
    else:
        filtered_df = df[(df['predicted_class'] == sub_class)]
    return len(filtered_df)/len(df)
    
        
def estimate_accuracy(model_name,mdb_client, db_name, coll_name = None, window = 10000):
    db = mdb_client[db_name]
    collection = db[coll_name]
    filter_criteria = {"model": model_name}
    sort_criteria = [("timestamp", pymongo.ASCENDING)]
    results = collection.find(filter_criteria).sort(sort_criteria).limit(window)
    result_list = list(results)
    df = pd.DataFrame(result_list, columns=result_list[0].keys())
    filtered_df = df[(df['accuracy'] == 1)]
    return len(filtered_df)/len(df)