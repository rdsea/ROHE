from collections import deque
import time

class EventBuffer(object):
    def __init__(self, size=100):
        self.size = size   
        self.buffer = deque(maxlen=size)
    
    def append(self, item):
        # add a new entry to the right side
        self.buffer.append(item) 
    
    def get(self):
        # get all item as a list
        return list(self.buffer)
    
    def pop(self):
        # return and remove the rightmost item
        self.buffer.pop()

class TimeBuffer(object):
    def __init__(self, windowside=100, maxsize=100000):
        self.size = maxsize   
        self.buffer = deque(maxlen=maxsize)
        self.windowside = windowside
    
    def append(self, item):
        # add a new entry to the right side
        self.buffer.append(item) 
    
    def get(self):
        # get all item as a list within the window time
        current_time = time.time()
        while len(self.buffer != 0):
            if (current_time - self.buffer[0]["metadata"]["timestamp"]) > self.windowside:
                self.buffer.popleft()
        return list(self.buffer)
    
    def pop(self):
        # return and remove the rightmost item
        self.buffer.pop()