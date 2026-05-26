"""Collect performance metrics from a completed simulation run."""

from typing import Dict, List

from backend.simulator.simulator import Simulator


def collect_metrics(simulator: Simulator) -> Dict:
    """Extract comparison metrics from a Simulator instance after completion."""
    total_tasks = simulator.config.get("task_count", 100)
    completed = simulator.completed_tasks
    failed = simulator.failed_tasks

    # Completion / failure rates
    completion_rate = len(completed) / total_tasks if total_tasks > 0 else 0
    failure_rate = len(failed) / total_tasks if total_tasks > 0 else 0

    # Distance
    total_distance = sum(simulator.total_distance_traveled)

    # Completion / wait times
    completion_times = []
    wait_times = []
    for task in completed:
        if task.completed_time is not None:
            completion_times.append(task.completed_time - task.create_time)
            wait_times.append(task.completed_time - task.ready_time)

    avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
    avg_wait_time = sum(wait_times) / len(wait_times) if wait_times else 0

    # Charging
    total_charging_time = simulator.total_charging_time
    charging_count = simulator.charging_count

    # Vehicle utilization: moving time / total simulation time
    total_sim_time = simulator.current_time
    utilizations = []
    for vt in simulator.vehicle_moving_time:
        if total_sim_time > 0:
            utilizations.append(vt / total_sim_time)
    avg_utilization = sum(utilizations) / len(utilizations) if utilizations else 0

    # Score
    score = simulator._calculate_score()

    return {
        "strategy": simulator.scheduler_type if hasattr(simulator, "scheduler_type") else "unknown",
        "completion_rate": round(completion_rate, 4),
        "failure_rate": round(failure_rate, 4),
        "completed_count": len(completed),
        "failed_count": len(failed),
        "total_tasks": total_tasks,
        "total_distance": round(total_distance, 2),
        "avg_completion_time": round(avg_completion_time, 2),
        "avg_wait_time": round(avg_wait_time, 2),
        "total_charging_time": round(total_charging_time, 2),
        "charging_count": charging_count,
        "avg_utilization": round(avg_utilization, 4),
        "score": round(score, 2),
        "simulation_time": total_sim_time,
    }
