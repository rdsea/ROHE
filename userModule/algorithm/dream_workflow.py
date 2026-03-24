from __future__ import annotations

import logging

from rohe.orchestration.multimodal_abstration import InferenceTask, TaskList

STARVATION_WEIGHT = 0.1


def compute_urgency(task: InferenceTask, remaining_time: float) -> float:
    to_go = task.min_execution_time
    slack = remaining_time - to_go
    if slack <= 0:
        return float("inf")
    return to_go / slack


def compute_map_score(
    task: InferenceTask, remaining_time: float, starvation: float = 0.0
) -> float:
    urgency = compute_urgency(task, remaining_time)
    lat_pref = task.allocated_time / remaining_time if remaining_time > 0 else 1.0
    return urgency * lat_pref + STARVATION_WEIGHT * starvation


def should_early_drop(task: InferenceTask, remaining_time: float) -> bool:
    return task.min_execution_time > remaining_time


def assigning_phase_with_dream(task_list: TaskList, remaining_time: float):
    try:
        surviving_tasks = []
        dropped_tasks = []
        for task in task_list.data:
            if should_early_drop(task, remaining_time):
                task.status = "dropped"
                dropped_tasks.append(task)
                logging.info(
                    f"DREAM early-dropped task {task.task_id} (modality={task.modality}, min_exec={task.min_execution_time:.4f}, remaining={remaining_time:.4f})"
                )
            else:
                task.phase = 0
                surviving_tasks.append(task)
        surviving_tasks = sorted(
            surviving_tasks,
            key=lambda t: compute_map_score(t, remaining_time),
            reverse=True,
        )
        task_list.data = surviving_tasks
        return task_list
    except Exception as e:
        logging.error(f"Error in assigning phase with DREAM: {e}")
        return task_list
