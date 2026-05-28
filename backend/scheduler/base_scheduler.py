"""Base scheduler interface for task assignment strategies."""

from abc import ABC, abstractmethod
from typing import List, Optional


class BaseScheduler(ABC):
    """Abstract base class for task scheduling strategies."""

    @abstractmethod
    def assign_task(
        self,
        task,
        fleet: List,
        map_obj,
    ) -> Optional:
        """Assign task to the most suitable vehicle.

        Args:
            task: The task to assign
            fleet: List of available vehicles
            map_obj: The transport map

        Returns:
            The assigned vehicle, or None if no vehicle available
        """
        pass

    @abstractmethod
    def replan(
        self,
        fleet: List,
        active_tasks: List,
        map_obj,
    ) -> None:
        """Replan routes for all vehicles (optional periodic re-optimization)."""
        pass

    def check_capacity(self, vehicle, task) -> bool:
        """Check if vehicle can carry the task weight."""
        committed_load = vehicle.current_load
        reserved_task_ids = set()

        for action in vehicle.action_plan:
            planned_task = action.get("task")
            if planned_task is None or planned_task in vehicle.carrying_tasks:
                continue
            if planned_task.id in reserved_task_ids:
                continue

            committed_load += planned_task.weight
            reserved_task_ids.add(planned_task.id)

        return committed_load + task.weight <= vehicle.max_capacity

    def refresh_vehicle_path(self, vehicle, map_obj) -> None:
        """Rebuild a vehicle path unless it is already moving on an edge."""
        if vehicle.status.value == "moving" and vehicle.current_path_nodes:
            return

        vehicle.current_path_nodes = [vehicle.current_node]
        current = vehicle.current_node

        for action in vehicle.action_plan:
            target = self.get_action_target(action)
            if target is None:
                continue

            if target != current:
                path = map_obj.get_path(current, target)
                if path and len(path) > 1:
                    vehicle.current_path_nodes.extend(path[1:])
                else:
                    vehicle.current_path_nodes.append(target)
                current = target

        vehicle.current_path_index = 0
        if len(vehicle.current_path_nodes) > 1:
            vehicle.status = type(vehicle.status).MOVING

    def get_action_target(self, action: dict):
        """Return the target node for a route action."""
        action_type = action.get("type")
        if action_type == "pickup":
            return action["task"].pickup_node
        if action_type == "deliver":
            return action["task"].delivery_node
        if action_type in ("move", "depot_return"):
            return action["target"]
        return None

    def check_battery(
        self,
        vehicle,
        task,
        map_obj,
        planned_distance: float,
        safety_margin: float = 1.2,
    ) -> bool:
        """Check if vehicle has enough battery for planned route plus safety margin."""
        consumption = vehicle.get_consumption_rate() * planned_distance

        nearest_station = map_obj.find_nearest_station(task.delivery_node)
        if nearest_station is None:
            return vehicle.current_battery >= consumption

        dist_to_station = map_obj.get_distance(task.delivery_node, nearest_station)
        consumption_to_station = vehicle.consumption_empty * dist_to_station * safety_margin

        return vehicle.current_battery >= consumption + consumption_to_station

    def check_time_window(self, vehicle, task, arrival_time: int) -> bool:
        """Check if arrival time satisfies task time window."""
        return arrival_time <= task.due_time

