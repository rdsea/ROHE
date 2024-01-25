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


#### TEST ####
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Analyzing")
    parser.add_argument('--exID', type=int, help='experiment id', default=1)

    
    

    # Parse the parameters
    args = parser.parse_args()
    # runID = int(args.exID)

    sumary = {}
    x1 = []
    y1 = []
    for i in range(1,5):
        runID = i
        folderName = "./run"+str(runID)
        if os.path.exists(folderName):
            readFlag = True
        else:
            readFlag = False

        if readFlag:
            runSumary = roheUtils.load_config(folderName+"/sumary.yaml")
            mlSumary = pd.read_csv(folderName+"/sumary.csv")
            
            y1.append(runSumary["nIteration"])
            x1.append(runSumary["nModel"])
            sumary["run"+str(i)] = {"nModel": runSumary["nModel"], "nIteration": runSumary["nIteration"], "mlSumary": mlSumary}

    # fig1, ax1 = plt.subplots()
    # ax1.plot(x1, y1)
    # ax1.set_xlabel('Number of Selected Model')
    # ax1.set_ylabel('Number of Iteration')
    # ax1.set_title('N model vs Iteration')
    # plt.savefig("./plot/nModel_iteration.png")

    # fig2, ax2 = plt.subplots()
    # for folderName, data in sumary.items():
    #     folderPath = "./"+folderName+"/"
    #     mlSumary = data["mlSumary"]
    #     for index, row in mlSumary.iterrows():
    #         fileName = folderPath+row["ensemble"]+".csv"
    #         dfi = pd.read_csv(fileName)
    #         yi = []
    #         xi = []
    #         for idi, irow in dfi.iterrows():
    #             xi.append(data["nModel"])
    #             yi.append(irow["baseCost"])
    #         ax2.scatter(xi, yi, label=str(data["nModel"])+row["ensemble"], s=1)
    #     print(folderName)
            
    # ax2.set_xlabel('maxRes')
    # ax2.set_ylabel('baseCost')   
    # ax2.set_title('Dot Chart')
    # # legend2 = ax2.legend()
    # # legend2.set_bbox_to_anchor((1.05, 1))
    # print("start plotting")
    # plt.savefig("./plot/maxRes_baseCost.png")
    # plt.show()
            
    fig2, ax2 = plt.subplots()
    for folderName, data in sumary.items():
        folderPath = "./"+folderName+"/"
        mlSumary = data["mlSumary"]
        yi = []
        xi = []
        for index, row in mlSumary.iterrows():
            fileName = folderPath+row["ensemble"]+".csv"
            dfi = pd.read_csv(fileName)
            for idi, irow in dfi.iterrows():
                xi.append(data["nModel"])
                yi.append(irow["baseCost"])
        ax2.scatter(xi, yi, label=str(data["nModel"])+row["ensemble"], s=1)
        print(folderName)
            
    ax2.set_xlabel('nModel')
    ax2.set_ylabel('baseCost')   
    ax2.set_title('Dot Chart')
    # legend2 = ax2.legend()
    # legend2.set_bbox_to_anchor((1.05, 1))
    print("start plotting")
    plt.savefig("./plot/nModel_baseCost.png")
    plt.show()