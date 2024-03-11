from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

def get_mdb_client(mdb_conf):
    m_uri = mdb_conf.prefix+mdb_conf.username+":"+mdb_conf.password+mdb_conf.url
    client = MongoClient(m_uri, server_api=ServerApi('1'))
    try:
        client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
        return client
    except Exception as e:
        print(e)
        return None