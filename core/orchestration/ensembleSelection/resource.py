import traceback
import argparse
import sys, os
# User must export ROHE_PATH befor using
ROHE_PATH = os.getenv("ROHE_PATH")
sys.path.append(ROHE_PATH)
from lib import roheUtils

import random, uuid
from math import log10, log

from core.orchestration.ensembleSelection.function import *

DEFAULT_OBJECT_CONFIG = ROHE_PATH + "/config/nii/classObject.yaml"
DEFAULT_BASE_COST = 500
DEFAULT_MULTI_BASE_COST = 2
classConfig = roheUtils.load_config(DEFAULT_OBJECT_CONFIG)
DEFAULT_NSPECIALIZE = [2,2,3,3,4,4]
DEFAULT_CPU_SETUP = [4, 16, 32]
DEFAULT_MEM_SETUP = [4, 8, 64]
DEFAULT_CPU_FREQ = [1.5, 2.3, 3.5]



class MLModel(object):
    def __init__(self, tier=None, baseCost=None, specialize=None) -> None:
        if tier != None:
            self.tier = tier
        if baseCost != None:
            self.baseCost = baseCost
        if specialize != None:
            self.specialize = specialize
        self.modelID = str(uuid.uuid4())
        self.wThroughput = 0
        self.bThroughput = 0
        
        if tier == None:
            self.tier = random.randint(1,6)
        if baseCost == None:
            self.baseCost = DEFAULT_BASE_COST*log10(self.tier*DEFAULT_MULTI_BASE_COST)
        if specialize == None:
            self.nSpecialize = DEFAULT_NSPECIALIZE[self.tier-1]
            self.specialize = roheUtils.getNSampleInRange(self.nSpecialize, 0, 13)
            self.specializeName = []
            for item in self.specialize:
                self.specializeName.append(classConfig[str(item)])
        # To Do: improve fomular
        self.costPerRequest = self.baseCost/1000

        self.accuracy = {}
        for i in range(0,13):
            if i in self.specialize:
                self.accuracy[str(i)] = random.uniform(0.6, 0.8)*log10(10+self.tier)
            else:
                self.accuracy[str(i)] = random.uniform(0.1, 0.3)*log10(10+self.tier)
        self.confidence = {}
        for i in range(0,13):
            if i in self.specialize:
                self.confidence[str(i)] = random.uniform(0.5, 0.7)*log10(10+self.tier)
            else:
                self.confidence[str(i)] = random.uniform(0.1, 0.3)*log10(10+self.tier)

    def exportFeature(self):
        # collect all features
        feature = {}
        feature["tier"] = self.tier
        feature["baseCost"] = self.baseCost
        feature["specialize"] = self.specialize
        feature["wThroughput"] = self.wThroughput
        feature["bThroughput"] = self.bThroughput
        feature["nSpecialize"] = self.nSpecialize 
        feature["specializeName"] = self.specializeName
        feature["costPerRequest"] = self.costPerRequest
        feature["accuracy"] = self.accuracy
        feature["confidence"] = self.confidence
        modelDict = {self.modelID:feature}
        return modelDict
    
    def importFeature(self, feature, modelID):
        self.modelID = modelID
        self.tier = feature["tier"]
        self.baseCost = feature["baseCost"] 
        self.specialize = feature["specialize"]
        self.wThroughput = feature["wThroughput"] 
        self.bThroughput = feature["bThroughput"] 
        self.nSpecialize = feature["nSpecialize"] 
        self.specializeName = feature["specializeName"] 
        self.costPerRequest = feature["costPerRequest"]
        self.accuracy = feature["accuracy"]
        self.confidence = feature["confidence"]



    def __str__(self):
        return str({
            "ModelID": self.modelID,
            "Tier": self.tier,
            "BaseCost": self.baseCost,
            "Specialize":self.specializeName
        })

    def __repr__(self):
        return str({
            "ModelID": self.modelID,
            "Tier": self.tier,
            "BaseCost": self.baseCost,
            "Specialize":self.specializeName
        })
    
