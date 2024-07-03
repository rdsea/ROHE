# import string, random
import json
import queue
import threading

from .utilities.transceiver import AmqpTransceiver, RestTransceiver, ZmqTransceiver


class TaskHandler:
    def __init__(self, configuration):
        # Init the main process of the task
        self.task_conf = configuration["task_configuration"]
        # self.processing_task = Processing_Task(configuration["task_info"])

        # loader = importlib.machinery.SourceFileLoader(self.task_conf['function']['module_name'], self.task_conf['function']['patch'])
        # spec = importlib.util.spec_from_loader(self.task_conf['function']['module_name'],loader)
        # self.processing_task = importlib.util.module_from_spec(spec)
        # loader.exec_module(self.processing_task)
        # self.method_to_call = getattr(self.processing_task, self.task_conf['function']['main_function'])

        user_module = __import__(
            "userapp." + self.task_conf["function"]["package"],
            fromlist=[self.task_conf["function"]["module_name"]],
        )
        self.user_class = getattr(
            user_module, self.task_conf["function"]["module_name"]
        )
        self.user_object = self.user_class(self.task_conf)
        self.user_function = getattr(
            self.user_object, self.task_conf["function"]["function_name"]
        )

        # Init Task Queue
        self.task_queue = queue.Queue(configuration["queue_size"])

        # Init data downstream
        self.downstream_conf = configuration["downstream"][0]
        if self.downstream_conf["protocol"] == "AMQP":
            # self.downstream_conf["configuration"]["in_queue"] =  self.downstream_conf["configuration"]["in_queue"] + self.get_random_string(5)
            self.downstream = AmqpTransceiver(
                self, self.downstream_conf["configuration"]
            )
        elif self.downstream_conf["protocol"] == "REST":
            self.downstream = RestTransceiver(
                self, self.downstream_conf["configuration"]
            )
        elif self.downstream_conf["protocol"] == "ZMQ":
            self.downstream = ZmqTransceiver(
                self, self.downstream_conf["configuration"]
            )

        # Init data upstream (to next task)
        self.upstream_conf = configuration["upstream"][0]
        if self.upstream_conf["protocol"] == "AMQP":
            self.upstream = AmqpTransceiver(self, self.upstream_conf["configuration"])
        elif self.upstream_conf["protocol"] == "REST":
            self.upstream = RestTransceiver(self, self.upstream_conf["configuration"])
        elif self.upstream_conf["protocol"] == "ZMQ":
            self.upstream = ZmqTransceiver(self, self.upstream_conf["configuration"])

        # Create a thread for receiving data
        self.mess_sub_thread = threading.Thread(target=self.upstream.run)

        # Init task monitor
        self.monitor_conf = configuration["monitor"]
        self.heartbeat_time = self.monitor_conf["heartbeat"]
        self.report_metadata = {}
        self.report_metadata["routing_key"] = self.monitor_conf["configuration"][
            "routing_key"
        ]
        self.report_metadata["exchange_name"] = self.monitor_conf["configuration"][
            "exchange_name"
        ]
        self.report_metadata["corr_id"] = "0"
        self.report = {}
        self.report["task_id"] = self.monitor_conf["task_id"]
        self.count_request = 0
        self.last_count = 0
        self.report["waiting_request"] = self.task_queue.qsize()
        self.monitor = AmqpTransceiver(self, self.monitor_conf["configuration"])
        self.mess_received = 0

        # Init heartbeat to update task status
        self.heartbeat = threading.Timer(self.heartbeat_time, self.send_task_report)

        # Start - Stop Flag
        self.run_flag = True

    def attache_header(self, mess, metadata):
        try:
            data = {}
            data["header"] = {}
            data["header"]["routing_key"] = metadata["props"].reply_to
            data["header"]["corr_id"] = metadata["props"].correlation_id
            data["content"] = mess
            data["raw"] = mess
            return data
        except Exception as e:
            print(f"Error when adding header {e}")
            return None

    # The call-back function when receiving message
    def message_processing(self, mess, metadata=None):
        # Format the message to json object
        format_mess = self.format_mess(mess)
        obj_mess = json.loads(format_mess)
        self.mess_received += 1
        # Adding the header if the message hasn't got any header.
        # The header is used to store info which is where return the result to client
        # Add the headered data to the Task Queue
        # if isinstance(obj_mess, list) == False:
        #     obj_mess = [obj_mess]
        # for i in range(len(obj_mess)):
        if "content" not in obj_mess:
            obj_mess = self.attache_header(obj_mess, metadata)
        self.task_queue.put_nowait(obj_mess)
        print("Current waiting queue: ", self.task_queue.qsize())

    def send(self, data):
        # Return result to client
        if self.downstream_conf["protocol"] == "AMQP":
            metadata = {}
            metadata["routing_key"] = data["header"]["routing_key"]
            metadata["corr_id"] = data["header"]["corr_id"]
            metadata["exchange_name"] = ""
            mess = data["content"]
            mess["request"] = data["raw"]
            self.downstream.send(str(json.dumps(mess)), metadata)
        # Send data to the next task
        else:
            self.downstream.send(str(json.dumps(data)))

    def send_task_report(self):
        n_request = self.count_request - self.last_count
        self.last_count = self.count_request
        self.report["waiting_request"] = self.task_queue.qsize()
        self.report["request_proc"] = n_request / self.heartbeat_time
        self.report["count_request"] = self.count_request
        self.report["mess_received"] = self.mess_received
        self.monitor.send(str(json.dumps(self.report)), self.report_metadata)
        print("send report: ", self.report)
        self.heartbeat = threading.Timer(self.heartbeat_time, self.send_task_report)
        self.heartbeat.start()

    def run(self):
        # Start a thread for receiving data
        self.mess_sub_thread.start()
        self.heartbeat.start()
        # Take the request from task Queue to process
        while self.run_flag:
            if not self.task_queue.empty():
                data = self.task_queue.get_nowait()
                self.count_request += 1
                data["content"] = self.processing(data["content"])
                if data is not None:
                    self.send(data)

    def stop(self):
        self.run_flag = False
        self.heartbeat.cancel()

    def processing(self, data):
        # Invoke user processing application
        return self.user_function(data)
        # return self.processing_task.process(data, self.task_conf)

    def format_mess(self, mess):
        # Format the message
        if isinstance(mess, str):
            return mess
        else:
            return str(mess.decode("utf-8"))

    # def get_random_string(self, length):
    #     # choose from all lowercase letter
    #     letters = string.ascii_lowercase
    #     return ''.join(random.choice(letters) for i in range(length))
