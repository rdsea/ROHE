import sys, os
# User must export ROHE_PATH befor using
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)

from core.metricStorage.abstract import MDBConf

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

def get_mdb_client(mdb_conf: MDBConf):
    m_uri = mdb_conf.prefix+mdb_conf.username+":"+mdb_conf.password+mdb_conf.url
    client = MongoClient(m_uri, server_api=ServerApi('1'))
    try:
        client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
        return client
    except Exception as e:
        print(e)
        return None