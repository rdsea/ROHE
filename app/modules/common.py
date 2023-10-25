from collections import deque
from threading import Lock
import time



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