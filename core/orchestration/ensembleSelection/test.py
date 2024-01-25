import traceback
import argparse
import sys, os
# User must export ROHE_PATH befor using
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
print(ROHE_PATH)
from lib import roheUtils
import time
import pandas as pd

import random, uuid
from math import log10, log
import itertools
import copy

from core.orchestration.ensembleSelection.function import *
from core.orchestration.ensembleSelection.resource import *


DEFAULT_THROUGHPUT_REQ = 60
DEFAULT_RESPONSETIME_REQ = 2
DEFAULT_BASE_RESPONSETIME = 100
DEFAULT_DATA_DISTRIBUTE = [1/13,1/13,1/13,1/13,1/13,1/13,1/13,1/13,1/13,1/13,1/13,1/13,1/13]
DEFAULT_DATA_WEIGHT = [1/13,1/13,1/13,1/13,1/13,1/13,1/13,1/13,1/13,1/13,1/13,1/13,1/13]
DEFAULT_MAX_ACC = 0.95
DEFAULT_MIN_ACC = 0.5
DEFAULT_MAX_RES = 3
DEFAULT_MIN_RES = 0.2
DEFAULT_MAX_COST = 8000
DEFAULT_MIN_COST = 1000
DEFAULT_WEIGHT_FACTOR = [1,1,1]
DEFAULT_MISS = {
    "ped": {
        "target": "6",
    },
    "car_rider":{
        "target": "2",
        "miss": "7"
    }
}

