import os, sys

from threading import Lock

from dotenv import load_dotenv
load_dotenv()

main_path = os.getenv('ROHE_PATH')
print(f"This is main path: {main_path}")
sys.path.append(main_path)



from app.modules.image_processing.aggregatingObject import KafkaStreamAggregatingListener
from app.modules.connectors.storage.mongoDBConnector import MongoDBConnector, MongoDBInfo

if __name__ == "__main__":

    kafka_address = '127.0.0.1:9092'
    # kafka_address = '128.214.254.126:9092'
    # kafka_address = 'http://128.214.254.126:9092'
    # kafka_address = '128.214.254.127:9092'


    # topic_name = 'quickstart-topic'
    topic_name = 'nii_case'
    lock = Lock()

    # topic_name = 'quickstart-topic'
    topic_name = 'nii_case'

    db_info = MongoDBInfo(
        username='admin_user',
        password='admin_pass',
        host='localhost',
        port=27017,
        database_name='nii_case',
        collection_name='inference_result_consumer'
    )

    db_connector = MongoDBConnector(db_info= db_info)


    listener = KafkaStreamAggregatingListener(kafka_address, topic_name, lock= lock, db_connector= db_connector)
    listener.run()