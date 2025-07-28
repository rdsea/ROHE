from pydantic import BaseModel, Field
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Union, Type
from enum import Enum
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import logging
import time
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
import os
import sys
import uuid
parent_dir = os.path.abspath(os.path.join(os.getcwd(), '..'))
sys.path.append(parent_dir)
import traceback
import duckdb

DEFAULT_INFERENCE_URL = 'http://localhost:6666/inference'


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"

class CommonMetric(Enum):
    RESPONSE_TIME = "response_time"
    ACCURACY = "accuracy"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    
class InstanceStatus(Enum):
    AVAILABLE = "available"
    FAILURE = "failure"
    CONTENTION = "contention"
    INACTIVE = "inactive"

class Explainability(Enum):
    DISABLED = 'normal'
    ENABLED = 'explainability'

class InferenceQuery(BaseModel):
    metadata: dict = Field(..., description="Metadata for about the consumer")
    data_source: list = Field(..., description="Data sources for the inference query")
    time_window: int = Field(..., description="Time window for the inference query")
    explainability: bool = Field(..., description="Whether to include explainability")
    constraint: dict = Field(..., description="Constraints for the inference query")
    query_id: Optional[str] = Field(None, description="Unique identifier for the query")
    
    def to_dict(self):
        """Convert the model to a dictionary."""
        return self.dict()
    
    def get_metadata(self):
        """Get metadata from the model."""
        return self.metadata
    
    def get_data_source(self):
        """Get data sources from the model."""
        return self.data_source
    
    def get_time_window(self):
        """Get time window from the model."""
        return self.time_window
    
    def get_explainability(self):
        """Get explainability flag from the model."""
        return self.explainability
    
    def get_constraint(self):
        """Get constraints from the model."""
        return self.constraint
    
    def get_response_time(self):
        """Get response time from the model."""
        return self.constraint.get('response_time', None)
    
    def __str__(self):
        """String representation of the model."""
        return f"InferenceQuery(\n  metadata={self.metadata}, \n  data_source={self.data_source}, \n  time_window={self.time_window}, \n  explainability={self.explainability}, \n  constraint={self.constraint}, \n  query_id={self.query_id})"

    def to_string(self):
        """Convert the model to a string."""
        return str(self)
    
class MonitoringReport(BaseModel):
    metadata: Optional[dict] = Field(None, description="Metadata for the monitoring report")
    query_id: str = Field(..., description="Unique identifier for the query")
    inf_id: Optional[str] = Field(None, description="Inference ID for the report")
    inf_time: float = Field(..., description="Inference time in seconds")
    data_source: Optional[Union[List[str], str]] = Field(..., description="Data sources used in the inference")
    time_window: Optional[float] = Field(None, description="Time window for the inference")
    model_id: str = Field(..., description="Model ID used for the inference")
    device_id: str = Field(..., description="Device ID used for the inference")
    instance_id: str = Field(..., description="Instance ID for the inference")
    response_time: float = Field(..., description="Response time in seconds")
    inf_result: dict = Field(..., description="Inference result data")
    model_version: Optional[str] = Field(None, description="Version of the model used for the inference")
    explainability: Optional[bool] = Field(False, description="Whether the report includes explainability data")
    time_violation: Optional[bool] = Field(False, description="Whether the report includes time violation data")
    time_for_inference: Optional[float] = Field(None, description="Remaining time for inference in seconds")
    
    def to_dict(self):
        """Convert the model to a dictionary."""
        return self.dict()
    def __str__(self):
        """String representation of the model."""
        return f"MonitoringReport(\n  metadata={self.metadata}, \n  query_id={self.query_id}, \n  inf_id={self.inf_id}, \n  inf_time={self.inf_time}, \n  data_source={self.data_source}, \n  time_window={self.time_window}, \n  model_id={self.model_id}, \n  device_id={self.device_id}, \n  instance_id={self.instance_id}, \n  response_time={self.response_time}, \n  inf_result={self.inf_result}, \n  model_version={self.model_version}, \n  explainability={self.explainability})"
    def to_string(self):
        """Convert the model to a string."""
        return str(self)
    
