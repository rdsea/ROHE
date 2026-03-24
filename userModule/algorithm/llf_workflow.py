from __future__ import annotations

import logging

from rohe.orchestration.multimodal_abstration import InferenceTask, TaskList


def compute_laxity(task: InferenceTask, remaining_time: float) -> float:
    return remaining_time - task.allocated_time


def assigning_phase_with_laxity(task_list: TaskList, remaining_time: float):
    try:
        for task in task_list.data:
            task.phase = 0
        task_list.data = sorted(
            task_list.data, key=lambda t: compute_laxity(t, remaining_time)
        )
        return task_list
    except Exception as e:
        logging.error(f"Error in assigning phase with laxity: {e}")
        return task_list
