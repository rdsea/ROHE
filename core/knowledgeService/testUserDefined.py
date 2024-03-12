import sys, os, argparse
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
from core.knowledgeService.abstract import MDBConf
from core.knowledgeService.common import get_mdb_client
from lib import roheUtils as rUtil
from core.knowledgeService.custom import execute_metric_queries

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="User-defined metric test")
    parser.add_argument('--config', help='Client config file', default="/config/database/queryconf.yaml")
    parser.add_argument('--metric', help='Metric config file', default="/config/database/exMetric.yaml")

    args = parser.parse_args()

    dbConfFile = rUtil.load_config(ROHE_PATH+args.config)
    metricConfFile = rUtil.load_config(ROHE_PATH+args.metric)

    dbconf = MDBConf(url=dbConfFile["url"], prefix=dbConfFile["prefix"], username=dbConfFile["username"],password=dbConfFile["password"])

    dbclient = get_mdb_client(dbconf)
    db = dbclient[dbConfFile["database"]]
    collection = db[dbConfFile["collection"]]

    metric_result = execute_metric_queries(collection, metricConfFile, limit=10000, timestamp=1697430147)
    print(metric_result)