class Metric(BaseModel):
    metric_name: str = Field(..., description="Name of the metric")
    value: float = Field(..., description="Value of the metric")
    unit: Optional[str] = Field(None, description="Unit of the metric value")
    condition: Optional[str] = Field(None, description="Condition for the metric (e.g., confidence threshold)")

    def to_dict(self):
        """Convert the metric to a dictionary."""
        return self.dict()
    
    def __str__(self):
        """String representation of the metric."""
        return f"Metric(metric_name={self.metric_name}, value={self.value}, unit={self.unit}, condition={self.condition})"

    def __repr__(self):
        return f"Metric(metric_name={self.metric_name!r}, value={self.value!r}, unit={self.unit!r}, condition={self.condition!r})"


class ClassSpecificMetric(BaseModel):
    class_name: str = Field(..., description="Name of the class-specific metric")
    performance: list[Metric] = Field(..., description="Class-specific performance metrics")
    def to_dict(self):
        """Convert the class-specific metric to a dictionary."""
        return self.dict()
    def __str__(self):
        """String representation of the class-specific metric."""
        return f"ClassSpecificMetric(class_name={self.class_name}, performance={self.performance})"
    
    @classmethod
    def from_dict(cls: Type['ClassSpecificMetric'], data: Dict[str, Any]) -> 'ClassSpecificMetric':
        """Create a ClassSpecificMetric instance from a dictionary."""
        if 'performance' in data and isinstance(data['performance'], list):
            try:
                data['performance'] = [Metric(**item) for item in data['performance']]
            except Exception as e:
                raise ValueError(f"Invalid performance data: {e}")
        return cls.model_validate(data)

class RuntimePerformance(BaseModel):
    overall_performance: Optional[list[Metric]] = Field(..., description="Overall performance metrics")
    class_specific_performance: Optional[list[ClassSpecificMetric]] = Field(..., description="Class-specific performance metrics")
    def to_dict(self):
        """Convert the runtime performance to a dictionary."""
        return self.dict()
    def __str__(self):
        """String representation of the runtime performance."""
        return f"RuntimePerformance(\n overall_performance={self.overall_performance}, \n class_specific_performance={self.class_specific_performance})"
    @classmethod
    def from_dict(cls: Type['RuntimePerformance'], data: Dict[str, Any]) -> 'RuntimePerformance':
        """Create a RuntimePerformance instance from a dictionary."""
        if 'overall_performance' in data and isinstance(data['overall_performance'], list):
            try:
                data['overall_performance'] = [Metric(**item) for item in data['overall_performance']]
            except Exception as e:
                raise ValueError(f"Invalid overall performance data: {e}")
        if 'class_specific_performance' in data and isinstance(data['class_specific_performance'], list):
            try:
                data['class_specific_performance'] = [ClassSpecificMetric.from_dict(item) for item in data['class_specific_performance']]
            except Exception as e:
                raise ValueError(f"Invalid class-specific performance data: {e}")
        return cls.model_validate(data)

