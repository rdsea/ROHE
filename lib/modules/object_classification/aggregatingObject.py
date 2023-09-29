import pandas as pd
import numpy as np
import time
import concurrent.futures
from threading import Lock
from collections import deque
import time

from lib.service_connectors.quixStreamConsumer import KafkaStreamListener
from lib.service_connectors.mongoDBConnector import MongoDBConnector


class TimeBuffer:
    def __init__(self, window_size=60, lock: Lock = None):
        self.buffer = deque()
        self.window_size = window_size  # in seconds
        self.last_cleanup_time = time.time()  # initialized to current time
        self.lock = lock or Lock()

    def append(self, item):
        current_time = time.time()
        if current_time - self.last_cleanup_time >= self.window_size:
            with self.lock:
                self.clean_buffer()
                self.last_cleanup_time = current_time  # update last cleanup time

        self.buffer.append({'id': item, 'timestamp': current_time})
    
    def clean_buffer(self):
        current_time = time.time()
        while self.buffer and (current_time - self.buffer[0]['timestamp'] > self.window_size):
            self.buffer.popleft()
    
    def contains(self, item):
        return any(entry['id'] == item for entry in self.buffer)


class KafkaStreamAggregatingListener(KafkaStreamListener):
    def __init__(self, kafka_address: str, topic_name: str, lock: Lock = None, config: dict = None, db_connector: MongoDBConnector = None):
        super().__init__(kafka_address, topic_name)
        # print("Enter this initial block")
        self.lock = lock or Lock()
        self.config = config or {}

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
        self.already_processed_ids = TimeBuffer(window_size= self.config['valid_time'], lock= Lock())
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers= self.config['max_threads'])

    def on_dataframe_received_handler(self, stream, df: pd.DataFrame):
        # print("enter this receiving dataframe block")
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
                
                self.executor.submit(self.check_and_process, req_id, self.buffer_dict[req_id])

    def check_and_process(self, req_id, buffer_data):
        # Check the conditions: Time elapsed or minimum number of messages reached
        elapsed_time = time.time() - buffer_data['timer']
        num_messages = len(buffer_data['data'])
        
        if elapsed_time >= self.time_limit or num_messages >= self.min_messages:
            print(f"Request_id: {req_id}, elapsed time: {elapsed_time}, current messages: {num_messages} ")
            self.aggregating_process(req_id, buffer_data['data'])
            self.buffer_dict.pop(req_id, None)
            self.already_processed_ids.append(req_id)

        
    def aggregating_process(self, req_id, data):
        # Perform the aggregating process on the data
        # Convert list of dicts back to DataFrame for aggregations
        df = pd.DataFrame(data)
        print(f"Request ID : {req_id}, len of the dataframe: {len(df)}")
        
        def mean_prediction(group):
            arrays = group.values.tolist()
            return np.mean(np.array(arrays), axis=0)
        
        def aggregate_instances(group):
            return ','.join(group.values.tolist())

        def pipeline_instances(group):
            return ','.join(group.values.tolist())
    
        aggregated_df = df.groupby('request_id').agg({
            'prediction': mean_prediction,
            # 'pipeline_id': 'first',
            'pipeline_id': pipeline_instances,
            'inference_model_id': aggregate_instances
        }).reset_index()

        # Display the aggregated results
        for index, row in aggregated_df.iterrows():
            print(f"Request ID: {row['request_id']}, Aggregate Prediction: {row['prediction']}, "
                  f"Pipeline ID: {row['pipeline_id']}, Inference Instances: {row['inference_model_id']}")
        
        print("End of aggregating process\n\n\n\n")

        # return aggregated_df
        if self.db_connector:
            self._save_to_db(data= aggregated_df)


    def _save_to_db(self, data: pd.DataFrame):
        # Convert any numpy arrays to lists
        data = data.applymap(lambda x: x.tolist() if isinstance(x, np.ndarray) else x)
        
        self.db_connector.upload(data= data)