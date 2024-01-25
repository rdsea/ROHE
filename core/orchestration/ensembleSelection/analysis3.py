import traceback
import argparse
import sys, os
# User must export ROHE_PATH befor using
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
from lib import roheUtils
import time, math
import pandas as pd

import random, uuid
from math import log10, log
import itertools
import copy


import matplotlib.pyplot as plt


def map_to_log_scale(value, min_value, max_value, logbase):
    # Calculate the logarithmic scale
    log_min = log(min_value,logbase)
    log_max = log(max_value,logbase)

    # Map the value to the logarithmic scale
    log_value = log(value,logbase)

    # Map the logarithmic value to the range [0, 1]
    mapped_value = (log_value - log_min) / (log_max - log_min)

    return mapped_value

#### TEST ####
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Argument for Analyzing")
    parser.add_argument('--exID', type=int, help='experiment id', default=16)
    parser.add_argument('--acc', type=float, help='accuracy requirement', default=0.6)

    
    

    # Parse the parameters
    args = parser.parse_args()
    runID = int(args.exID)
    accuracyRequirement = float(args.acc)

    filePath = "./report/reduceScale.csv"

    dfScaleReduction = pd.read_csv(filePath)


    # y1 = []
    # x1 = []
    # y2 = []
    # x2 = []
    # fig1, ax1 = plt.subplots()
    # n2DF = dfScaleReduction[dfScaleReduction["nModel"] == 3]
    # for index, row in n2DF.iterrows():
    #     x1.append(row["throughtput"])
    #     y1.append(row["nIteration_noScaleReduction"])
    #     x2.append(row["throughtput"])
    #     y2.append(row["nIteration_ScaleReduction"])
    # print(x1)
    # ax1.semilogy(x1, y1, label='Without Scale Reduction')
    # ax1.semilogy(x2, y2, label='With Scale Reduction') 
    # ax1.set_xlabel('Throughput Requirement')
    # ax1.set_ylabel('Number of Iteration')
    # ax1.set_title('Number of ML model: 3')
    # ax1.legend()
    # plt.savefig("./plot/ScaleReductionP3.png")
    # plt.show()


    # y3 = []
    # x3 = []
    # y4 = []
    # x4 = []
    # fig2, ax2 = plt.subplots()
    # n2DF = dfScaleReduction[dfScaleReduction["nModel"] == 3]
    # for index, row in n2DF.iterrows():
    #     x3.append(row["throughtput"])
    #     y3.append(row["minCost_noScaleReduction"])
    #     x4.append(row["throughtput"])
    #     y4.append(row["minCost_ScaleReduction"])
    # print(x1)
    # ax2.plot(x3, y3, label='Without Scale Reduction')
    # ax2.plot(x4, y4, label='With Scale Reduction') 
    # ax2.set_xlabel('Throughput Requirement')
    # ax2.set_ylabel('Optimal Cost')
    # ax2.set_title('Number of ML model: 3')
    # ax2.legend()
    # plt.savefig("./plot/ScaleReductionP3Cost.png")
    # plt.show()


    y = [100,200,300,400,500,600,700,800,900,1000]
    x = [1,2,3,4,5,6,7,8,9,10]
    y5 =[]
    for i in y:
        y5.append(map_to_log_scale(i,1,1000, 2))
    
    # fig2, ax2 = plt.subplots()
    fig3, ax3 = plt.subplots()
    # ax2.plot(x, y, label='Without Scale Reduction')
    ax3.plot(x, y5, label='With Scale Reduction') 
    plt.show()