class InferenceServiceProfile(BaseModel):
    metadata: Optional[dict] = Field(None, description="Metadata for the inference service profile")
    inference_service_id: str = Field(..., description="Unique identifier for the inference service")
    model_id: str = Field(..., description="Model ID used in the inference service")
    model_version: Optional[str] = Field(None, description="Version of the model used in the inference service")
    device_type: str = Field(..., description="Type of device used for the inference service")
    base_line: list[Metric] = Field(..., description="Baseline performance metrics for the inference service")
    inference_performance: Optional[RuntimePerformance] = Field(None, description="Runtime performance metrics for the inference service")
    instance_list: list[str] = Field(..., description="List of instance_id for the inference service")
    specialized_class: Optional[list[str]] = Field(None, description="List of specialized classes for the inference service")
    modality: Optional[str] = Field(None, description="Modality of the inference service (e.g., 'image', 'text')")
    
    def to_dict(self):
        """Convert the inference service profile to a dictionary."""
        return self.dict()
    def __str__(self):
        """String representation of the inference service profile."""
        return f"InferenceServiceProfile(\n  inference_service_id={self.inference_service_id}, \n  model_id={self.model_id}, \n  model_version={self.model_version}, \n  device_type={self.device_type}, \n  base_line={self.base_line}, \n  inference_performance={self.inference_performance}, \n  instance_list={self.instance_list}, \n  specialized_class={self.specialized_class}, \n  modality={self.modality})"
    def to_string(self):
        """Convert the inference service profile to a string."""
        return str(self)
    @classmethod
    def from_dict(cls: Type['InferenceServiceProfile'], data: Dict[str, Any]) -> 'InferenceServiceProfile':
        """Create an InferenceServiceProfile instance from a dictionary."""
        if 'base_line' in data and isinstance(data['base_line'], list):
            try:
                data['base_line'] = [Metric(**item) for item in data['base_line']]
            except Exception as e:
                raise ValueError(f"Invalid base line data: {e}")
        if 'inference_performance' in data and isinstance(data['inference_performance'], dict):
            try:
                data['inference_performance'] = RuntimePerformance.from_dict(data['inference_performance'])
            except Exception as e:
                raise ValueError(f"Invalid inference performance data: {e}")
        return cls.model_validate(data)
    
class InferenceServiceInstance(BaseModel):
    instance_id: str = Field(..., description="Unique identifier for the inference service instance")
    model_id: Optional[str] = Field(..., description="Model ID used in the inference service instance")
    model_version: Optional[str] = Field(None, description="Version of the model used in the inference service instance")
    device_id: str = Field(..., description="Device ID where the inference service instance is running")
    ip_address: str = Field(..., description="IP address of the device running the inference service instance")
    port: int = Field(..., description="Port number for the inference service instance")
    runtime_performance: list[Metric] = Field(..., description="Runtime performance metrics for the inference service instance")
    modality: Optional[str] = Field(None, description="Modality of the inference service instance (e.g., 'image', 'text')")
    device_type: Optional[str] = Field(None, description="Type of device used for the inference service instance")
    inference_service_id: Optional[str] = Field(None, description="Inference service ID associated with the instance")
    status: Optional[str] = Field(None, description="Status of the inference service instance (e.g., 'active', 'inactive', 'error', 'contention')")
    inference_url: Optional[str] = Field(None, description="URL for the inference service instance")
    
    def to_dict(self):
        """Convert the inference service instance to a dictionary."""
        return self.dict()
    
    def __str__(self):
        """String representation of the inference service instance."""
        return f"InferenceServiceInstance(\n  instance_id={self.instance_id}, \n  model_id={self.model_id}, \n  model_version={self.model_version}, \n  device_id={self.device_id}, \n  ip_address={self.ip_address}, \n  port={self.port}, \n  runtime_performance={self.runtime_performance}, \n  modality={self.modality}, \n  device_type={self.device_type}, \n  inference_service_id={self.inference_service_id}, \n  status={self.status}, \n  inference_url={self.inference_url})"

    @classmethod
    def from_dict(cls: Type['InferenceServiceInstance'], data: Dict[str, Any]) -> 'InferenceServiceInstance':
        """Create an InferenceServiceInstance instance from a dictionary."""
        if 'runtime_performance' in data and isinstance(data['runtime_performance'], list):
            try:
                data['runtime_performance'] = [Metric(**item) for item in data['runtime_performance']]
            except Exception as e:
                raise ValueError(f"Invalid runtime performance data: {e}")
        return cls.model_validate(data)
    
class ServiceLevelIndicator(BaseModel):
    metric_name: str = Field(..., description="Name of the service level indicator")
    target_value: Optional[Union[float, list[float]]] = Field(None, description="Target value(s) for the service level indicator")
    operator: Optional[str] = Field(None, description="Operator for the service level indicator (e.g., '>', '<', '==')")
    objective_type: Optional[str] = Field(None, description="Type of the objective (e.g., 'minimize', 'maximize')")
    condition: Optional[str] = Field(None, description="Condition for the objective (e.g., 'confidence threshold')")
    class_id: Optional[str] = Field(None, description="Class id for the objective (if applicable)")
    def to_dict(self):
        """Convert the objective to a dictionary."""
        return self.dict()
    def __str__(self):
        """String representation of the service level indicator."""
        return f"ServiceLevelIndicator(metric_name={self.metric_name}, target_value={self.target_value}, operator={self.operator}, objective_type={self.objective_type}, condition={self.condition}, class_id={self.class_id})"
    def to_string(self):
        """Convert the service level indicator to a string."""
        return str(self)

