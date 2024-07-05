from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from .logger import logger


def get_mdb_client(mdb_conf):
    try:
        m_uri = (
            mdb_conf.prefix + mdb_conf.username + ":" + mdb_conf.password + mdb_conf.url
        )
        client: MongoClient = MongoClient(m_uri, server_api=ServerApi("1"))
        client.admin.command("ping")
        logger.info("Pinged your deployment. You successfully connected to MongoDB!")
        return client
    except Exception as e:
        logger.exception(f"Error in get_mdb_client: {e}")
        return None
