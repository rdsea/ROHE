from __future__ import annotations

import argparse
import json
import os
from threading import Event, Lock, Thread, Timer
from typing import Any

import pymongo
from qoa4ml.collector.amqp_collector import AmqpCollector

from ..common import rohe_utils
from ..common.logger import logger
from ..common.window import EventBuffer, TimeBuffer
from ..models.common import AgentStatus
from ..variable import ROHE_PATH

DEFAULT_CONFIG_PATH = "configurations/observationConfigLocal.yaml"
DEFAULT_DATA_PATH = "/agent/data/"
DEFAULT_MODULE_PATH = "/agent/userModule/"

# Window types
_EVENT_WINDOW = 1
_TIME_WINDOW = 2

# Trigger types
_TIME_TRIGGER = 1
_EVENT_TRIGGER = 2


def get_app(collection: Any, application_name: str) -> dict[str, Any] | None:
    """Get application data from database."""
    pipeline = [
        {"$sort": {"timestamp": 1}},
        {
            "$group": {
                "_id": "$appID",
                "application_name": {"$last": "$application_name"},
                "user_id": {"$last": "$user_id"},
                "run_id": {"$last": "$run_id"},
                "timestamp": {"$last": "$timestamp"},
                "db": {"$last": "$db"},
                "client_count": {"$last": "$client_count"},
                "agent_config": {"$last": "$agent_config"},
            }
        },
    ]
    app_list = list(collection.aggregate(pipeline))
    for app in app_list:
        if app["application_name"] == application_name:
            return app
    return None