class ServiceLevelAgreement(BaseModel):
    sla_id: str = Field(..., description="Unique identifier for the SLA")
    tenant_id: str = Field(..., description="Tenant ID associated with the SLA")
    access_privileges: List[str] = Field(..., description="List of data sources the tenant has access to")
    service_level_indicators: list[ServiceLevelIndicator] = Field(..., description="List of service level indicators for the SLA")
    consumer_list: Optional[List[str]] = Field(None, description="List of consumers associated with the SLA")
    ensemble_size: Optional[int] = Field(1, description="Ensemble size for the inferences")
    ensemble_selection_strategy: Optional[str] = Field("enhance_confidence", description="Ensemble selection strategy for the tenant")
    def to_dict(self):
        """Convert the SLA to a dictionary."""
        return self.dict()
    def __str__(self):
        """String representation of the SLA."""
        return f"ServiceLevelAgreement(\n  sla_id={self.sla_id}, \n  tenant_id={self.tenant_id}, \n  access_privileges={self.access_privileges}, \n  performance_indicators={self.performance_indicators}, \n  consumer_list={self.consumer_list}, \n  ensemble_size={self.ensemble_size}, \n  ensemble_selection_strategy={self.ensemble_selection_strategy})"
    def to_string(self):
        """Convert the SLA to a string."""
        return str(self)
    
    @classmethod
    def from_dict(cls: Type['ServiceLevelAgreement'], data: Dict[str, Any]) -> 'ServiceLevelAgreement':
        """Create a ServiceLevelAgreement instance from a dictionary."""
        if 'service_level_indicators' in data and isinstance(data['service_level_indicators'], list):
            try:
                data['service_level_indicators'] = [ServiceLevelIndicator(**item) for item in data['service_level_indicators']]
            except Exception as e:
                raise ValueError(f"Invalid service level indicators data: {e}")
        return cls.model_validate(data)
    
class MonitoringClient(BaseModel):
    monitoring_url: str = Field(..., description="URL for the monitoring service")
    metric_table: str = Field(..., description="The metric table name")

    def to_dict(self):
        """Convert the monitoring client to a dictionary."""
        return self.dict()
    def __str__(self):
        """String representation of the monitoring client."""
        return f"MonitoringClient(monitoring_url={self.monitoring_url}, metric_table={self.metric_table})"
    def send_report(self, report: MonitoringReport):
        try:
            connection = duckdb.connect(self.monitoring_url)
            # create the table if it does not exist
            connection.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.metric_table} (
                query_id TEXT,
                inf_id TEXT,
                instance_id TEXT,
                inf_time FLOAT,
                time_window INT,
                model_id TEXT,
                device_id TEXT,
                model_version TEXT,
                response_time FLOAT,
                data_source TEXT,
                explainability TEXT,
                data TEXT
            );
            """)
            # insert the report into the table
            connection.execute(f"""
            INSERT INTO {self.metric_table} (query_id, inf_id, instance_id, inf_time, time_window, model_id, device_id, model_version, response_time, data_source, explainability, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (report.query_id, report.inf_id, report.instance_id, report.inf_time, report.time_window, report.model_id, report.device_id, report.model_version, report.response_time, report.data_source, str(report.explainability), str(report.inf_result)))
            connection.commit()
            connection.close()
            logging.info(f"Monitoring report sent successfully for query_id: {report.query_id}")
            return True
        except Exception as e:
            logging.error(f"Failed to connect to monitoring database: {e}")
            return False

