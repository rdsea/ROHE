import concurrent.futures
import time
from threading import Lock
from typing import Callable

import app.object_classification.modules.model_aggregating_functions as aggregating_func
import app.object_classification.modules.utils as pipeline_utils
import numpy as np

# import quixstreams as qx
import pandas as pd
from app.object_classification.lib.connectors.quixStream import (
    QuixStreamDataframeHandler,
)
from app.object_classification.lib.connectors.storage.mongoDBConnector import (
    MongoDBConnector,
)
from app.object_classification.modules.common import MongoDBInfo, TimeLimitedCache
from core.common.roheObject import RoheObject


class AggregatingServiceExecutor(RoheObject):
    def __init__(self, config: dict, lock: Lock = None, log_level: int = 2):
        super().__init__(logging_level=log_level)

        self.lock = lock or Lock()
        self.config = config or {}
        self.conf = config
        # load processing function
        self.aggregating_func: Callable = pipeline_utils.get_function_from_module(
            module=aggregating_func,
            func_name=self.conf["aggregating"]["aggregating_func"]["func_name"],
        )
        print(f"\n\n\nthis is the aggregating function: {self.aggregating_func}")

        # self.config['max_threads'] = self.config.get('aggregating', {}).get('max_threads') or 10
        # self.config['valid_time'] = self.config.get('aggregating', {}).get('valid_time') or 60
        # self.time_limit: int = self.config.get('aggregating', {}).get('time_limit') or 5  # in second
        # self.min_message: int = self.config.get('aggregating', {}).get('min_messages') or 10
        max_thread = int(self.config["aggregating"]["threading"]["max_thread"])
        cache_valid_time = pipeline_utils.parse_time(
            self.config["aggregating"]["cache"]["valid_time"]
        )
        self.time_limit = pipeline_utils.parse_time(
            self.config["aggregating"]["aggregating_func"]["time_limit"]
        )
        self.min_message: int = self.config["aggregating"]["aggregating_func"][
            "min_message"
        ]

        self.buffer_dict = {}
        # self.already_processed_ids = TimeLimitedCache(window_size= self.config['valid_time'], lock= Lock())
        # self.executor = concurrent.futures.ThreadPoolExecutor(max_workers= self.config['max_threads'])

        self.already_processed_ids = TimeLimitedCache(
            window_size=cache_valid_time, lock=Lock()
        )
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_thread)

        # self.db_connector: MongoDBConnector = MongoDBConnector(**self.conf['mongodb'])
        mongodb_info = MongoDBInfo(**config["external_services"]["mongodb"])
        self.db_connector = MongoDBConnector(db_info=mongodb_info)
        print(f"\n\n\nthis is db connector: {self.db_connector}")

        self.quix_stream_listener = QuixStreamDataframeHandler(
            kafka_address=self.conf["external_services"]["kafka"]["address"],
            topic_name=self.conf["external_services"]["kafka"]["topic_name"],
            host_object=self,
        )

    def run(self):
        self.quix_stream_listener.run()

    def change_aggregating_function(self, func_name) -> bool:
        # the function must be defined in the image_processing_functions file in modules
        func: Callable = pipeline_utils.get_function_from_module(
            module=aggregating_func, func_name=func_name
        )
        if func is not None:
            self.aggregating_func = func
            return True
        else:
            return False

    # def change_

    def on_receive_data_as_dataframe(self, stream, df: pd.DataFrame):
        print("enter this receiving dataframe block")
        # Convert the 'prediction' column to NumPy arrays
        df["prediction"] = df["prediction"].apply(
            lambda x: np.frombuffer(x, dtype=np.float64)
        )

        print(
            f"this is the len of already processed id list: {len(self.already_processed_ids.buffer)}"
        )
        with self.lock:
            # Group by 'request_id'
            for req_id, group in df.groupby("request_id"):
                # pass the already processed id
                if self.already_processed_ids.contains(req_id):
                    continue

                # Convert group DataFrame to list of dicts for more efficient processing
                group_list = group.to_dict(orient="records")

                if req_id in self.buffer_dict:
                    self.buffer_dict[req_id]["data"].extend(group_list)
                else:
                    self.buffer_dict[req_id] = {
                        "data": group_list,
                        "timer": time.time(),  # Current timestamp
                    }
                    # # test aggregate function - emulate as more than one inference server send result to the aggregating server
                    # self.buffer_dict[req_id]['data'].extend(group_list)

            req_ids = self.buffer_dict.keys()
            # for req_id, info in self.buffer_dict.items():
            for req_id in req_ids:
                print(f"This is the req id: {req_id}")
                # self.executor.submit(self.check_and_process, req_id, info)
                self.executor.submit(
                    self.check_and_process, req_id, self.buffer_dict[req_id]
                )

    # def check_and_process(self, req_id, buffer_data):
    def check_and_process(self, req_id, buffer_data):
        # Check the conditions: Time elapsed or minimum number of messages reached
        elapsed_time = float(time.time() - buffer_data["timer"])
        num_messages = len(buffer_data["data"])
        print(
            f"This is the elapse time: {elapsed_time} and type of it: {type(elapsed_time)}, this is time limit: {self.time_limit}"
        )
        print(f"This is elapse time and time limit: {elapsed_time}, {self.time_limit}")
        print(f"this is the result of time buffer: {elapsed_time >= self.time_limit}")

        if elapsed_time >= self.time_limit or num_messages >= self.min_message:
            # if req_id not in self.already_processed_ids:
            if not self.already_processed_ids.contains(req_id):
                print(
                    f"Request_id: {req_id}, elapsed time: {elapsed_time}, current messages: {num_messages}"
                )
                self.aggregating_process(buffer_data["data"])
                self.buffer_dict.pop(req_id, None)
                self.already_processed_ids.append(req_id)

    def aggregating_process(self, data: list):
        # print(f"\n\n\nenter this block")
        aggregated_result: dict = self.aggregating_func(data)

        # print(f"\n\n\n this is the result: {aggregated_result}")

        # return aggregated_df
        if self.db_connector:
            print("about to upload data")
            self._save_to_db(data=aggregated_result)

    def _save_to_db(self, data: dict):
        # Convert any numpy arrays to lists
        # data = data.applymap(lambda x: x.tolist() if isinstance(x, np.ndarray) else x)

        print(f"This is the upload data: {data}")

        self.db_connector.upload(data=data)
