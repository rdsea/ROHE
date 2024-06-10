import logging
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from ..lib.common.mongo_utils import get_mdb_client

logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)


class DBConf(BaseModel):
    url: str
    prefix: str
    username: str
    password: str


class DBCollection(BaseModel):
    database: str
    collection: str


class DBClient(ABC):
    def __init__(self, db_config: DBConf) -> None:
        try:
            super().__init__()
            self.db_config = db_config
        except Exception as e:
            logging.error("Error in __init__ DBClient: {}".format(e))

    @abstractmethod
    def get(self, collection: DBCollection, query: Any) -> dict:
        """Return data"""
        return {}

    def to_dict(self) -> dict:
        return self.db_config.dict()


class MDBClient(DBClient):
    def __init__(self, mdb_config: DBConf) -> None:
        try:
            super().__init__(mdb_config)

            self.mdb_client = get_mdb_client(self.db_config)
        except Exception as e:
            logging.error("Error in __init__ MDBClient: {}".format(e))

    def get(self, db_collection: DBCollection, query: Any) -> dict:
        try:
            if self.mdb_client is not None:
                db = self.mdb_client[db_collection.database]
                collection = db[db_collection.collection]
                data = collection.aggregate(query)
            return data
        except Exception as e:
            logging.error("Error in `get` MDBClient: {}".format(e))
            return {}

    def insert_one(self, db_collection: DBCollection, data: dict):
        try:
            if self.mdb_client is not None:
                db = self.mdb_client[db_collection.database]
                collection = db[db_collection.collection]
                response = collection.insert_one(data)
            return response
        except Exception as e:
            logging.error("Error in `insert_one` MDBClient: {}".format(e))
            return {}

    def insert_many(self, db_collection: DBCollection, data: list):
        try:
            if self.mdb_client is not None:
                db = self.mdb_client[db_collection.database]
                collection = db[db_collection.collection]
                response = collection.insert_many(data)
            return response
        except Exception as e:
            logging.error("Error in `insert_many` MDBClient: {}".format(e))
            return {}

    def delete_many(self, db_collection: DBCollection, data: dict):
        try:
            if self.mdb_client is not None:
                db = self.mdb_client[db_collection.database]
                collection = db[db_collection.collection]
                response = collection.delete_many(data)
            return response
        except Exception as e:
            logging.error("Error in `delete_many` MDBClient: {}".format(e))
            return {}

    def find(self, db_collection: DBCollection, query: Any) -> dict:
        try:
            if self.mdb_client is not None:
                db = self.mdb_client[db_collection.database]
                collection = db[db_collection.collection]
                data = collection.find(query)
            return data
        except Exception as e:
            logging.error("Error in `find` MDBClient: {}".format(e))
            return {}

    def aggregate(
        self, db_collection: DBCollection, find_query: Any, sort_query: Any
    ) -> dict:
        try:
            if self.mdb_client is not None:
                db = self.mdb_client[db_collection.database]
                collection = db[db_collection.collection]
                data = collection.find(find_query).sort(sort_query)
            return data
        except Exception as e:
            logging.error("Error in `find` MDBClient: {}".format(e))
            return {}

    def drop(self, db_collection: DBCollection) -> dict:
        try:
            if self.mdb_client is not None:
                db = self.mdb_client[db_collection.database]
                collection = db[db_collection.collection]
                collection.drop()
            return True
        except Exception as e:
            logging.error("Error in `find` MDBClient: {}".format(e))
            return False
