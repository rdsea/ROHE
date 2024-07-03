import os

try:
    ROHE_PATH = os.environ["ROHE_PATH"]
except KeyError:
    raise RuntimeError("ROHE_PATH is not defined, please defined it ")