class InferenceTask(BaseModel):
    task_id: str = Field(..., description="Unique identifier for the task - inf_id")
    modality: Optional[str] = Field(None, description="Modality of the task (e.g., 'image', 'text')")
    allocated_time: Optional[float] = Field(None, description="Allocated time for the task in seconds")
    min_execution_time: Optional[float] = Field(None, description="Minimum execution time for the task in seconds")
    max_execution_time: Optional[float] = Field(None, description="Maximum execution time for the task in seconds")
    min_execution_time_ex: Optional[float] = Field(None, description="Minimum execution time for the task in seconds")
    max_execution_time_ex: Optional[float] = Field(None, description="Maximum execution time for the task in seconds")
    inference_services: Optional[dict] = Field({}, description="Inference services associated with the task")
    inference_instances: Optional[dict] = Field({}, description="Inference instances associated with the task")
    inference_services_ex: Optional[dict] = Field({}, description="Inference services associated with the task for explainability")
    inference_instances_ex: Optional[dict] = Field({}, description="Inference instances associated with the task for explainability")
    status: Optional[str] = Field(None, description="Status of the task (e.g., 'pending', 'running', 'completed', 'error')")
    phase: Optional[int] = Field(0, description="Phase of the task")
    inference_query: Optional[InferenceQuery] = Field(None, description="Inference query associated with the task")
    selected_instances: Optional[List[InferenceServiceInstance]] = Field([], description="List of selected inference service instances for the task")
    selected_instances_ex: Optional[List[InferenceServiceInstance]] = Field([], description="List of selected inference service instances for the task in explainability mode")
    ensemble_size: Optional[int] = Field(1, description="Ensemble size for the task")
    ensemble_selection_strategy: Optional[str] = Field("enhance_confidence", description="Ensemble selection strategy for the task")
    test_mode: Optional[bool] = Field(True, description="Whether the task is in test mode")
    monitoring_client: Optional[MonitoringClient] = Field(None, description="Monitoring client for the task")
    explainability: Optional[bool] = Field(False, description="Whether to include explainability in the task")
    
    def to_dict(self):
        """Convert the task info to a dictionary."""
        return self.dict()
    
    def __str__(self):
        """String representation of the task info."""
        return f"InferenceTask(\n  task_id={self.task_id}, \n  modality={self.modality}, \n  allocated_time={self.allocated_time}, \n  min_execution_time={self.min_execution_time}, \n  max_execution_time={self.max_execution_time}, \n  inference_services={len(self.inference_services) if self.inference_services else 0}, \n  inference_instances={len(self.inference_instances) if self.inference_instances else 0}, \n  status={self.status}, \n  phase={self.phase}, \n  inference_query={self.inference_query}, \n  selected_instances={len(self.selected_instances) if self.selected_instances else 0}, \n  ensemble_size={self.ensemble_size}, \n  ensemble_selection_strategy={self.ensemble_selection_strategy}, \n  test_mode={self.test_mode}, \n  monitoring_client={self.monitoring_client}, \n  explainability={self.explainability})"
    
    def execute(self):
        try:
            if self.explainability:
                self.ensemble_size += 1
            inf_lock = Lock()
            self.status = TaskStatus.RUNNING.value
            request_dict = {
                'inf_id': self.task_id,
                'ensemble_size': self.ensemble_size,
                'explainability': self.explainability,
            }
            aggregated_inference_results = InferenceResult()
            with ThreadPoolExecutor(max_workers=self.ensemble_size) as executor:
                futures = []
                if self.explainability:
                    for instance_ex_i in self.selected_instances_ex:
                        inference_url = instance_ex_i.inference_url if instance_ex_i.inference_url else DEFAULT_INFERENCE_URL
                        request_dict['instance_id'] = instance_ex_i.instance_id
                        request_dict['model_id'] = instance_ex_i.model_id
                        request_dict['device_id'] = instance_ex_i.device_id
                        request_dict['model_version'] = instance_ex_i.model_version
                        futures.append(executor.submit(requests.post, inference_url, json=request_dict))
                for instance_i in self.selected_instances:
                    inference_url = instance_i.inference_url if instance_i.inference_url else DEFAULT_INFERENCE_URL
                    request_dict['instance_id'] = instance_i.instance_id
                    request_dict['model_id'] = instance_i.model_id
                    request_dict['device_id'] = instance_i.device_id
                    request_dict['model_version'] = instance_i.model_version
                    futures.append(executor.submit(requests.post, inference_url, json=request_dict))

                for future in as_completed(futures):
                    try:
                        response = future.result()
                        if response.status_code == 200:
                            dict_response = response.json()
                            inference_result = dict_response.get('inference_result', {})
                            response_id = dict_response.get('response_id', str(uuid.uuid4()))
                            inf_result_i = InferenceResult(
                                query_id = self.inference_query.query_id,
                                task_id = [self.task_id],
                                inf_id = [response_id],
                                data = inference_result,
                                inference_time = time.perf_counter()
                            )
                            with inf_lock:
                                aggregated_inference_results.aggregate(inf_result_i)
                                
                            response_explainability = dict_response.get('explainability', False)
                            logging.debug(f"Executed inference for task {self.task_id} with {inference_result}")
                            if isinstance(self.monitoring_client, MonitoringClient):
                                metadata = dict_response.get('metadata', {})
                                monitoring_report_dict = {
                                    'query_id': self.inference_query.query_id,
                                    'inf_id': self.task_id,
                                    'instance_id': metadata['instance_id'],
                                    'inf_time': time.perf_counter(),
                                    'time_window': self.inference_query.time_window,
                                    'model_id': metadata['model_id'],
                                    'model_version': metadata['model_version'],
                                    'device_id': metadata['device_id'],
                                    'response_time': dict_response.get('response_time', 0.0),
                                    'data_source': self.modality,
                                    'inf_result': inference_result,
                                    'explainability': response_explainability
                                }
                                monitoring_report = MonitoringReport.model_validate(monitoring_report_dict)
                                self.monitoring_client.send_report(monitoring_report)
                        else:
                            logging.error(f"Failed to execute inference for task {self.task_id} on instance {instance_i.instance_id}: {response.status_code} - {response.text}")
                    except Exception as e:
                        logging.error(f"Error occurred while executing inference for task {self.task_id} on instance {instance_i.instance_id}: {e}")
                        logging.error(traceback.format_exc())
            
            logging.debug(f"Aggregated inference result for task {self.task_id}: {aggregated_inference_results}")
            self.status = TaskStatus.COMPLETED.value
            return aggregated_inference_results
        except Exception as e:
            logging.error(f"Error in executing task {self.task_id}: {e}")
            logging.error(traceback.format_exc())
            self.status = TaskStatus.ERROR.value
            return None
        

