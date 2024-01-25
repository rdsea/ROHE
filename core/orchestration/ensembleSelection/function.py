import traceback
import argparse
import sys, os
# User must export ROHE_PATH befor using
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
from lib import roheUtils

import random
from math import log10, log, gcd, ceil
import copy

from core.orchestration.ensembleSelection.resource import ServiceDeployment, MLModel, PhysicalDevice

DEFAULT_MAX_ACC = 0.95
DEFAULT_MIN_ACC = 0.5
DEFAULT_MAX_RES = 3
DEFAULT_MIN_RES = 0.2
DEFAULT_MAX_COST = 8000
DEFAULT_MIN_COST = 1000
DEFAULT_WEIGHT_FACTOR = [1,1,1]

def estimatePerformance(deploymentDict, baseResTime):
    minThroughput = float('inf')
    maxResponseTime = float('-inf')
    for modelKey, deployData in deploymentDict.items():
        sThroughput = 0
        for repKey, replicaData in deployData.items():
            sThroughput += replicaData.throughput
            if maxResponseTime < replicaData.responseTime:
                maxResponseTime = replicaData.responseTime
        if minThroughput > sThroughput:
            minThroughput = sThroughput
         
    performanceScore = baseResTime/maxResponseTime
    return performanceScore, minThroughput, maxResponseTime

def estimateBaseCost(deploymentDict):
    baseCost = 0
    for modelKey, deployData in deploymentDict.items():
        sThroughput = 0
        for repKey, replicaData in deployData.items():
            baseCost += replicaData.baseCost
    return baseCost

def estimateRuntimeCost(deploymentDict, nRequest):
    baseCost = 0
    for modelKey, deployData in deploymentDict.items():
        sThroughput = 0
        for repKey, replicaData in deployData.items():
            baseCost += replicaData.baseCost
    return baseCost

def find_gcd(numbers):
    result = numbers[0]
    for num in numbers[1:]:
        result = gcd(result, num)
    return result

def createModelReplica(ensemble, throughputReq):
    modelCount = 0
    repModel = {}
    modelScale = {}
    minScale = float('inf')

    for model in ensemble:
        repModel[str(modelCount)] = {}
        nReplica = throughputReq/model.wThroughput
        modelScale[str(modelCount)] = nReplica
        if nReplica < minScale:
            minScale = nReplica
        modelCount += 1
    if minScale > 1:
        for key, value in modelScale.items():
            modelScale[key] = int(ceil(value/minScale))

    modelCount = 0
    for model in ensemble:
        nReplica = modelScale[str(modelCount)]
        for i in range(int(ceil(nReplica))):
            repModel[str(modelCount)][str(i)] = copy.deepcopy(model)
        modelCount += 1
    return repModel, minScale

def creatDeploymentDict(repModel, deployList, devices):
    deploymentDict = {}
    for deploy in deployList:
        modelKey = deploy["modelKey"]
        replicaKey = deploy["replicaKey"]
        deviceKey = deploy["deviceKey"]
        device = devices[deviceKey]
        model = repModel[modelKey][replicaKey]
        if modelKey not in deploymentDict:
            deploymentDict[modelKey] = {}
        deploymentDict[modelKey][replicaKey] = ServiceDeployment(model,device)
    return deploymentDict

def estimateAccuracy(dataDistribute, ensemble, dataWeight):
    # Estimate ML specific Metrics
    accuracy = 0
    maxAcc = 0
    for i in range(len(dataDistribute)):
        classID = str(i)
        missRate = 1
        for model in ensemble:
            missRate *= (1-model.accuracy[classID])
        iAccuracy = 1 - missRate
        accuracy += dataWeight[i]*iAccuracy
        if iAccuracy > maxAcc:
            maxAcc = iAccuracy
    return accuracy

def estimateConfidence(dataDistribute, ensemble, dataWeight):
    # Estimate ML specific Metrics
    confidence = 0
    mc = 0
    for i in range(len(dataDistribute)):
        classID = str(i)
        maxConfidence = 0
        for model in ensemble:
            if model.confidence[classID] > maxConfidence:
                maxConfidence = model.confidence[classID]
        confidence += dataWeight[i]*maxConfidence
        if mc < maxConfidence:
            mc = maxConfidence
    return confidence

def estimateMissRate(dataDistribute, ensemble, mObject, dataWeight):
    missRate = 0
    for key, value in mObject.items():
        eMissRate = 1
        if "target" in value:
            target = str(value["target"])
        if "miss" in value:
            miss = str(value["miss"])
        else:
            miss = None
        for model in ensemble:
            iMissRate = dataDistribute[int(target)]*(1-model.accuracy[target])
            if miss != None:
                iMissRate *= dataWeight[int(miss)]
            eMissRate *= iMissRate
        missRate += eMissRate
    return missRate

def randomModelAndDevice():
    models = []
    # Init 20 ML Model
    for i in range(20):
        models.append(MLModel(tier=random.randint(1,6)))

    devices = []
    # init 10 types of physical device
    for i in range(15):
        devices.append(PhysicalDevice(tier=random.randint(1,3)))

    modelDict = {}
    for model in models:
        modelDict.update(model.exportFeature())


    deviceDict = {}
    for device in devices:
        deviceDict.update(device.exportFeature())

    return models, devices 
    # roheUtils.to_yaml("./export/model20_features.yaml",modelDict)
    # roheUtils.to_yaml("./export/device15_features.yaml",deviceDict)

def loadModel(file_path):
    modelDict = roheUtils.load_config(file_path)
    models = []
    for key, value in modelDict.items():
        newModel = MLModel()
        newModel.importFeature(value,key)
        models.append(newModel)
    return models

def loadDevice(file_path):
    deviceDict = roheUtils.load_config(file_path)
    devices = []
    for key, value in deviceDict.items():
        newDevice = PhysicalDevice()
        newDevice.importFeature(value,key)
        devices.append(newDevice)
    return devices

def map_to_log_scale(value, min_value, max_value, logbase):
    # Calculate the logarithmic scale
    log_min = log(min_value,logbase)
    log_max = log(max_value,logbase)

    # Map the value to the logarithmic scale
    log_value = log(value,logbase)

    # Map the logarithmic value to the range [0, 1]
    mapped_value = (log_value - log_min) / (log_max - log_min)

    return mapped_value

def ScoreEstimation(avgAcc, res, cost):
    score = DEFAULT_WEIGHT_FACTOR[0]*map_to_log_scale(avgAcc, DEFAULT_MIN_ACC, DEFAULT_MAX_ACC, 2)+ \
            DEFAULT_WEIGHT_FACTOR[1]*(1-map_to_log_scale(res, DEFAULT_MIN_RES, DEFAULT_MAX_RES, 2)) + \
            DEFAULT_WEIGHT_FACTOR[2]*(1-map_to_log_scale(cost, DEFAULT_MIN_COST, DEFAULT_MAX_COST, 2))
    return score