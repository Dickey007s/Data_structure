"""Insertion heuristic scheduling strategy."""

from typing import List, Optional, Tuple
from backend.models.task import Task
from backend.models.vehicle import Vehicle, VehicleStatus
from backend.models.transport_map import TransportMap
from backend.scheduler.base_scheduler import BaseScheduler


class InsertionScheduler(BaseScheduler):
    """Insert new task into the best position of existing routes."""

    def assign_task(
        self,
        task: Task,
        fleet: List[Vehicle],
        map_obj: TransportMap,
    ) -> Optional[Vehicle]:
        """Find best insertion position across all vehicles."""
        best_cost = float("inf")
        best_vehicle = None
        best_insertion = None  # (pickup_idx, delivery_idx)

        for vehicle in fleet:
            if vehicle.status not in [VehicleStatus.IDLE, VehicleStatus.MOVING]:
                continue

            # Vehicle with no route: direct assignment
            if not vehicle.action_plan:
                cost = self._calculate_direct_cost(vehicle, task, map_obj)
                if cost is not None and cost < best_cost:
                    best_cost = cost
                    best_vehicle = vehicle
                    best_insertion = (0, 1)
                continue

            # Try all possible insertion positions
            n = len(vehicle.action_plan)
            for p_idx in range(n + 1):
                for d_idx in range(p_idx, n + 2):
                    cost = self._calculate_insertion_cost(
                        vehicle, task, p_idx, d_idx, map_obj
                    )
                    if cost is not None and cost < best_cost:
                        best_cost = cost
                        best_vehicle = vehicle
                        best_insertion = (p_idx, d_idx)

        if best_vehicle and best_insertion:
            self._apply_insertion(best_vehicle, task, best_insertion, map_obj)
            return best_vehicle
        return None

    def _calculate_direct_cost(
        self,
        vehicle: Vehicle,
        task: Task,
        map_obj: TransportMap,
    ) -> Optional[float]:
        """Calculate cost for direct assignment to empty vehicle."""
        if not self.check_capacity(vehicle, task):
            return None

        dist = (
            map_obj.get_distance(vehicle.current_node, task.pickup_node)
            + map_obj.get_distance(task.pickup_node, map_obj.depot_node)
            + map_obj.get_distance(map_obj.depot_node, task.delivery_node)
        )

        if not self.check_battery(vehicle, task, map_obj, dist):
            return None

        return dist

    def _calculate_insertion_cost(
        self,
        vehicle: Vehicle,
        task: Task,
        p_idx: int,
        d_idx: int,
        map_obj: TransportMap,
    ) -> Optional[float]:
        """Calculate marginal cost of inserting task at given positions."""
        if not self.check_capacity(vehicle, task):
            return None

        # Build tentative action plan (pickup -> depot -> deliver)
        new_plan = vehicle.action_plan.copy()
        actions = self.build_task_actions(task, map_obj)
        new_plan.insert(p_idx, actions[0])
        new_plan.insert(p_idx + 1, actions[1])
        new_plan.insert(d_idx + 2, actions[2])

        # Simulate route to calculate total distance
        total_dist = 0.0
        current_node = vehicle.current_node

        for action in new_plan:
            if action["type"] == "pickup":
                target = action["task"].pickup_node
            elif action["type"] == "deliver":
                target = action["task"].delivery_node
            elif action["type"] == "move":
                target = action["target"]
            else:
                continue

            dist = map_obj.get_distance(current_node, target)
            if dist == float("inf"):
                return None
            total_dist += dist
            current_node = target

        if not self.check_battery(vehicle, task, map_obj, total_dist):
            return None

        # Marginal cost = total distance with insertion
        return total_dist

    def _apply_insertion(
        self,
        vehicle: Vehicle,
        task: Task,
        insertion: Tuple[int, int],
        map_obj: TransportMap,
    ) -> None:
        """Apply the insertion to vehicle's action plan."""
        p_idx, d_idx = insertion
        actions = self.build_task_actions(task, map_obj)
        vehicle.action_plan.insert(p_idx, actions[0])
        vehicle.action_plan.insert(p_idx + 1, actions[1])
        vehicle.action_plan.insert(d_idx + 2, actions[2])

        self.refresh_vehicle_path(vehicle, map_obj)
        task.status = Task.STATUS_ASSIGNED
        task.assigned_vehicle = vehicle.id

    def replan(self, fleet: List[Vehicle], active_tasks: List[Task], map_obj: TransportMap) -> None:
        """Periodic re-optimization (placeholder for future improvement)."""
        pass
