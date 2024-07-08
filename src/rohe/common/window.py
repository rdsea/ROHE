import time
from collections import deque

import pandas as pd


class EventBuffer:
    # Object handling Event window as a buffer
    def __init__(self, size=100):
        self.size = size
        self.buffer = deque(maxlen=size)

    def append(self, item):
        # add a new entry to the right side
        # item should be DataFrame
        self.buffer.append(item)

    def get(self, dataframe=False):
        if dataframe:
            df_list = list(self.buffer)
            df = df_list[0]
            if isinstance(df, pd.DataFrame):
                for i in range(1, len(df_list)):
                    df = pd.concat([df, df_list[i]], ignore_index=True)
                return df
        # get all item as a list
        return list(self.buffer)

    def pop(self):
        # return and remove the rightmost item
        self.buffer.pop()


class TimeBuffer:
    def __init__(self, windowside=100, maxsize=100000):
        # Object handling Time window as a buffer
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
            if (
                current_time - self.buffer[0]["metadata"]["timestamp"]
            ) > self.windowside:
                self.buffer.popleft()
        return list(self.buffer)

    def pop(self):
        # return and remove the rightmost item
        self.buffer.pop()
