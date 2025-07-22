import os
import sys
import logging
import time
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
parent_dir = os.path.abspath(os.path.join(os.getcwd(), '..'))
sys.path.append(parent_dir)

from rohe.orchestration.multimodal_abstration  import TaskList

def assigning_phase_with_longest_sequence(task_list: TaskList, time_constraint: float):
    try:
        sorted_tasks = sorted(task_list.data, key=lambda x: x.allocated_time)
        first_task = sorted_tasks[0]
        first_task.phase = 0
        phase_execution_time = [first_task.allocated_time]

        for task in sorted_tasks[1:]:
            task.phase = 0
            for j in range(len(phase_execution_time), 0, -1):
                if task.allocated_time + phase_execution_time[j-1] <= time_constraint:
                    task.phase = j
                    if j == len(phase_execution_time):
                        phase_execution_time.append(task.allocated_time + phase_execution_time[j-1])
                    break
        task_list.data = sorted_tasks
        return task_list
    except Exception as e:
        logging.error(f"Error in assigning phase with longest sequence: {e}")
        return task_list