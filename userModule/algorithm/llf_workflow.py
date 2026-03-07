import os
import sys
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
parent_dir = os.path.abspath(os.path.join(os.getcwd(), '..'))
sys.path.append(parent_dir)

from rohe.orchestration.multimodal_abstration import TaskList, InferenceTask


def compute_laxity(task: InferenceTask, remaining_time: float) -> float:
    return remaining_time - task.allocated_time


def assigning_phase_with_laxity(task_list: TaskList, remaining_time: float):
    try:
        for task in task_list.data:
            task.phase = 0
        task_list.data = sorted(task_list.data, key=lambda t: compute_laxity(t, remaining_time))
        return task_list
    except Exception as e:
        logging.error(f"Error in assigning phase with laxity: {e}")
        return task_list
