import duckdb
import logging
import traceback
import yaml
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Timer, Lock
import sys
import os
import ast
import uuid
import copy
import requests
import json
ROHE_PATH = os.getenv('ROHE_PATH', '../..')
sys.path.append(ROHE_PATH)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
from rohe.orchestration.multimodal_abstration import InferenceQuery, InferenceServiceProfile, InferenceServiceInstance, ServiceLevelAgreement, InferenceTask, TaskList, TaskStatus, CommonMetric, InstanceStatus, InferenceResult, MonitoringClient, Explainability
import multiprocessing
from userModule.algorithm.multimodal_workflow import assigning_phase_with_longest_sequence
from userModule.algorithm import multimodal_ensemble


def kill_process_after_timeout(proc: multiprocessing.Process):
    if proc.is_alive():
        print("Timeout reached. Terminating process.")
        proc.terminate()

class AdaptiveOrchestrator:
    def __init__(self, config_path: str = '../config/orchestrator.yaml'):
        self.config_path = config_path
        self.config = {}
        self.db_path = None
        self.db_conn = None
        self.lock = Lock()
        self.monitoring_table = None
        self.inference_service_table = None
        self.inference_service_instance_table = None
        self.update_interval = None
        self.inference_service = {}
        self.inference_service_instance = {}
        self.time_proportions = {}
        self.data_hub_url = None
        self.process_timeout = 10
        self.max_workers = 10
        self.test_mode = True
        self.default_inference_url = None
        self.default_overhead = 0.01  
        self.prepare_process = None
        self.inference_result_table = None
        self.schedule_load_quality_profile()
        
        
    def load_config(self):
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            logging.debug(f"Configuration loaded: {self.config}")
            self.db_path = self.config.get('database_file', '../database/file.duckdb')
            self.monitoring_table = self.config.get('monitoring_table', 'monitoring_report')
            self.inference_service_table = self.config.get('inference_service_table', 'inference_service')
            self.inference_service_instance_table = self.config.get('inference_service_instance_table', 'inference_service_instance')
            self.update_interval = self.config.get('update_interval', 100)
            self.sla_path = self.config.get('sla_path', './sla.yaml')
            sla_dict = yaml.safe_load(open(self.sla_path, 'r'))
            self.sla = {}
            for key, value in sla_dict.items():
                self.sla[key] = ServiceLevelAgreement.from_dict(value)
            logging.debug(f"Loaded SLA: {self.sla}")
            self.time_proportions = self.config.get('time_proportions', {})
            self.data_hub_url = self.config.get('data_hub_url', 'http://localhost:5550/query_data')
            self.max_workers = self.config.get('max_workers', 10)
            self.process_timeout = self.config.get('process_timeout', 10)
            self.test_mode = self.config.get('test_mode', True)
            self.default_inference_url = self.config.get('default_inference_url', None)
            self.default_overhead = self.config.get('default_overhead', 0.01)
            self.inference_result_table = self.config.get('inference_result_table', 'inference_result')
        except Exception as e:
            logging.error(f"Failed to load configuration: {e}")
            raise e

    def update_inference_service(self):
        """Update inference service information from the database."""
        try:
            with self.lock:
                connection = duckdb.connect(self.db_path)
                self.inference_service = {}
                query = f"SELECT * FROM {self.inference_service_table}"
                result = connection.execute(query).fetchall()
                if result:
                    for service_row in result:
                        data_row = ast.literal_eval(service_row[5])
                        tmp_service = InferenceServiceProfile.from_dict(data_row)
                        self.inference_service[tmp_service.inference_service_id] = tmp_service
                connection.close()
            logging.debug(f"{len(self.inference_service)} inference services updated")
        except Exception as e:
            logging.error(f"Failed to update inference services: {e}")
            traceback.print_exc()
    
    def update_inference_service_instance(self):
        """Update inference service instance information from the database."""
        try:
            with self.lock:
                connection = duckdb.connect(self.db_path)
                self.inference_service_instance = {}
                query = f"SELECT * FROM {self.inference_service_instance_table}"
                result = connection.execute(query).fetchall()
                if result:
                    for instance_row in result:
                        data_row = ast.literal_eval(instance_row[9])
                        if self.test_mode:
                            data_row['inference_url'] = self.default_inference_url
                        tmp_instance = InferenceServiceInstance.from_dict(data_row)
                        self.inference_service_instance[tmp_instance.instance_id] = tmp_instance
                connection.close()
            logging.debug(f"{len(self.inference_service_instance)} inference service instances updated")
        except Exception as e:
            logging.error(f"Failed to update inference service instances: {e}")
            traceback.print_exc()

    def orchestrate(self, inference_query: InferenceQuery):
        """Orchestrate inference requests based on the query."""
        start_time = time.perf_counter()
        try:
            query_id = str(uuid.uuid4())
            consumer_id = inference_query.metadata.get('consumer_id', 'unknown')
            access_privileges, tenant_sla = self.get_access_privileges(consumer_id)
            logging.debug(f"Consumer {consumer_id} has access privileges: {access_privileges}, requested data sources: {inference_query.data_source}")
            data_source = inference_query.data_source
            inference_query.query_id = query_id
            for source in data_source:
                if source not in access_privileges:
                    logging.warning(f"Consumer {consumer_id} does not have access to data source {source}")
                    return {"Error": f"Access denied to data source {source}"}
                
            # If all data sources are accessible, proceed with the orchestration
            # Execute inference in separate thread for a given time, if it exceeds the time limit, it will killed
            proc = multiprocessing.Process(target=self.execute_inference, args=(start_time, inference_query, tenant_sla))
            proc.start()
            Timer(self.process_timeout, kill_process_after_timeout, args=(proc,)).start()
            return {"Success": "Orchestration completed successfully", "query_id": query_id}

        except Exception as e:
            logging.error(f"Orchestration failed: {e}")
            traceback.print_exc()
            return None

    def execute_inference(self, start_time: float, inference_query: InferenceQuery, tenant_sla: ServiceLevelAgreement):
        """Execute inference based on the query."""
        try:
            logging.debug(f"Executing inference for query on: {inference_query.data_source}")
            ############## Step 1: Data preparation ###############
            task_list = TaskList()
            ensemble_size = tenant_sla.ensemble_size
            ensemble_selection_strategy = tenant_sla.ensemble_selection_strategy
            explainability = inference_query.explainability
            monitoring_client = MonitoringClient(monitoring_url=self.db_path, metric_table=self.monitoring_table)
            for modality in inference_query.data_source:
                task_id = str(uuid.uuid4())
                inf_task = InferenceTask(task_id=task_id, modality=modality, status="pending", phase=0, inference_query=inference_query, ensemble_size=ensemble_size, ensemble_selection_strategy=ensemble_selection_strategy, monitoring_client=monitoring_client, explainability=explainability)
                task_list.add_task(inf_task)
            
            ##### run in another process to avoid blocking the main process #####
            self.prepare_process = multiprocessing.Process(target=self.prepare_data, args=(task_list,))
            self.prepare_process.start()
            self.prepare_process.join()

            task_list = self.get_inf_task_info(task_list)
            e2e_response_time = inference_query.constraint.get(CommonMetric.RESPONSE_TIME.value, 5)
            inference_result = InferenceResult(inference_time = time.perf_counter())
            step_1_execution_time = time.perf_counter() - start_time
            logging.debug(f"######## Step 1 execution time: {step_1_execution_time:.4f} seconds")
            remaining_time = e2e_response_time - step_1_execution_time
            # Loop until all tasks are processed or time violation occurs
            self.task_execution_loop(task_list=task_list, inference_query=inference_query, start_time=start_time, e2e_response_time=e2e_response_time, intermediate_result=inference_result)
            inference_result.get_avg_from_aggregated_sum()
            inference_time = time.perf_counter() - start_time
            violation = inference_time > e2e_response_time
            inference_result.metadata = {
                'remaining_time': remaining_time,
                'time_violation': violation
            }
            self.report_inference_result(inference_result)
            logging.info(f"Total inference time: {inference_time:.4f} seconds, Violation: {violation}")
            logging.debug(f"Final inference result after: {inference_result}")
        except Exception as e:
            logging.error(f"Inference execution failed: {e}")
            traceback.print_exc()
            
    def report_inference_result(self, inference_result: InferenceResult):
        try:
            connection = duckdb.connect(self.db_path)
            result_dict = inference_result.to_dict()
            connection.execute(f"""CREATE TABLE IF NOT EXISTS {self.inference_result_table} (
                inference_time TEXT,
                data JSON,
                query_id TEXT,
                task_id TEXT,
                inf_id TEXT);""")
            connection.execute(f"""
                INSERT INTO {self.inference_result_table} 
                VALUES ( ?, ?, ?, ?, ?);
            """, (
                result_dict['inference_time'],
                json.dumps(result_dict['data']),
                result_dict['query_id'],
                result_dict['task_id'],
                result_dict['inf_id']
            ))
            connection.close()
            logging.info(f"Inference result reported: {result_dict}")
        except Exception as e:
            logging.error(f"Failed to report inference result: {e}")
            traceback.print_exc()

    def task_execution_loop(self, task_list: TaskList, inference_query: InferenceQuery, start_time: float, e2e_response_time: float, intermediate_result: InferenceResult):
        try:
            time_violation = False
            if self.check_pending_tasks(task_list) and not time_violation:
                ################ Step 2: Determine execution workflow ###############
                step_2_start_time = time.perf_counter()
                remaining_time = e2e_response_time - (time.perf_counter() - start_time)
                logging.debug(f"Remaining time for inference: {remaining_time:.2f} seconds")
                if remaining_time <= 0:
                    time_violation = True
                    logging.warning(f"Time violation detected for query: {inference_query.metadata.get('consumer_id', 'unknown')}")
                else:
                    task_list = self.determine_execution_workflow(inference_query=inference_query, task_list=task_list, start_time=start_time, e2e_response_time=e2e_response_time)
                    logging.info("#" * 40)
                    for task in task_list.data:
                        logging.info(f"Task {task.task_id} - Modality: {task.modality}, Phase: {task.phase}, Allocated Time: {task.allocated_time}")
                step_2_execution_time = time.perf_counter() - step_2_start_time
                logging.debug(f"######## Step 2 execution time: {step_2_execution_time:.4f} seconds")
                ################ Step 3:Distribute Inference Workload ###############
                step_3_start_time = time.perf_counter()
                task_list = self.distribute_inference_workload(task_list, intermediate_result)
                step_3_execution_time = time.perf_counter() - step_3_start_time
                logging.debug(f"######## Step 3 execution time: {step_3_execution_time:.4f} seconds")
                ############### Step 4: Invoke Inference Tasks ###############
                # Get all tasks in phase 0 and drop them from the task list
                step_4_start_time = time.perf_counter()
                phase_0_tasks = [task for task in task_list.data if task.phase == 0]
                task_list.data = [task for task in task_list.data if task.phase != 0]
                first_finished = True
                if self.prepare_process is not None:
                    self.prepare_process.join()
                    self.prepare_process = None
                if phase_0_tasks:
                    recurrent_task_execution = None
                    
                    with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                        futures = {executor.submit(task.execute): task for task in phase_0_tasks}
                        remaining_time = e2e_response_time - (time.perf_counter() - start_time)
                        try:
                            # for future in as_completed(futures, timeout=remaining_time):
                            for future in as_completed(futures):
                                task_inf_result = future.result()
                                with self.lock:
                                    intermediate_result.aggregate(task_inf_result)
                                if first_finished:
                                    first_finished = False
                                    recurrent_task_execution = executor.submit(self.task_execution_loop, task_list=task_list, inference_query=inference_query, start_time=start_time, e2e_response_time=e2e_response_time, intermediate_result=intermediate_result)
                            step_4_execution_time = time.perf_counter() - step_4_start_time
                            logging.debug(f"######## Step 4 execution time: {step_4_execution_time:.4f} seconds")
                        except TimeoutError:
                            logging.warning(f"Task execution timed out after {self.process_timeout} seconds.")
                            return TaskStatus.FAILED.value
                        if recurrent_task_execution != None:
                            recurrent_task_status = recurrent_task_execution.result()  # Wait for the recursive call to finish
                            if recurrent_task_status == None:
                                logging.debug(f"Number of remaining tasks: {len(task_list.data)}")
                            else:
                                logging.debug(f"Recurrent task execution status: {recurrent_task_status}")
                return TaskStatus.COMPLETED.value
        except Exception as e:
            logging.error(f"Task execution loop failed: {e}")
            traceback.print_exc()

    def prepare_data(self, task_list: TaskList):
        inf_id_dict = {}
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for task in task_list.data:
                    modality = task.modality
                    time_window = task.inference_query.time_window
                    task_id = task.task_id
                    futures.append(executor.submit(self.send_data_request, modality, time_window, task_id))
                for future in as_completed(futures):
                    try:
                        data_request_response = future.result()
                        logging.debug(f"Data request response: {data_request_response}")
                    except Exception as e:
                        logging.error(f"Failed to get data for {modality}: {e}")
                        traceback.print_exc()
            if not inf_id_dict:
                logging.warning("No data was prepared for inference. Check data sources and time window.")
            return inf_id_dict
        except Exception as e:
            logging.error(f"Failed to prepare data: {e}")
            traceback.print_exc()
            return inf_id_dict
        
    def send_data_request(self, stream_id: str, time_window: int, task_id: str):
        result = {}
        try:
            data_request = {
                "inf_id": task_id,
                "stream_id": stream_id,
                "window_size": time_window
            }
            response = requests.post(self.data_hub_url, json=data_request)
            if response.status_code == 200:
                result = response.json()
            return result 
        except Exception as e:
            logging.error(f"Failed to send data request for {stream_id}: {e}")
            traceback.print_exc()
            return result

    def determine_execution_workflow(self, inference_query: InferenceQuery, task_list: TaskList, start_time: float, e2e_response_time: float = 5):
        try:
            # start_time = time.perf_counter()
            remaining_time = e2e_response_time - (time.perf_counter() - start_time)
            consumer_id = inference_query.metadata.get('consumer_id', 'unknown')
            task_list = self.get_time_allocation(consumer_id=consumer_id, task_list=task_list, remaining_time=remaining_time)
            # check_point_0 = time.perf_counter() - start_time
            # logging.info(f"######## Checkpoint 0 execution time: {check_point_0:.2f} seconds")
            # Placeholder for actual logic
            # check_point_1 = time.perf_counter() - start_time
            # logging.info(f"######## Checkpoint 1 execution time: {check_point_1:.2f} seconds")
            task_list = assigning_phase_with_longest_sequence(task_list, remaining_time)
            for task in task_list.data:
                logging.debug(f"Modality: {task.modality}, Services: {len(task.inference_services)}, Instances: {len(task.inference_instances)}, Min Execution Time: {task.min_execution_time}, Max Execution Time: {task.max_execution_time}, Allocated Time: {task.allocated_time}, Phase: {task.phase}, Status: {task.status}")
            # check_point_2 = time.perf_counter() - start_time
            # logging.info(f"######## Checkpoint 2 execution time: {check_point_2:.2f} seconds")
            return task_list
        except Exception as e:
            logging.error(f"Failed to determine execution workflow: {e}")
            traceback.print_exc()
            return None
        
    def get_inf_task_info(self, task_list: TaskList):
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for task in task_list.data:
                    futures.append(executor.submit(self.filter_instances, task))

                for future in as_completed(futures):
                    if future.result() is not None:
                        future.result()
                            
                                
            return task_list
        except Exception as e:
            logging.error(f"Failed to get inference task info: {e}")
            traceback.print_exc()
            return None
        
    def filter_instances(self, task: InferenceTask):
        try:
            modality = task.modality
            min_execution_time = float('inf')
            max_execution_time = float('-inf')
            min_execution_time_ex = float('inf')
            max_execution_time_ex = float('-inf')
            # filtered_services = {}
            filtered_instances = {}
      
            for key_id, instance in self.inference_service_instance.items():
                if modality == instance.modality and instance.status == InstanceStatus.AVAILABLE.value: # not in contention and failed
                    if instance.runtime_performance == []:
                        raise ValueError(f"Runtime performance for instance {instance.instance_id} is empty.")
                    filtered_instances[key_id] = copy.deepcopy(instance)
                    # inference_service_id = instance.inference_service_id
                    # if inference_service_id not in list(filtered_services.keys()):
                    #     filtered_services[inference_service_id] = copy.deepcopy(self.inference_service[inference_service_id])
                    for metric in instance.runtime_performance:
                        if metric.metric_name == CommonMetric.RESPONSE_TIME.value:
                            if metric.condition == Explainability.ENABLED.value:
                                if metric.value < min_execution_time_ex:
                                    min_execution_time_ex = metric.value
                                if metric.value > max_execution_time_ex:
                                    max_execution_time_ex = metric.value
                            elif metric.condition == Explainability.DISABLED.value:
                                if metric.value < min_execution_time:
                                    min_execution_time = metric.value
                                if metric.value > max_execution_time:
                                    max_execution_time = metric.value
            task.min_execution_time = min_execution_time
            task.max_execution_time = max_execution_time
            # task.inference_services = filtered_services
            task.inference_instances = filtered_instances
            task.min_execution_time_ex = min_execution_time_ex
            task.max_execution_time_ex = max_execution_time_ex
            # task.inference_services_ex = copy.deepcopy(filtered_services)
            task.status = TaskStatus.PENDING.value
        except Exception as e:
            logging.error(f"Failed to find minimum execution time for modality {modality}: {e}")
            traceback.print_exc()

    def get_time_allocation(self, consumer_id: str, task_list: TaskList, remaining_time: float):
        try:
            time_proportions = copy.deepcopy(self.time_proportions.get(consumer_id, {}))
            
            for task in task_list.data:
                modality = task.modality
                if task.allocated_time is None:
                    if modality in time_proportions:
                        task.allocated_time = time_proportions[modality]* remaining_time
                    else:
                        task.allocated_time = remaining_time
                    self.update_task_allocation_time(task)
                else:
                    if task.allocated_time > remaining_time:
                        task.allocated_time = remaining_time
                        self.update_task_allocation_time(task)

        except Exception as e:
            logging.error(f"Failed to get time allocation: {e}")
            traceback.print_exc()
        return task_list
    
    def update_task_allocation_time(self, task: InferenceTask):
        try:
            task.allocated_time = max(task.min_execution_time, task.allocated_time)
            task.allocated_time = min(task.allocated_time, task.max_execution_time)
            instance_id_list = list(task.inference_instances.keys())
            task.inference_instances_ex = copy.deepcopy(task.inference_instances)
            for instance_id in instance_id_list:
                instance = task.inference_instances[instance_id]
                for metric in instance.runtime_performance:
                    if metric.metric_name == CommonMetric.RESPONSE_TIME.value:
                        if metric.condition == Explainability.DISABLED.value:
                            if metric.value > task.allocated_time:
                                # drop the instance
                                task.inference_instances.pop(instance_id, None)
                            else:
                                service_id = instance.inference_service_id
                                if service_id not in list(task.inference_services.keys()):
                                    task.inference_services[service_id] = copy.deepcopy(self.inference_service[service_id])
                        elif metric.condition == Explainability.ENABLED.value:
                            if metric.value > task.allocated_time:
                                # drop the instance
                                task.inference_instances_ex.pop(instance_id, None)
                            else:
                                service_id = instance.inference_service_id
                                if service_id not in list(task.inference_services_ex.keys()):
                                    task.inference_services_ex[service_id] = copy.deepcopy(self.inference_service[service_id])
        except Exception as e:
            logging.error(f"Failed to update task allocation time: {e}")
            traceback.print_exc()
    
    def schedule_load_quality_profile(self):
        try:
            self.load_config()
            self.update_inference_service()
            self.update_inference_service_instance()
            logging.info("Inference service and instance profiles updated")
            # Start the timer again
            Timer(self.update_interval, self.schedule_load_quality_profile).start()
        except Exception as e:
            logging.error(f"Failed to schedule load quality profile: {e}")
            traceback.print_exc()
            # Retry after a delay
            Timer(self.update_interval, self.schedule_load_quality_profile).start()
    
    def get_access_privileges(self, consumer_id: str):
        """Get access privileges for the inference query."""
        access_privileges = []
        tenant_sla = None
        try:
            for key, value in self.sla.items():
                if consumer_id in value.consumer_list:
                    access_privileges.extend(value.access_privileges)
                    tenant_sla = value
        except Exception as e:
            logging.error(f"Failed to get access privileges: {e}")
            traceback.print_exc()
        return access_privileges, tenant_sla

    def distribute_inference_workload(self, task_list: TaskList, intermediate_result: InferenceResult):
        """Distribute inference workload across available instances."""
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(self.select_ensemble, task, intermediate_result): task for task in task_list.data}
                for future in as_completed(futures):
                    future.result()
            for task in task_list.data:
                logging.debug(f"Task {task.task_id}, number of selected instances: {len(task.selected_instances)}")
            return task_list
        except Exception as e:
            logging.error(f"Failed to distribute inference workload: {e}")
            traceback.print_exc()
            return task_list
    
    def select_ensemble(self, task: InferenceTask, intermediate_result: InferenceResult):
        """Select ensemble of inference services for the task."""
        try:
            ensemble_size = task.ensemble_size
            function_name = task.ensemble_selection_strategy
            selection_method = getattr(multimodal_ensemble, function_name, None)
            if selection_method is None:
                logging.error(f"Ensemble selection method {function_name} not found.")
                return None
            selection_method(task, intermediate_result, ensemble_size)
            return task
        except Exception as e:
            logging.error(f"Failed to select ensemble for task {task.task_id}: {e}")
            traceback.print_exc()
            return None
        
    def check_pending_tasks(self, task_list: TaskList):
        """Check for pending tasks and update their status."""
        try:
            with self.lock:
                for task in task_list.data:
                    if task.status == TaskStatus.PENDING.value:
                        return True
            return False
        except Exception as e:
            logging.error(f"Failed to check pending tasks: {e}")
            traceback.print_exc()
            return True