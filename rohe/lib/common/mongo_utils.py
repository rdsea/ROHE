import logging

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)


def get_mdb_client(mdb_conf):
    try:
        m_uri = (
            mdb_conf.prefix + mdb_conf.username + ":" + mdb_conf.password + mdb_conf.url
        )
        client: MongoClient = MongoClient(m_uri, server_api=ServerApi("1"))
        client.admin.command("ping")
        logging.info("Pinged your deployment. You successfully connected to MongoDB!")
        return client
    except Exception as e:
        logging.error("Error in get_mdb_client: {}".format(e))
        return None
