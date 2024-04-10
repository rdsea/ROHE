import sys, os
# User must export ROHE_PATH befor using
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
import logging, traceback
logging.basicConfig(format='%(asctime)s:%(levelname)s -- %(message)s', level=logging.INFO)



from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

def get_mdb_client(mdb_conf):
    try:
        m_uri = mdb_conf.prefix+mdb_conf.username+":"+mdb_conf.password+mdb_conf.url
        client = MongoClient(m_uri, server_api=ServerApi('1'))
        client.admin.command('ping')
        logging.info("Pinged your deployment. You successfully connected to MongoDB!")
        return client
    except Exception as e:
        logging.error("Error in get_mdb_client: {}".format(e))
        return None