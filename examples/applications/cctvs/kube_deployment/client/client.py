import argparse
import json
import os
import random
import time
from threading import Thread

import requests

parser = argparse.ArgumentParser(description="Data processing")
parser.add_argument("--th", help="number concurrent thread", default=1)
parser.add_argument("--sl", help="time sleep", default=1.0)
args = parser.parse_args()
concurrent = int(args.th)
time_sleep = float(args.sl)
url = "http://127.0.0.1:5004/inference"


def sender(num_thread):
    count = 0
    start_time = time.time()
    while time.time() - start_time < 600:
        print("This is thread: ", num_thread, "Starting request: ", count)
        ran_file = random.choice(os.listdir("./image"))
        files = {"image": open("./image/" + ran_file, "rb")}
        response = requests.post(url, files=files)
        print("Thread - ", num_thread, " Response:", json.loads(response.content))
        count += 1
        time.sleep(time_sleep)


for i in range(concurrent):
    t = Thread(target=sender, args=[i])
    t.start()
