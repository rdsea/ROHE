import sys, os
# User must export ROHE_PATH befor using
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
from lib import roheUtils as rUtils
from core.orchestration.ensembleOptimization import objective
import random

def scale_reduction(ml_performance_list: list, objective_func_name: str, contract: dict):
    ensemble = random.sample(ml_performance_list, 3)
    objective_function = rUtils.get_function_from_module(objective, objective_func_name)
    result = objective_function(ensemble,contract)
    print(result)
    return result