class ObservationAgent:
    """Streaming observation agent that collects metrics via AMQP,
    buffers them in configurable windows, and processes with user-defined functions."""

    def __init__(self, configuration: dict[str, Any], mg_db: bool = False) -> None:
        self.conf = configuration
        self.application_name: str = configuration["application_name"]
        self.temp_path = DEFAULT_DATA_PATH + self.application_name

        # Init metric collector
        collector_conf = self.conf["collector"]
        self.collector = AmqpCollector(
            collector_conf["amqp_collector"]["conf"], host_object=self
        )

        # Init database connection
        db_conf = self.conf["database"]
        self.mongo_client = pymongo.MongoClient(db_conf["url"])
        self.db = self.mongo_client[db_conf["db_name"]]
        self.metric_collection = self.db[db_conf["metric_collection"]]

        self.status = AgentStatus.READY

        # Init processing configuration
        self.agent_config = self.conf["stream_config"]
        self.buff_config = self.agent_config["window"]
        self.proc_config = self.agent_config["processing"]
        self.module_path = DEFAULT_MODULE_PATH + f"{self.proc_config['module']}.py"
        self.proc_module = rohe_utils.load_module(
            self.module_path, self.proc_config["module"]
        )

        # Init buffer based on window type
        if self.buff_config["size"]["type"] == _TIME_WINDOW:
            self.buffer = TimeBuffer(self.buff_config["size"]["value"])
        elif self.buff_config["size"]["type"] == _EVENT_WINDOW:
            self.buffer = EventBuffer(self.buff_config["size"]["value"])

        self.trigger = self.buff_config["interval"]
        self.insert_db = mg_db

        # Thread safety
        self._processing_lock = Lock()
        self._stop_event = Event()
        self._timer: Timer | None = None

    def reset_db(self) -> None:
        """Drop all metric collections."""
        self.metric_collection.drop()

    def start_consuming(self) -> None:
        """Start consuming metric reports from broker."""
        logger.info("Start consuming messages")
        self.collector.start_collecting()

    def start(self) -> None:
        """Start the observation agent."""
        self.status = AgentStatus.RUNNING
        self._stop_event.clear()

        sub_thread = Thread(target=self.start_consuming, daemon=True)
        sub_thread.start()
        logger.info(f"Agent '{self.application_name}' started consuming messages")

        if self.trigger["type"] == _TIME_TRIGGER:
            self._schedule_time_trigger()
        elif self.trigger["type"] == _EVENT_TRIGGER:
            self.trigger["count"] = 0

    def message_processing(self, ch: Any, method: Any, props: Any, body: bytes) -> None:
        """Callback for incoming AMQP messages."""
        mess = json.loads(str(body.decode("utf-8")))

        parser_name = self.proc_config["parser"]["name"]
        if parser_name == "dummy":
            logger.info(mess)
            return

        parser = getattr(self.proc_module, self.proc_config["parser"]["name"])
        df_mess = parser(mess, self.proc_config["parser"])
        file_path = self.temp_path + "/raw_message.csv"
        rohe_utils.df_to_csv(file_path, df_mess)

        self.buffer.append(df_mess)
        logger.debug(f"Buffer size: {len(self.buffer.get())}")

        if self.insert_db:
            insert_id = self.metric_collection.insert_one(mess)
            logger.debug(f"Inserted to database: {insert_id}")

        if self.trigger["type"] == _EVENT_TRIGGER:
            self._event_trigger()

    def window_processing(self) -> None:
        """Process accumulated buffer data with user-defined function."""
        if not self._processing_lock.acquire(blocking=False):
            logger.warning("Window processing already in progress, skipping")
            return

        try:
            logger.info("Start window processing")
            data = self.buffer.get(dataframe=True)

            function_name = self.proc_config["function"]
            if function_name == "dummy":
                return

            proc_func = getattr(self.proc_module, self.proc_config["function"])
            feature_list = self.proc_config["parser"]["feature"]

            for feature in feature_list:
                result_df, _model = proc_func(data, feature)
                if result_df is None:
                    continue

                rohe_utils.make_folder(self.temp_path)
                file_path = self.temp_path + "/" + str(feature) + ".csv"
                rohe_utils.df_to_csv(file_path, result_df)

                errors = result_df.loc[result_df["anomaly"] == -1]
                if len(errors) > 0:
                    logger.warning(f"Anomalies detected in feature '{feature}': {len(errors)} rows")
                    err_file_path = self.temp_path + "/error_" + str(feature) + ".csv"
                    rohe_utils.df_to_csv(err_file_path, errors)
        finally:
            self._processing_lock.release()

    def _event_trigger(self) -> None:
        """Event-based trigger: fire after N messages."""
        self.trigger["count"] += 1
        if self.trigger["count"] >= self.trigger["value"]:
            if self.status == AgentStatus.RUNNING:
                self.window_processing()
            self.trigger["count"] = 0

    def _schedule_time_trigger(self) -> None:
        """Schedule the next time-based trigger."""
        if self._stop_event.is_set():
            return
        self._timer = Timer(self.trigger["value"], self._time_trigger)
        self._timer.daemon = True
        self._timer.start()

    def _time_trigger(self) -> None:
        """Time-based trigger: fire periodically."""
        try:
            if self.status == AgentStatus.RUNNING:
                self.window_processing()
            self._schedule_time_trigger()
        except Exception as e:
            logger.exception(f"Error in time trigger: {e}")

    def stop(self) -> None:
        """Stop the observation agent."""
        self._stop_event.set()
        self.insert_db = False
        self.status = AgentStatus.STOPPED
        if self._timer is not None:
            self._timer.cancel()
        logger.info(f"Agent '{self.application_name}' stopped")

    def restart(self) -> None:
        """Restart database insertion."""
        self.insert_db = True
        self.status = AgentStatus.RUNNING
        self._stop_event.clear()
        logger.info(f"Agent '{self.application_name}' restarted")


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="ROHE Observation Agent")
    arg_parser.add_argument("--conf", help="configuration file", default=None)
    args = arg_parser.parse_args()

    config_file = args.conf
    if not config_file:
        config_file = ROHE_PATH + DEFAULT_CONFIG_PATH
        logger.info(f"Using default config: {config_file}")

    try:
        config = rohe_utils.load_config(config_file)
        if config is None:
            raise RuntimeError(f"Failed to load config from {config_file}")

        db_config = config["database"]
        mongo_client = pymongo.MongoClient(db_config["url"])
        db = mongo_client[db_config["db_name"]]
        collection = db[db_config["collection"]]

        application_name = os.environ.get("APP_NAME", "test")
        agent_config = get_app(collection, application_name)["agent_config"]
        agent_config["application_name"] = application_name
        logger.info(f"Starting agent for application: {application_name}")
        agent = ObservationAgent(agent_config)
        agent.start()
    except Exception:
        logger.exception("Exception in observation agent")
