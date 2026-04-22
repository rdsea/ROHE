from typing import Any
from urllib.parse import quote_plus

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from ..common.data_models import MongoAuthentication, MongoCollection
from ..common.logger import logger


class MDBClient:
    def __init__(self, mdb_config: MongoAuthentication) -> None:
        self.db_config = mdb_config
        # Fail-fast: let connection errors propagate so callers can decide
        # how to handle them; do not swallow and leave mdb_client unset.
        self.mdb_client = self.get_mdb_client(self.db_config)

    def get_mdb_client(self, mdb_conf):
        username = quote_plus(mdb_conf.username)
        password = quote_plus(mdb_conf.password)
        # Build the URI inline and do not bind it to a named local; this keeps
        # the plaintext credentials out of traceback frames that include locals.
        client = MongoClient(
            f"{mdb_conf.prefix}{username}:{password}@{mdb_conf.url}",
            server_api=ServerApi("1"),
        )
        client.admin.command("ping")
        logger.info("Pinged your deployment. You successfully connected to MongoDB!")
        return client

    def get(self, db_collection: MongoCollection, query: Any):
        try:
            db = self.mdb_client[db_collection.database]
            collection = db[db_collection.collection]
            data = list(collection.aggregate(query))
            return data
        except Exception as e:
            logger.error(f"MDBClient error in `get` ({type(e).__name__})")
            return []

    def insert_one(self, db_collection: MongoCollection, data: dict):
        try:
            db = self.mdb_client[db_collection.database]
            collection = db[db_collection.collection]
            response = collection.insert_one(data)
            return response
        except Exception as e:
            logger.error(f"MDBClient error in `insert_one` ({type(e).__name__})")
            return {}

    def insert_many(self, db_collection: MongoCollection, data: list):
        try:
            db = self.mdb_client[db_collection.database]
            collection = db[db_collection.collection]
            response = collection.insert_many(data)
            return response
        except Exception as e:
            logger.error(f"MDBClient error in `insert_many` ({type(e).__name__})")
            return {}

    def delete_many(self, db_collection: MongoCollection, data: dict):
        try:
            db = self.mdb_client[db_collection.database]
            collection = db[db_collection.collection]
            response = collection.delete_many(data)
            return response
        except Exception as e:
            logger.error(f"MDBClient error in `delete_many` ({type(e).__name__})")
            return {}

    def find(self, db_collection: MongoCollection, query: Any):
        try:
            db = self.mdb_client[db_collection.database]
            collection = db[db_collection.collection]
            data = collection.find(query)
            return data
        except Exception as e:
            logger.error(f"MDBClient error in `find` ({type(e).__name__})")
            return {}

    def aggregate(
        self, db_collection: MongoCollection, find_query: Any, sort_query: Any
    ):
        try:
            db = self.mdb_client[db_collection.database]
            collection = db[db_collection.collection]
            data = collection.find(find_query).sort(sort_query)
            return data
        except Exception as e:
            logger.error(f"MDBClient error in `aggregate` ({type(e).__name__})")
            return {}

    def drop(self, db_collection: MongoCollection):
        try:
            db = self.mdb_client[db_collection.database]
            collection = db[db_collection.collection]
            collection.drop()
            return True
        except Exception as e:
            logger.error(f"MDBClient error in `drop` ({type(e).__name__})")
            return False

    def to_dict(self):
        return self.db_config.model_dump()
