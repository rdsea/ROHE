import os
import sys

from dotenv import load_dotenv
from qoa4ml.QoaClient import QoaClient

load_dotenv()

ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)


import argparse
import signal

import app.object_classification.modules.utils as pipeline_utils
import lib.roheUtils as roheUtils
from app.object_classification.lib.connectors.storage.minioStorageConnector import (
    MinioConnector,
)
from app.object_classification.services.ingestion.ingestionService import (
    IngestionService,
)
from core.common.restService import RoheRestService
from core.serviceRegistry.consul import ConsulClient

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Argument for Ingestion Service")
    parser.add_argument("--port", type=int, help="default port", default=3000)
    parser.add_argument(
        "--conf",
        type=str,
        help="specify configuration file path",
        default="ingestion_config.yaml",
    )
    parser.add_argument("--run", type=str, help="specify run ID", default="profiling1")

    # Parse the parameters
    args = parser.parse_args()
    port = int(args.port)

    config_file = args.conf

    # yaml load configuration file
    config = roheUtils.load_config(file_path=config_file)
    if not config:
        print(
            "Something also wrong with rohe utils load config function. Third attempt to load config using rohe config load yaml config function"
        )
        config = roheUtils.load_yaml_config(file_path=config_file)

    # Minio Connector for uploading image
    minio_connector = MinioConnector(
        storage_info=config["external_services"]["minio_storage"]
    )
    config["minio_connector"] = minio_connector

    # consul for service register
    # register service
    local_ip = pipeline_utils.get_local_ip()
    consul_client = ConsulClient(
        config=config["external_services"]["service_registry"]["consul_config"]
    )
    service_id = consul_client.serviceRegister(
        name="ingestion", address=local_ip, tag=["nii_case"], port=port
    )

    # query for image info service url
    tags = config["external_services"]["service_registry"]["service"]["image_info"][
        "tags"
    ]
    query_type = config["external_services"]["service_registry"]["service"][
        "image_info"
    ]["type"]
    # for now, assume that we just need one image info service
    # service_info: dict = consul_client.getAllServiceInstances(name='image_info', tags=tags)[0]
    service_info: dict = pipeline_utils.handle_service_query(
        consul_client=consul_client,
        service_name="image_info",
        query_type=query_type,
        tags=tags,
    )[0]

    image_info_endpoint = "image_info_service"
    endpoint = (
        f"http://{service_info['Address']}:{service_info['Port']}/{image_info_endpoint}"
    )
    config["image_info_service"] = {}
    config["image_info_service"]["url"] = endpoint
    print(f"This is image info endpoint: {endpoint}")

    # qoa
    if config.get("qoa_config"):
        config["qoa_config"]["client"]["run_id"] = args.run
        print(f"\nAbout to load qoa client: {config['qoa_config']}")
        qoa_client = QoaClient(config["qoa_config"])
        qoa_client.process_monitor_start(5)
        config["qoaClient"] = qoa_client

    def signal_handler(sig, frame):
        print("You pressed Ctrl+C! Gracefully shutting down.")
        consul_client.serviceDeregister(id=service_id)
        sys.exit(0)

    # Register the signal handler for SIGINT
    signal.signal(signal.SIGINT, signal_handler)

    # start server
    rest_service = RoheRestService(config)
    rest_service.add_resource(IngestionService, "/ingestion_service")
    rest_service.run(port=port)
