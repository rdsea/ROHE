import traceback
import argparse
import sys, os
# User must export ROHE_PATH befor using
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
from lib import roheUtils
import time
import pandas as pd

import random, uuid
from math import log10, log
import itertools
import copy


import matplotlib.pyplot as plt

def estimateCost(row):
    if "minScale" in row.to_dict():
        if row["minScale"] > 1:
            return row["minScale"]*row["baseCost"]
    return row["baseCost"]


#### TEST ####
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Analyzing")
    parser.add_argument('--exID', type=int, help='experiment id', default=16)
    parser.add_argument('--acc', type=float, help='accuracy requirement', default=0.6)

    
    

    # Parse the parameters
    args = parser.parse_args()
    runID = int(args.exID)
    accuracyRequirement = float(args.acc)

    folderName = "./run"+str(runID)
    if os.path.exists(folderName):
        readFlag = True
    else:
        readFlag = False

    if readFlag:
        runSumary = roheUtils.load_config(folderName+"/sumary.yaml")
        mlSumary = pd.read_csv(folderName+"/sumary.csv")

        filteredEmsemble = mlSumary[mlSumary["AvgAccuracy"]>accuracyRequirement]

        minCost = float('inf')
        maxScore = float('-inf')
        costScoreMax = 0
        for index, row in filteredEmsemble.iterrows():
            filePath = folderName+"/{}.csv".format(row["ensemble"])
            ensembleDF = pd.read_csv(filePath)
            ensembleDF["Cost"] = ensembleDF.apply(estimateCost, axis=1)
            dfMinCost = ensembleDF["Cost"].min()
            idScoreMax = ensembleDF["score"].idxmax()
            dfMaxScore = ensembleDF["score"][idScoreMax]
            

            if minCost > dfMinCost:
                minCost = dfMinCost
            if maxScore < dfMaxScore:
                maxScore = dfMaxScore
                costScoreMax = ensembleDF["Cost"][idScoreMax]
    
    print("Min Cost: ",minCost)
    print("Max Score: ", maxScore, " Cost: ", costScoreMax)
    print("nModel: ",runSumary["nModel"])
    print("scaleReduction: ",runSumary["scaleReduction"])
    print("Throughput: ",runSumary["throughputReq"])

        
       
            
  