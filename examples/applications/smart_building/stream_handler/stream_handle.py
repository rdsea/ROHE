import cv2
import zmq
import torch
import threading
import time
import numpy as np
import time
import copy
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from enum import Enum
logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)


MAX_BUFFER_WINDOW = 60
DEFAULT_FRAME_RATE = 30
FRAME_COUNT_INTERVAL = 100
TIMESERIES_COUNT_INTERVAL = 500
MAX_TIMESERIES_WINDOW = 1000

class DataType(int, Enum):
    TIME_SERIES = 0
    VIDEO = 1
    IMAGE = 2
    AUDIO = 3
    TEXT = 4
    
class ModalityType(int, Enum):
    TIME_SERIES = 0
    VIDEO = 1
    
class StreamStatus(int, Enum):
    ACTIVE = 0
    INACTIVE = 1
    PAUSED = 2
    STOPPED = 3

class ModelFamily(int, Enum):
    X3D = 0
    MINI_ROCKET = 1

class ModelTransform(tuple, Enum):
    X3D = (2, 0, 1)

class StreamHandler():
    def __init__(self, host:str, port:int, data_type:int, data_shape:list, sample_index:int, model_family:int, buffer_size:int=MAX_BUFFER_WINDOW, frame_rate:int=DEFAULT_FRAME_RATE, timestamp_index:int=0, data_axis:int=1, stream_id:Optional[str]=None, modality:int=ModalityType.TIME_SERIES.value):
        if stream_id != None:
            self.stream_id = stream_id
        else:
            self.stream_id = str(uuid.uuid4())
        self.host = host
        self.port = port
        self.buffer_lock = threading.Lock()
        self.data_type = data_type
        self.modality = modality
        self.shape = data_shape
        self.sample_index = sample_index
        self.buffer = None
        self.data_count = 0
        self.model_family = model_family
        self.buffer_size = buffer_size
        self.frame_rate = frame_rate
        self.max_buffer_size = self.frame_rate * self.buffer_size
        self.timestamp_index = timestamp_index
        self.data_axis = data_axis
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.max_timestamp = time.perf_counter()
        try:
            data_shape[sample_index] = 0
            self.buffer = torch.empty(data_shape)
        except Exception as e:
            logging.error(f"Error in creating buffer in stream handler: {e}")
        self.model_transform = None
        try:
            if self.model_family == ModelFamily.X3D.value:
                self.model_transform = ModelTransform.X3D.value
        except Exception as e:
            logging.error(f"Error in setting model transform in stream handler: {e}")
                
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.status = StreamStatus.INACTIVE.value
        
    def start_consume(self):
        self.socket.connect(f"tcp://{self.host}:{self.port}")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
        self.status = StreamStatus.ACTIVE.value
        if self.data_type == int(DataType.VIDEO.value):
            self.executor.submit(self.consume_video)
        elif self.data_type == int(DataType.TIME_SERIES.value):
            self.executor.submit(self.consume_time_series)
    
    def consume_video(self):
        try:
            if self.model_family == ModelFamily.X3D.value:
                if self.model_transform == None:
                    logging.error("Model transform not set")
                    return
            while self.status == StreamStatus.ACTIVE.value:
                try:
                    frame = self.socket.recv()
                    frame = cv2.imdecode(np.frombuffer(frame, np.uint8), cv2.IMREAD_COLOR)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convert to RGB
                    frame = np.transpose(frame, self.model_transform)  # Change shape to [channels, height, width]
                    frame_tensor = torch.tensor(frame, dtype=torch.float32) / 255.0 # Convert to tensor and normalize
                    frame_tensor = frame_tensor.unsqueeze(self.sample_index) # Shape: [channels, 1, height, width]
                    with self.buffer_lock:
                        self.buffer = torch.cat((self.buffer, frame_tensor), dim=self.sample_index)
                        if self.buffer.size(self.sample_index) > self.max_buffer_size:
                            self.buffer = self.buffer.narrow(self.sample_index, 1, self.max_buffer_size)
                            
                    self.data_count += 1
                    if self.data_count % FRAME_COUNT_INTERVAL == 0:
                        logging.info(f"Video stream {self.stream_id} receive: {self.data_count} frames")
                except Exception as e:
                    logging.error(f"Error in adding video frame to buffer: {e}")
        except Exception as e:
            logging.error(f"Error in consuming video frame: {e}")
    
    def consume_time_series(self):
        try:
            if self.model_family == ModelFamily.MINI_ROCKET.value:
                while self.status == StreamStatus.ACTIVE.value:
                    try:
                        message = self.socket.recv_string()
                        data_array = message.split(",")
                        current_time = float(time.perf_counter())
                        data_array[self.timestamp_index] = current_time
                        data_array = [float(x) for x in data_array] 
                        data_tensor = torch.tensor(data_array, dtype=torch.float32).unsqueeze(self.sample_index)
                        with self.buffer_lock:
                            self.buffer = torch.cat((self.buffer, data_tensor), dim=self.sample_index)
                            if self.buffer.size(self.sample_index) > MAX_TIMESERIES_WINDOW:
                                self.buffer = self.buffer.narrow(self.sample_index, 1, MAX_TIMESERIES_WINDOW)
                        self.data_count += 1
                        if self.data_count % TIMESERIES_COUNT_INTERVAL == 0:
                            logging.info(f"Time-series stream {self.stream_id} receive: {self.data_count} data points")
                    except Exception as e:
                        logging.error(f"Error in adding time series data: {e}")
        except Exception as e:
            logging.error(f"Error in consuming time series data: {e}")
    
    def process_data(self, time_window, frame_rate=DEFAULT_FRAME_RATE):
        try:
            if self.model_family == ModelFamily.X3D.value:
                window_data = self.video_processing(time_window, frame_rate)
            elif self.model_family == ModelFamily.MINI_ROCKET.value:
                window_data = self.time_series_processing(time_window)
            return window_data
        except Exception as e:
            logging.error(f"Error in processing data: {e}")
            return None
            
    def video_processing(self, time_window, frame_rate):
        try:
            with self.buffer_lock:
                # Calculate the number of frames to select
                buffer_data = copy.deepcopy(self.buffer)
            num_frames_to_select = frame_rate * time_window
            # Calculate the starting index for the latest data
            start_index = buffer_data.size(self.sample_index) - num_frames_to_select

            # Ensure the start_index is not negative
            start_index = max(start_index, 0)
            no_selected_frames = min(num_frames_to_select, buffer_data.size(self.sample_index) - start_index)
            window_data = buffer_data.narrow(self.sample_index, start_index, no_selected_frames)
            return window_data
        except Exception as e:
            logging.error(f"Error in video processing: {e}")
            return None
    def time_series_processing(self, time_window):
        try:
            current_time = float(time.perf_counter())
            with self.buffer_lock:
                # Select only one column in data_axis and timestamp column
                timestamp_col = self.buffer.narrow(self.data_axis, self.timestamp_index, 1).squeeze()
                i_max_timestamp = float(timestamp_col.max())
                if i_max_timestamp > self.max_timestamp:
                    self.max_timestamp = i_max_timestamp
                
                threshold = current_time - time_window
                mask = timestamp_col >= threshold 
                mask = mask.squeeze()
                buffer_data = self.buffer[mask]     
                return buffer_data
        except Exception as e:
            logging.error(f"Error in time series processing: {e}")
            return None
    
    def stop_consume(self):
        self.status = StreamStatus.INACTIVE.value
        self.executor.shutdown(wait=False)
        self.socket.close()
        self.context.term()
        
