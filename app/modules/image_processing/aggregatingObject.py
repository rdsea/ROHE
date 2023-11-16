import pandas as pd
import numpy as np
import time
import concurrent.futures
from threading import Lock
from typing import Callable
import time


from app.object_classification.lib.connectors.quixStream import QuixStreamListener
from app.object_classification.lib.connectors.storage.mongoDBConnector import MongoDBConnector
from app.object_classification.modules.common import TimeLimitedCache


class KafkaStreamAggregatingListener(QuixStreamListener):
    def __init__(self, kafka_address: str, topic_name: str, 
                 aggregate_function: Callable, lock: Lock = None, 
                 config: dict = None, db_connector: MongoDBConnector = None):
        super().__init__(kafka_address, topic_name)
        # print("Enter this initial block")
        self.lock = lock or Lock()
        self.config = config or {}

        self.aggregate_function = aggregate_function

        self.time_limit: int = self.config.get('time_limit') or 5  # in second
        self.min_messages: int = self.config.get('min_messages') or 10

        self.config['max_threads'] = self.config.get('max_threads') or 10
        self.config['valid_time'] = self.config.get('valid_time') or 60
        # print(f"This is the config: {self.config}")

        # self.max_threads = self.config['max_threads']
        # self.valid_time = self.config['valid_time']
        self.db_connector = db_connector

        print(f"This is the db connector: {self.db_connector}")

        self.buffer_dict = {}
        self.already_processed_ids = TimeLimitedCache(window_size= self.config['valid_time'], lock= Lock())
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers= self.config['max_threads'])

    def on_dataframe_received_handler(self, stream, df: pd.DataFrame):

        print("enter this receiving dataframe block")
        # Convert the 'prediction' column to NumPy arrays
        df['prediction'] = df['prediction'].apply(lambda x: np.frombuffer(x, dtype=np.float64))

        with self.lock:
            # Group by 'request_id'
            for req_id, group in df.groupby('request_id'):
                if self.already_processed_ids.contains(req_id):
                    continue
                
                # Convert group DataFrame to list of dicts for more efficient processing
                group_list = group.to_dict(orient='records')
                
                if req_id in self.buffer_dict:
                    self.buffer_dict[req_id]['data'].extend(group_list)
                else:
                    self.buffer_dict[req_id] = {
                        'data': group_list,
                        'timer': time.time()  # Current timestamp
                    }
                    # test aggregate function
                    self.buffer_dict[req_id]['data'].extend(group_list)

            for req_id, info in self.buffer_dict.items():
                self.executor.submit(self.check_and_process, req_id, info)

    # def check_and_process(self, req_id, buffer_data):
    def check_and_process(self, req_id, buffer_data):

        # Check the conditions: Time elapsed or minimum number of messages reached
        elapsed_time = float(time.time() - buffer_data['timer'])
        num_messages = len(buffer_data['data'])
        print(f"This is the elapse time: {elapsed_time} and type of it: {type(elapsed_time)}, this is the num message: {num_messages}")
        print(f"this is the result of time buffer: {elapsed_time >= self.time_limit}")
        
        if elapsed_time >= self.time_limit or num_messages >= self.min_messages:
            print(f"Request_id: {req_id}, elapsed time: {elapsed_time}, current messages: {num_messages} ")
            self.aggregating_process(buffer_data['data'])
            self.buffer_dict.pop(req_id, None)
            self.already_processed_ids.append(req_id)

        
    def aggregating_process(self, data: list):
        aggregated_result: dict = self.aggregate_function(data)
        
        # return aggregated_df
        if self.db_connector:
            print("about to upload data")
            self._save_to_db(data= aggregated_result)


    def _save_to_db(self, data: dict):
        # Convert any numpy arrays to lists
        # data = data.applymap(lambda x: x.tolist() if isinstance(x, np.ndarray) else x)

        print(f"This is the upload data: {data}")
        
        self.db_connector.upload(data= data)