import os, sys
import qoa4ml.qoaUtils as qoa_utils

from threading import Lock

# set the ROHE to be in the system path
lib_level = os.environ.get('LIB_LEVEL')
if not lib_level:
    lib_level = 5
main_path = config_file = qoa_utils.get_parent_dir(__file__,lib_level)
sys.path.append(main_path)

print(f"This is the main path: {main_path}")


# # set the ROHE to be in the system path
# def get_parent_dir(file_path, levels_up=1):
#     file_path = os.path.abspath(file_path)  # Get the absolute path of the running file
#     parent_path = file_path
#     for _ in range(levels_up):
#         parent_path = os.path.dirname(parent_path)
#     return parent_path

# up_level = 6
# root_path = get_parent_dir(__file__, up_level)
# sys.path.append(root_path)
# print(f"This is the main path: {root_path}")

from app.modules.image_processing.aggregatingObject import KafkaStreamAggregatingListener
from app.modules.service_connectors.storage_connectors.mongoDBConnector import MongoDBConnector, MongoDBInfo

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