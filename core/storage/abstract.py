import os
import sys
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

# User must export ROHE_PATH befor using
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
import logging

from lib.common.mongoUtils import get_mdb_client

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
    def __init__(self, dbConfig: DBConf) -> None:
        try:
            super().__init__()
            self.dbConfig = dbConfig
        except Exception as e:
            logging.error("Error in __init__ DBClient: {}".format(e))

    @abstractmethod
    def get(self, collection: DBCollection, query: Any) -> dict:
        """Return data"""
        return {}

    def to_dict(self) -> dict:
        return self.dbConfig.dict()


class MDBClient(DBClient):
    def __init__(self, mdbConfig: DBConf) -> None:
        try:
            super().__init__(mdbConfig)

            self.mdbClient = get_mdb_client(self.dbConfig)
        except Exception as e:
            logging.error("Error in __init__ MDBClient: {}".format(e))

    def get(self, dbCollection: DBCollection, query: Any) -> dict:
        try:
            if self.mdbClient != None:
                db = self.mdbClient[dbCollection.database]
                collection = db[dbCollection.collection]
                data = collection.aggregate(query)
            return data
        except Exception as e:
            logging.error("Error in `get` MDBClient: {}".format(e))
            return {}

    def insert_one(self, dbCollection: DBCollection, data: dict):
        try:
            if self.mdbClient != None:
                db = self.mdbClient[dbCollection.database]
                collection = db[dbCollection.collection]
                response = collection.insert_one(data)
            return response
        except Exception as e:
            logging.error("Error in `insert_one` MDBClient: {}".format(e))
            return {}

    def insert_many(self, dbCollection: DBCollection, data: list):
        try:
            if self.mdbClient != None:
                db = self.mdbClient[dbCollection.database]
                collection = db[dbCollection.collection]
                response = collection.insert_many(data)
            return response
        except Exception as e:
            logging.error("Error in `insert_many` MDBClient: {}".format(e))
            return {}

    def delete_many(self, dbCollection: DBCollection, data: list):
        try:
            if self.mdbClient != None:
                db = self.mdbClient[dbCollection.database]
                collection = db[dbCollection.collection]
                response = collection.delete_many(data)
            return response
        except Exception as e:
            logging.error("Error in `delete_many` MDBClient: {}".format(e))
            return {}

    def find(self, dbCollection: DBCollection, query: Any) -> dict:
        try:
            if self.mdbClient != None:
                db = self.mdbClient[dbCollection.database]
                collection = db[dbCollection.collection]
                data = collection.find(query)
            return data
        except Exception as e:
            logging.error("Error in `find` MDBClient: {}".format(e))
            return {}

    def aggregate(
        self, dbCollection: DBCollection, find_query: Any, sort_query: Any
    ) -> dict:
        try:
            if self.mdbClient != None:
                db = self.mdbClient[dbCollection.database]
                collection = db[dbCollection.collection]
                data = collection.find(find_query).sort(sort_query)
            return data
        except Exception as e:
            logging.error("Error in `find` MDBClient: {}".format(e))
            return {}

    def drop(self, dbCollection: DBCollection) -> dict:
        try:
            if self.mdbClient != None:
                db = self.mdbClient[dbCollection.database]
                collection = db[dbCollection.collection]
                collection.drop()
            return True
        except Exception as e:
            logging.error("Error in `find` MDBClient: {}".format(e))
            return False
