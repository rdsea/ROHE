import time
from abc import ABC
from collections import deque
from threading import Lock


class MessageObject(ABC):
    def to_dict(self):
        return {
            key: value if not isinstance(value, MessageObject) else value.to_dict()
            for key, value in self.__dict__.items()
        }


class StorageInfo(MessageObject):
    """ """

    def __init__(
        self, endpoint_url, bucket_name: str, access_key: str = "", secret_key: str = ""
    ):
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name


class MongoDBInfo:
    """ """

    def __init__(
        self,
        username: str,
        password: str,
        host: str,
        port: int,
        database_name: str,
        collection_name: str,
    ):
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.database_name = database_name
        self.collection_name = collection_name


class TimeLimitedCache:
    """ """

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

        self.buffer.append({"id": item, "timestamp": current_time})

    def clean_buffer(self):
        current_time = time.time()
        while self.buffer and (
            current_time - self.buffer[0]["timestamp"] > self.window_size
        ):
            self.buffer.popleft()

    def contains(self, item):
        return any(entry["id"] == item for entry in self.buffer)


class InferenceEnsembleState:
    """
    this class intend to specify the direction of the inference result:
    whether to send the result to the database storage or (mode = False)
    to send it to aggregation server via kafka topic (mode = True)

    """

    def __init__(self, mode: bool):
        self.mode = mode

    def change_mode(self, mode: bool):
        self.mode = mode

    def get_mode(self) -> bool:
        return self.mode


# TimeParser
