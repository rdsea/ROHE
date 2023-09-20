import requests,time
from threading import Thread
import os, random,json
import numpy as np
from qoa4ml.reports import Qoa_Client
import qoa4ml.qoaUtils as qoa_utils


def init_env_variables():
    # Get Pod ID: for monitoring
    pod_id = os.environ.get('POD_ID')
    if not pod_id:
        print("POD_ID is not defined")
        pod_id = "Empty"
    # Get Node name: for monitoring
    node_name = os.environ.get('NODE_NAME')
    if not node_name:
        print("NODE_NAME is not defined")
        node_name = "Empty"
    # Get Database Url
    num_thread = os.environ.get('NUM_THREAD')
    if not num_thread:
        print("NUM_THREAD is not defined")
        num_thread = 1
    # Get Database name
    time_sleep = os.environ.get('TIME_SLEEP')
    if not time_sleep:
        print("DATABASE_NAME is not defined")
        time_sleep = -1
    # Get user collection name
    service_url = os.environ.get('SERVICE_URL')
    if not service_url:
        print("SERVICE_URL is not defined")
        service_url = "http://0.0.0.0:8000/"
    # Get configuration file
    conf_file = os.environ.get('CONF_FILE')
    if not conf_file:
        print("CONF_FILE is not defined")
        conf_file = "/conf.json"
    
    return {
        "pod_id": pod_id,
        "node_name": node_name,
        "num_thread": num_thread,
        "time_sleep": time_sleep,
        "service_url": service_url,
        "conf_file": conf_file
    }
env_var = init_env_variables()

concurrent = int(env_var["num_thread"])
time_sleep = float(env_var["time_sleep"])
url = str(env_var["service_url"])
conf_file = env_var["conf_file"]
config_path = os.path.dirname(__file__)
configuration = qoa_utils.load_config(config_path+conf_file)
client_config = configuration["client_config"]
connector_conf = configuration["connector_conf"]


client_qoa = Qoa_Client(client_config,connector_conf)
client_conf = configuration["client_app"]
client_qoa.init_report(client_conf["instance_id"], client_conf["method"], client_conf["stage_id"])

def sender(num_thread):
    count = 0
    error = 0
    start_time = time.time()
    while (time.time() - start_time < 600):
        try:
            print("This is thread: ",num_thread, "Starting request: ", count)
            ran_file = random.choice(os.listdir("./image"))
            files = {'image': open("./image/"+ran_file, 'rb'), 'user_data':json.dumps(client_config).encode('utf-8')}
            response = requests.post(url, files=files)
            prediction = response.json()
            print(prediction["prediction"])
            # image = np.asarray((prediction["image"]))
            print("Thread - ",num_thread, " Response:" )
            count += 1
            if time_sleep == -1:
                time.sleep(1)
            else:
                time.sleep(time_sleep)
        except Exception as e:
            error +=1
            print("[Error]: ", e)



if __name__ == '__main__':
 
    for i in range(concurrent):
        t = Thread(target=sender,args=[i])
        t.start()