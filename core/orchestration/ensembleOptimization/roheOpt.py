import sys, os, copy, time
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
from lib.common.mongoUtils import get_mdb_client
from core.orchestration.ensembleOptimization.abstract import EnsembleOptimization
from core.metricStorage.custom import execute_metric_queries, get_service_performance, get_service_cost
from core.abstract import MLServicePerformance


class RoheEnsembleOptimization(EnsembleOptimization):
    def __init__(self, dbConfig, of_name: str, model_list: list, infrastructure_list: list):
        # init basic attribute in parent class:
        # self.model_list = model_list 
        # self.infrastructure_list = infrastructure_list
        # Othesr:
        # - methods: update_model_list, update_infrastructure_list, set_optimization_algorithm
        super().__init__(of_name, model_list, infrastructure_list)

        # init mongoClient to query data from Database
        self.mongoClient = get_mdb_client(dbConfig)

    def get_ml_service_performance(self, database , model_collection: str, infrastructure_collection: str, model_cost_collection: str, infrastructure_cost_collection: str, metricConf: dict, timestamp = None) -> dict:
        # from config, query and calculate runtime metrics based on user description
        # specify database name
        self.db = self.mongoClient[database]
        # specify collection for model performance
        self.model_collection = self.db[model_collection]
        # specify infrastructure collection 
        self.infrastructure_collection = self.db[infrastructure_collection]

        # specify collection for model cost
        self.model_cost_collection = self.db[model_cost_collection]
        # specify infrastructure cost collection 
        self.infrastructure_cost_collection = self.db[infrastructure_cost_collection]


        if timestamp == None:
            timestamp = int(time.time())
        
        # list of unused attributes from query
        rem_list = ['_id', 'model_id', 'infrastructure', 'timestamp']

        # init list of performance list
        ml_performance_list = []

        # iterate list of ML model
        for model_name in self.model_list:
            metrics = {}
            last_update = {"ml_metric": timestamp}

            # query and caculate individual metrics
            for key, metric in metricConf.items():
                metrics[key] = execute_metric_queries(self.model_collection, metric, model_name, timestamp=timestamp)
            
            # iterate list of infrastructure to query common metrics e.g., throughput and response time
            for infrastructure in self.infrastructure_list:
                service_performance = get_service_performance(self.infrastructure_collection, model_name, infrastructure)
                last_update["infrastructure"] = copy.deepcopy(service_performance["timestamp"])
                
                # remove unused attributes
                for rm_key in rem_list:
                    service_performance.pop(rm_key)
                
                # aggregate metric into a single dictionary 
                f_metrics = copy.deepcopy(metrics)
                f_metrics.update(service_performance)

                f_metrics["cost"] = get_service_cost(self.model_cost_collection, self.infrastructure_cost_collection, model_name, infrastructure)

                # init an MLServicePerformance represent performance of a ML model deployed on a specific infrastructure
                ml_service_performance = MLServicePerformance(model=model_name, infrastructure=infrastructure, metrics=f_metrics, last_update=last_update)

                # append to list of performance
                ml_performance_list.append(ml_service_performance)

        return ml_performance_list

    def select(self, mlServiceList: list, contract: dict) -> list:
        # must be call after "set_optimization_algorithm"
        ensemble = self.optimization_algorithm(mlServiceList, self.objective_funtion, contract)
        return ensemble
    
    # def test(self, database, collection, model_name, infrastructure):
    #     self.db = self.mongoClient[database]
    #     self.infrastructure_collection = self.db[collection]
    #     result = get_service_performance(self.infrastructure_collection, model_name, infrastructure)
    #     print(result)