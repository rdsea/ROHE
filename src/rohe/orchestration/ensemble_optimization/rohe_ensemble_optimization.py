import copy
import time

from ...common.performance import MLServicePerformance
from ...lib.common.mongo_utils import get_mdb_client
from ...storage.custom import (
    execute_metric_queries,
    get_service_cost,
    get_service_performance,
)
from .abstract import EnsembleOptimization


class RoheEnsembleOptimization(EnsembleOptimization):
    def __init__(
        self, db_config, of_name: str, model_list: list, infrastructure_list: list
    ):
        # init basic attribute in parent class:
        # self.model_list = model_list
        # self.infrastructure_list = infrastructure_list
        # Othesr:
        # - methods: update_model_list, update_infrastructure_list, set_optimization_algorithm
        super().__init__(of_name, model_list, infrastructure_list)

        # init mongoClient to query data from Database
        self.mongo_client = get_mdb_client(db_config)

    def get_ml_service_performance(
        self,
        database,
        model_collection: str,
        infrastructure_collection: str,
        model_cost_collection: str,
        infrastructure_cost_collection: str,
        metric_config: dict,
        timestamp=None,
        limit=10000,
    ) -> list:
        # from config, query and calculate runtime metrics based on user description
        # specify database name
        self.db = self.mongo_client[database]
        # specify collection for model performance
        self.model_collection = self.db[model_collection]
        # specify infrastructure collection
        self.infrastructure_collection = self.db[infrastructure_collection]

        # specify collection for model cost
        self.model_cost_collection = self.db[model_cost_collection]
        # specify infrastructure cost collection
        self.infrastructure_cost_collection = self.db[infrastructure_cost_collection]

        if timestamp is None:
            timestamp = int(time.time())

        # list of unused attributes from query
        rem_list = ["_id", "model_id", "infrastructure", "timestamp"]

        # init list of performance list
        ml_performance_list = []

        # iterate list of ML model
        for model_name in self.model_list:
            metrics = {}
            last_update = {"ml_metric": timestamp}

            # query and calculate individual metrics
            for key, metric in metric_config.items():
                metrics[key] = execute_metric_queries(
                    self.model_collection,
                    metric,
                    model_name,
                    limit=limit,
                    timestamp=timestamp,
                )

            # iterate list of infrastructure to query common metrics e.g., throughput and response time
            for infrastructure in self.infrastructure_list:
                service_performance = get_service_performance(
                    self.infrastructure_collection, model_name, infrastructure
                )
                last_update["infrastructure"] = copy.deepcopy(
                    service_performance["timestamp"]
                )

                # remove unused attributes
                for rm_key in rem_list:
                    service_performance.pop(rm_key)

                # aggregate metric into a single dictionary
                f_metrics = copy.deepcopy(metrics)
                f_metrics.update(service_performance)

                f_metrics["cost"] = get_service_cost(
                    self.model_cost_collection,
                    self.infrastructure_cost_collection,
                    model_name,
                    infrastructure,
                )

                # init an MLServicePerformance represent performance of a ML model deployed on a specific infrastructure
                ml_service_performance = MLServicePerformance(
                    model=model_name,
                    infrastructure=infrastructure,
                    metrics=f_metrics,
                    last_update=last_update,
                )

                # append to list of performance
                ml_performance_list.append(ml_service_performance)

        return ml_performance_list

    def select(self, ml_service_list: list, contract: dict) -> list:
        # must be call after "set_optimization_algorithm"
        ensemble = self.optimization_algorithm(
            self.model_list,
            self.infrastructure_list,
            ml_service_list,
            self.objective_funtion,
            contract,
        )
        return ensemble