class PhysicalDevice(object):
    def __init__(self, frequency=None, CPU=None, GPU=None, mem=None, network=None, tier=None, baseCost=None) -> None:
        if tier != None:
            self.tier = tier
        if baseCost != None:
            self.baseCost = baseCost
        if frequency != None:
            self.frequency = frequency
        if CPU != None:
            self.CPU = CPU
        if GPU != None:
            self.GPU = GPU
        if mem != None:
            self.mem = mem
        if network != None:
            self.network = network
        self.deviceID = str(uuid.uuid4())
        # To Do: improve fomular
        

        if tier == None:
            self.tier = random.randint(1,3)
        if baseCost == None:
            self.baseCost = DEFAULT_BASE_COST*log10(self.tier*DEFAULT_MULTI_BASE_COST)
        if frequency == None:
            self.frequency = DEFAULT_CPU_FREQ[self.tier-1]
        if network == None:
            self.network = log10(1+self.tier)
        if CPU == None:
            self.CPU = DEFAULT_CPU_SETUP[self.tier-1]
        if mem == None:
            self.mem = DEFAULT_MEM_SETUP[self.tier-1]
        self.costPerRequest = self.baseCost/1000

    
    def exportFeature(self):
        # collect all features
        feature = {}
        feature["tier"] = self.tier
        feature["baseCost"] = self.baseCost
        feature["frequency"] = self.frequency
        feature["network"] = self.network
        feature["CPU"] = self.CPU 
        feature["mem"] = self.mem
        feature["costPerRequest"] = self.costPerRequest
        deviceDict = {self.deviceID:feature}
        return deviceDict
    
    def importFeature(self, feature, deviceID):
        self.deviceID = deviceID
        self.tier = feature["tier"]
        self.baseCost = feature["baseCost"] 
        self.frequency = feature["frequency"]
        self.network = feature["network"] 
        self.CPU = feature["CPU"] 
        self.mem = feature["mem"] 
        self.costPerRequest = feature["costPerRequest"]


    def __str__(self):
        return str({
            "DeviceID": self.deviceID,
            "Tier": self.tier,
            "BaseCost": self.baseCost,
        })

    def __repr__(self):
        return str({
            "DeviceID": self.deviceID,
            "Tier": self.tier,
            "BaseCost": self.baseCost,
        })

class ServiceDeployment(object):
    def __init__(self, mlModel:MLModel, physicalDevice:PhysicalDevice, replica=1) -> None:
        self.mlModel = mlModel
        self.replica = replica
        self.physicalDevice = physicalDevice
        self.processingTime = self.mlModel.tier/(4*log(self.physicalDevice.CPU,8))
        self.responseTime = self.physicalDevice.network+self.processingTime
        self.throughput = self.replica /self.processingTime
        self.baseCost = self.mlModel.baseCost + self.physicalDevice.baseCost
    
    def setReplica(self, replica):
        self.replica = replica
        self.throughput = self.replica /self.processingTime

    def exportFeature(self):
        # collect all features
        feature = {}
        feature["tier"] = self.tier
        feature["baseCost"] = self.baseCost
        feature["specialize"] = self.specialize
        feature["wThroughput"] = self.wThroughput
        feature["bThroughput"] = self.bThroughput
        feature["nSpecialize"] = self.nSpecialize 
        feature["specializeName"] = self.specializeName
        feature["costPerRequest"] = self.costPerRequest
        feature["accuracy"] = self.accuracy
        feature["confidence"] = self.confidence
        modelDict = {self.modelID:feature}
        return modelDict
    
    def importFeature(self, feature, modelID):
        self.modelID = modelID
        self.tier = feature["tier"]
        self.baseCost = feature["baseCost"] 
        self.specialize = feature["specialize"]
        self.wThroughput = feature["wThroughput"] 
        self.bThroughput = feature["bThroughput"] 
        self.nSpecialize = feature["nSpecialize"] 
        self.specializeName = feature["specializeName"] 
        self.costPerRequest = feature["costPerRequest"]
        self.accuracy = feature["accuracy"]
        self.confidence = feature["confidence"]

    def __str__(self):
        return str({
            "ModelTier": self.mlModel.tier,
            "deviceTier": self.physicalDevice.tier,
            "ProcessingTime": self.processingTime,
            "ResponseTime": self.responseTime,
            "throughput": self.throughput,
        })

    def __repr__(self):
        return str({
            "ModelTier": self.mlModel.tier,
            "deviceTier": self.physicalDevice.tier,
            "ProcessingTime": self.processingTime,
            "ResponseTime": self.responseTime,
            "throughput": self.throughput,
        })
    

