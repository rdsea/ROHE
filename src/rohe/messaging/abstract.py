import logging

from pydantic import BaseModel

logging.basicConfig(
    format="%(asctime)s:%(levelname)s -- %(message)s", level=logging.INFO
)


class MessagingConnectionConfig(BaseModel):
    name: str
    connector_type: str
    config: dict

    def to_qoa4ml_config(self):
        try:
            self_dict = {
                "name": self.name,
                "connector_class": self.connector_type,
                "config": self.config,
            }
            return self_dict
        except Exception as e:
            logging.error(f"Error in `to_dict` MessagingConnection: {e}")
            return {}

    def to_dict(self):
        try:
            self_dict = {
                "name": self.name,
                "connector_type": self.connector_type,
                "config": self.config,
            }
            return self_dict
        except Exception as e:
            logging.error(f"Error in `to_dict` MessagingConnection: {e}")
            return {}
