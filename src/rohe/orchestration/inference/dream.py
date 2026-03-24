import logging
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

from userModule.algorithm.dream_workflow import assigning_phase_with_dream

from rohe.orchestration.inference.orchestrator import AdaptiveOrchestrator
from rohe.orchestration.multimodal_abstration import (
    InferenceQuery,
    InferenceResult,
    TaskList,
    TaskStatus,
)


class DREAMOrchestrator(AdaptiveOrchestrator):
    def determine_execution_workflow(
        self,
        inference_query: InferenceQuery,
        task_list: TaskList,
        start_time: float,
        e2e_response_time: float = 5,
    ):
        try:
            remaining_time = e2e_response_time - (time.perf_counter() - start_time)
            consumer_id = inference_query.metadata.get("consumer_id", "unknown")
            task_list = self.get_time_allocation(
                consumer_id=consumer_id,
                task_list=task_list,
                remaining_time=remaining_time,
            )
            task_list = assigning_phase_with_dream(task_list, remaining_time)
            for task in task_list.data:
                logging.debug(
                    f"DREAM - Modality: {task.modality}, Services: {len(task.inference_services)}, Instances: {len(task.inference_instances)}, Min Execution Time: {task.min_execution_time}, Max Execution Time: {task.max_execution_time}, Allocated Time: {task.allocated_time}, Phase: {task.phase}, Status: {task.status}"
                )
            return task_list
        except Exception as e:
            logging.error(f"Failed to determine DREAM execution workflow: {e}")
            traceback.print_exc()
            return None

    def task_execution_loop(
        self,
        task_list: TaskList,
        inference_query: InferenceQuery,
        start_time: float,
        e2e_response_time: float,
        intermediate_result: InferenceResult,
    ):
        try:
            if not self.check_pending_tasks(task_list):
                return TaskStatus.COMPLETED.value

            remaining_time = e2e_response_time - (time.perf_counter() - start_time)
            if remaining_time <= 0:
                logging.warning(
                    f"Time violation detected for query: {inference_query.metadata.get('consumer_id', 'unknown')}"
                )
                return TaskStatus.COMPLETED.value

            step_2_start_time = time.perf_counter()
            task_list = self.determine_execution_workflow(
                inference_query=inference_query,
                task_list=task_list,
                start_time=start_time,
                e2e_response_time=e2e_response_time,
            )
            logging.info("#" * 40)
            for task in task_list.data:
                logging.info(
                    f"Task {task.task_id} - Modality: {task.modality}, Phase: {task.phase}, Allocated Time: {task.allocated_time}"
                )
            step_2_execution_time = time.perf_counter() - step_2_start_time
            logging.debug(
                f"######## Step 2 execution time: {step_2_execution_time:.4f} seconds"
            )

            step_3_start_time = time.perf_counter()
            task_list = self.distribute_inference_workload(
                task_list, intermediate_result
            )
            step_3_execution_time = time.perf_counter() - step_3_start_time
            logging.debug(
                f"######## Step 3 execution time: {step_3_execution_time:.4f} seconds"
            )

            step_4_start_time = time.perf_counter()
            phase_0_tasks = [task for task in task_list.data if task.phase == 0]
            if self.prepare_process is not None:
                self.prepare_process.join()
                self.prepare_process = None
            if phase_0_tasks:
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = {
                        executor.submit(task.execute): task for task in phase_0_tasks
                    }
                    try:
                        for future in as_completed(futures):
                            task_inf_result = future.result()
                            with self.lock:
                                intermediate_result.aggregate(task_inf_result)
                        step_4_execution_time = time.perf_counter() - step_4_start_time
                        logging.debug(
                            f"######## Step 4 execution time: {step_4_execution_time:.4f} seconds"
                        )
                    except TimeoutError:
                        logging.warning(
                            f"Task execution timed out after {self.process_timeout} seconds."
                        )
                        return TaskStatus.FAILED.value
            return TaskStatus.COMPLETED.value
        except Exception as e:
            logging.error(f"DREAM task execution loop failed: {e}")
            traceback.print_exc()
