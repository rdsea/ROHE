import os
import sys

from pydantic import BaseModel

# User must export ROHE_PATH befor using
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
import logging

logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)


class MessagingConnectionConfig(BaseModel):
    name: str
    connectorType: str
    config: dict

    def to_qoa4ml_config(self):
        try:
            self_dict = {
                "name": self.name,
                "connector_class": self.connectorType,
                "config": self.config,
            }
            return self_dict
        except Exception as e:
            logging.error("Error in `to_dict` MessagingConnection: {}".format(e))
            return {}

    def to_dict(self):
        try:
            self_dict = {
                "name": self.name,
                "connectorType": self.connectorType,
                "config": self.config,
            }
            return self_dict
        except Exception as e:
            logging.error("Error in `to_dict` MessagingConnection: {}".format(e))
            return {}