class TaskList(BaseModel):
    data: Optional[List[InferenceTask]] = Field([], description="List of task information")

    def get_task_info(self, task_id: str) -> Optional[InferenceTask]:
        """Get task information by task ID."""
        for task in self.data:
            if task.task_id == task_id:
                return task
        return None
    def add_task(self, inf_task: InferenceTask):
        """Add task information to the task list."""
        if not isinstance(inf_task, InferenceTask):
            raise ValueError("task_info must be an instance of InferenceTask")
        if self.get_task_info(inf_task.task_id) is not None:
            raise ValueError(f"Task with ID {inf_task.task_id} already exists in the task list")
        self.data.append(inf_task)
    
    def get_list_modality(self) -> List[str]:
        """Get a list of modalities from the task list."""
        return [task.modality for task in self.data if task.modality is not None]
    
    def to_dict(self):
        """Convert the task list to a dictionary."""
        return self.dict()
    
    def __str__(self):
        """String representation of the task manager."""
        return f"TaskList(data={self.data})"

class InferenceResult(BaseModel):
    inference_time: Optional[float] = Field(0.0, description="Inference time in seconds")
    data: dict = Field({}, description="Inference result data")
    query_id: Optional[Union[List[str],str]] = Field(None, description="List of query IDs associated with the inference result")
    task_id: Optional[List[str]] = Field([], description="List of task IDs associated with the inference result")
    inf_id: Optional[List[str]] = Field([], description="List of inference IDs associated with the inference result")
    metadata: Optional[dict] = Field({}, description="Metadata associated with the inference result")

    def to_dict(self):
        """Convert the inference result to a dictionary."""
        result_dict = {}
        result_dict['inference_time'] = self.inference_time
        result_dict['data'] = self.data
        result_dict['query_id'] = self.query_id[0] if self.query_id else None
        result_dict['task_id'] = str(self.task_id)
        result_dict['inf_id'] = str(self.inf_id)
        result_dict['metadata'] = self.metadata
        return result_dict
    def __str__(self):
        """String representation of the inference result."""
        return f"InferenceResult(inference_time={self.inference_time}, data={self.data}, query_id={self.query_id}, task_id={self.task_id}, inf_id={self.inf_id}, metadata={self.metadata})"
    def to_string(self):
        """Convert the inference result to a string."""
        return str(self)
    def get_top_k_predictions(self, top_k: int = 5) -> List[str]:
        # sort key based on value in self.data as dict of class_name: confidence
        top_k = sorted(self.data.items(), key=lambda item: item[1], reverse=True)[:top_k]
        top_k_keys = [key for key, _ in top_k]
        return top_k_keys

    def get_worst_k_predictions(self, worst_k: int = 5) -> List[str]:
        # sort key based on value in self.data as dict of class_name: confidence
        worst_k = sorted(self.data.items(), key=lambda item: item[1])[:worst_k]
        worst_k_keys = [key for key, _ in worst_k]
        return worst_k_keys

    def aggregate(self, other: 'InferenceResult', avg_flag: bool = False) -> 'InferenceResult':
        """Aggregate another InferenceResult into this one."""
        if not isinstance(other, InferenceResult):
            raise ValueError("other must be an instance of InferenceResult")
        if self.query_id is None and other.query_id is None:
            raise ValueError("query_id of both InferenceResult instances must be set for aggregation")
        if self.query_id is None:
            self.query_id = other.query_id
        if self.query_id != other.query_id:
            raise ValueError("query_id of both InferenceResult instances must match for aggregation")
        self.inference_time = time.perf_counter() 
        # concatenate query_id, task_id, and inf_id and remove duplicates
        self.task_id = list(set(self.task_id + other.task_id))
        self.inf_id = list(set(self.inf_id + other.inf_id))

        # concatenate list of class names in self.data and other.data without duplicates
        new_class_list = list(set(self.data.keys()).union(set(other.data.keys())))  
        aggregate_data = {}
        for class_name in new_class_list:
            if avg_flag:
                # average the values for each class
                aggregate_data[class_name] = (self.data.get(class_name, 0) + other.data.get(class_name, 0)) / 2
            else:
                # sum the values for each class
                aggregate_data[class_name] = (self.data.get(class_name, 0) + other.data.get(class_name, 0))
        self.data = aggregate_data
        return self
    
    def get_avg_from_aggregated_sum(self):
        n_inf = len(self.inf_id)
        if n_inf == 0:
            return
        self.data = {class_name: value / n_inf for class_name, value in self.data.items()}
    def sort_inference_result(self):
        """Sort the inference result data by confidence in descending order."""
        self.data = dict(sorted(self.data.items(), key=lambda item: item[1], reverse=True))

class InferenceFeedback(BaseModel):
    query_id: str = Field(..., description="Unique identifier for the query")
    ground_truth: str = Field(..., description="Ground truth label for the inference")
    
    def to_dict(self):
        """Convert the inference feedback to a dictionary."""
        return self.dict()
    def __str__(self):
        """String representation of the inference feedback."""
        return f"InferenceFeedback(query_id={self.query_id}, ground_truth={self.ground_truth})"
    def to_string(self):
        """Convert the inference feedback to a string."""
        return str(self)

class InferenceServiceSelectionMethod(ABC):
    @abstractmethod
    def select_inference_services(
        self,
        inference_services: List[InferenceServiceProfile],
        intermediate_result: InferenceResult,
        k: int
    ) -> List[InferenceServiceProfile]:
        """
        Abstract method to select k inference services.
        Parameters:
            inference_services (List[InferenceServiceProfile]): List of available inference services.
            intermediate_result (InferenceResult): Intermediate result used for decision-making.
            k (int): Number of services to select.
        Returns:
            List[InferenceServiceProfile]: List of selected inference services.
        """
        pass