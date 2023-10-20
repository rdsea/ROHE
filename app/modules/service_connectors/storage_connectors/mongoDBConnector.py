import logging
import pandas as pd
from pymongo import MongoClient
from typing import Optional, Any

logging.getLogger(__name__)


class MongoDBInfo:
    def __init__(self, username: str, password: str, host: str, port: int, database_name: str, collection_name: str):
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.database_name = database_name
        self.collection_name = collection_name
        
class MongoDBConnector():
    def __init__(self, db_info: MongoDBInfo):
        self._client = None
        self._db = None
        self._collection = None
        self._setup_connection(db_info)

    def _setup_connection(self, db_info: MongoDBInfo):
        try:
            # Construct the connection string using the provided details
            connection_string = f"mongodb://{db_info.username}:{db_info.password}@{db_info.host}:{db_info.port}"

            self._client = MongoClient(connection_string)
            # Test if the connection is established.
            self._client.list_database_names()

            # Implicitly create the database and collection if they do not exist.
            self._db = self._client[db_info.database_name]
            self._collection = self._db[db_info.collection_name]
            logging.info(f'Connected to MongoDB server, Database: {db_info.database_name}, Collection: {db_info.collection_name}')
            print(f'Connected to MongoDB server, Database: {db_info.database_name}, Collection: {db_info.collection_name}')

        except Exception as e:
            logging.error("Invalid MongoDB Connection Information.")
            print("Invalid MongoDB Connection Information.")

            raise e
    
    # def upload(self, data: Any):
    #     try:
    #         if isinstance(data, pd.DataFrame):
    #             data = data.to_dict(orient='records')
                
    #         elif not isinstance(data, list):
    #             raise TypeError("Unsupported data type for upload. Supported types are: pandas DataFrame or List of Dictionaries.")
            
    #         self._collection.insert_many(data)
    #     except Exception as e:
    #         logging.error(e)
    #         raise e
    
    def upload(self, data: any):
        try:
            if isinstance(data, pd.DataFrame):
                data = data.to_dict(orient='records')
                
            elif isinstance(data, dict):
                data = [data]  # Convert the dictionary to a list of one dictionary
                
            elif not isinstance(data, list):
                raise TypeError("Unsupported data type for upload. Supported types are: pandas DataFrame, List of Dictionaries, or Dictionary.")
            
            self._collection.insert_many(data)
        except Exception as e:
            logging.error(e)
            raise e

    def download(self, query: Optional[dict] = None) -> pd.DataFrame:
        try:
            query = query or {}  # If no query is provided, fetch all documents
            data = list(self._collection.find(query))
            dataframe = pd.DataFrame(data)
            logging.info(f'Successfully downloaded data from {self._collection.name}')
            return dataframe
        except Exception as e:
            logging.error(e)
            raise e
    
    def close_connection(self):
        if self._client:
            self._client.close()
            logging.info('Closed connection to MongoDB server')