#### TEST ####
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Testing Algorithm")
    parser.add_argument('--device', type= str, help='default file to load device', default="./export/device3_features.yaml")
    parser.add_argument('--model', type= str, help='default file to load model', default="./export/model8_features.yaml")
    parser.add_argument('--nModel', type= int, help='number of selected model', default=2)
    parser.add_argument('--p', type= int, help='Default throughput requirement', default=1)
    parser.add_argument('--exID', type=int, help='experiment id', default=1)
    parser.add_argument('--sR', type=int, help='Scale recution', default=1)

    
    

    # Parse the parameters
    args = parser.parse_args()
    device_path = str(args.device)
    model_path = str(args.model)
    runID = int(args.exID)
    scaleReduction = int(args.sR)
    
    createFolder = True
    while createFolder:
        folderName = "./run"+str(runID)
        if os.path.exists(folderName):
            runID += 1
        else:
            os.makedirs(folderName)
            createFolder = False
    


    ######### Start #########
    # Load profile of models and devices 
    devices = loadDevice(device_path)
    models = loadModel(model_path)
    nModel = int(args.nModel)
    throughputReq = int(args.p)

    experimentMetaData = {"scaleReduction": scaleReduction, "modelFile":model_path, "deviceFile": device_path, "ensemble": {}, "nModel": nModel, "throughputReq": throughputReq, "runID": runID, "TotalModel": len(models), "TotalDevice": len(devices)}




    # Estimate scale 
    for i in range(len(models)):
        wThroughput = float('inf')
        bThroughput = float('-inf')
        for j in range(len(devices)):
            sDeployment = ServiceDeployment(models[i],devices[j])
            if sDeployment.throughput < wThroughput:
                wThroughput = sDeployment.throughput
            if sDeployment.throughput > bThroughput:
                bThroughput = sDeployment.throughput
        models[i].wThroughput = wThroughput # worst throughput
        models[i].bThroughput = bThroughput # best throughput

    print("Estimate throughput success")

    # Select k model to establish an ensemble

    iterateCount = 0
    ensembleCount = 0

    # Select nModel from the model collection
    ensembles = list(itertools.combinations(models, nModel))
    eMetadata = experimentMetaData["ensemble"]
    # iterate possible ensemble
    for ensemble in ensembles:
        # Define Ensemble MetaData
        eFile = folderName+"/ensemble"+str(ensembleCount)+".csv"
        
        deployList = []
        # create a dictionary include all service instance/replica need to be deployed
        repModel, minScale = createModelReplica(ensemble, throughputReq, scaleReduction)



        # init deployment for each replica deployment
        for modelKey, model in repModel.items():
            for replicaKey, replica in model.items():
                newKey = str(modelKey)+"x"+str(replicaKey)
                deployList.append({"modelKey":modelKey, "replicaKey": replicaKey, "deviceKey": 0})
        
        
        
        # # skip estimation
        # print("Total deployment: ", len(deployList))
        # print("Each ensemble iteration end after: ~", pow(len(devices),len(deployList)))
        # iterateCount += pow(len(devices),len(deployList))
        
        # init some value
        finish = True
        minThroughput = float("inf")
        maxPerformance = float("-inf")
        minBaseCost = float("inf")

        # Estimate ML specific Metrics
        avgAcc = estimateAccuracy(DEFAULT_DATA_DISTRIBUTE, ensemble, DEFAULT_DATA_WEIGHT)
        avgConf = estimateConfidence(DEFAULT_DATA_DISTRIBUTE, ensemble, DEFAULT_DATA_WEIGHT)
        missRate = estimateMissRate(DEFAULT_DATA_DISTRIBUTE, ensemble, DEFAULT_MISS, DEFAULT_DATA_WEIGHT)
        print("Avg Accuracy: ", avgAcc)
        print("Avg Confidence: ", avgConf)
        print("Miss Rate: ", missRate)
        print("Each ensemble iteration end after: ~", pow(len(devices),len(deployList)))

        print("Start iterating in 5s...")
        # time.sleep(5)
        print("Iteration Started")
        startTime = time.time()
        while finish:
            # reset pointer when update device for deployment
            pointer = 0
            iterateCount+=1
            
            # print("Doing something")
            deploymentDict = creatDeploymentDict(repModel, deployList, devices)
            # Estimate Performance
            performance, throughput, maxRes = estimatePerformance(deploymentDict, DEFAULT_BASE_RESPONSETIME)
            
            # Estimate base cost
            baseCost = estimateBaseCost(deploymentDict)
            score, accScore, resScore, costScore, missScore = ScoreEstimation(avgAcc=avgAcc, res=maxRes, cost=baseCost, missRate=missRate)
            dfi = pd.DataFrame({"performance":[performance],
                                "minScale":[minScale],
                                "throughput":[throughput],
                                "ensemble":["ensemble"+str(ensembleCount)],
                                "baseCost":[baseCost],
                                "accScore":[accScore],
                                "resScore":[resScore],
                                "costScore":[costScore],
                                "missScore":[missScore],
                                "score":[score],
                                "maxRes":[maxRes]})
            
            roheUtils.df_to_csv(eFile,dfi)

            if baseCost < minBaseCost:
                minBaseCost = baseCost

            if minThroughput > throughput:
                minThroughput = throughput
            if maxPerformance < performance:
                maxPerformance = performance

            deployList[pointer]["deviceKey"] += 1
            if (iterateCount % 10000) == 0:
                print("Iteration: ", iterateCount, "Ensemble Count: ", ensembleCount,"/",len(ensembles))
            while deployList[pointer]["deviceKey"] >= len(devices):
                deployList[pointer]["deviceKey"] = 0
                pointer += 1
                if pointer >= len(deployList):
                    finish = False
                    break
                deployList[pointer]["deviceKey"] += 1
            # break
        
        runTime = time.time()-startTime
        
        eMetadata.update({str(ensembleCount):{"File": str(eFile), "ensemble": str(ensemble), "runtime": str(runTime) }})
        dfe = pd.DataFrame({"AvgAccuracy":[avgAcc],
                            "minScale":[minScale],
                            "AvgConfidence":[avgConf],
                            "ensemble":["ensemble"+str(ensembleCount)],
                            "MissRate":[missRate],
                            "runtime":[runTime]})
        runFile = folderName+"/sumary.csv"
        roheUtils.df_to_csv(runFile,dfe)
        ensembleCount += 1
        # print(minBaseCost)
        # print(iterateCount, minThroughput, maxPerformance)
        # break
        experimentMetaData["nIteration"] = iterateCount
        roheUtils.to_yaml(folderName+"/sumary.yaml",experimentMetaData)
    print("Final iteration Count: ", iterateCount)
