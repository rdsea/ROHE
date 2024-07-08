from abc import ABC, abstractmethod
from typing import Any

from ..common.data_models import MongoAuthentication, MongoCollection
from ..common.logger import logger
from ..common.mongo_utils import get_mdb_client


class DBClient(ABC):
    def __init__(self, db_config: MongoAuthentication) -> None:
        try:
            super().__init__()
            self.db_config = db_config
        except Exception as e:
            logger.exception(f"Error in __init__ DBClient: {e}")

    @abstractmethod
    def get(self, collection: MongoCollection, query: Any) -> dict:
        """Return data"""
        return {}

    def to_dict(self) -> dict:
        return self.db_config.dict()


class MDBClient(DBClient):
    def __init__(self, mdb_config: MongoAuthentication) -> None:
        try:
            super().__init__(mdb_config)

            self.mdb_client = get_mdb_client(self.db_config)
        except Exception as e:
            logger.exception(f"Error in __init__ MDBClient: {e}")

    def get(self, db_collection: MongoCollection, query: Any) -> dict:
        try:
            if self.mdb_client is not None:
                db = self.mdb_client[db_collection.database]
                collection = db[db_collection.collection]
                data = collection.aggregate(query)
            return data
        except Exception as e:
            logger.exception(f"Error in `get` MDBClient: {e}")
            return {}

    def insert_one(self, db_collection: MongoCollection, data: dict):
        try:
            if self.mdb_client is not None:
                db = self.mdb_client[db_collection.database]
                collection = db[db_collection.collection]
                response = collection.insert_one(data)
            return response
        except Exception as e:
            logger.exception(f"Error in `insert_one` MDBClient: {e}")
            return {}

    def insert_many(self, db_collection: MongoCollection, data: list):
        try:
            if self.mdb_client is not None:
                db = self.mdb_client[db_collection.database]
                collection = db[db_collection.collection]
                response = collection.insert_many(data)
            return response
        except Exception as e:
            logger.exception(f"Error in `insert_many` MDBClient: {e}")
            return {}

    def delete_many(self, db_collection: MongoCollection, data: dict):
        try:
            if self.mdb_client is not None:
                db = self.mdb_client[db_collection.database]
                collection = db[db_collection.collection]
                response = collection.delete_many(data)
            return response
        except Exception as e:
            logger.exception(f"Error in `delete_many` MDBClient: {e}")
            return {}

    def find(self, db_collection: MongoCollection, query: Any) -> dict:
        try:
            if self.mdb_client is not None:
                db = self.mdb_client[db_collection.database]
                collection = db[db_collection.collection]
                data = collection.find(query)
            return data
        except Exception as e:
            logger.exception(f"Error in `find` MDBClient: {e}")
            return {}

    def aggregate(
        self, db_collection: MongoCollection, find_query: Any, sort_query: Any
    ) -> dict:
        try:
            if self.mdb_client is not None:
                db = self.mdb_client[db_collection.database]
                collection = db[db_collection.collection]
                data = collection.find(find_query).sort(sort_query)
            return data
        except Exception as e:
            logger.exception(f"Error in `find` MDBClient: {e}")
            return {}

    def drop(self, db_collection: MongoCollection) -> dict:
        try:
            if self.mdb_client is not None:
                db = self.mdb_client[db_collection.database]
                collection = db[db_collection.collection]
                collection.drop()
            return True
        except Exception as e:
            logger.exception(f"Error in `find` MDBClient: {e}")
            return False
