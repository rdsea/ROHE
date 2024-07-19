from abc import ABC


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
