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
        return vehicle.can_carry(task.weight)

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

    def preassign_all_tasks(self, tasks, fleet, map_obj) -> None:
        """Pre-assign all tasks to fleet (used by global schedulers).

        Override in subclasses that support static pre-computation.
        """
        pass
