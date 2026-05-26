"""Max-weight-first scheduling strategy."""

from typing import List, Optional
from backend.models.task import Task
from backend.models.vehicle import Vehicle, VehicleStatus
from backend.models.transport_map import TransportMap
from backend.scheduler.base_scheduler import BaseScheduler


class MaxWeightScheduler(BaseScheduler):
    """Prioritize heavy tasks, selecting most efficient vehicle."""

    def assign_task(
        self,
        task: Task,
        fleet: List[Vehicle],
        map_obj: TransportMap,
    ) -> Optional[Vehicle]:
        """Assign task to vehicle with best weight/distance ratio."""
        candidates = []

        for vehicle in fleet:
            if vehicle.status not in [VehicleStatus.IDLE, VehicleStatus.MOVING]:
                continue

            dist_to_pickup = map_obj.get_distance(vehicle.current_node, task.pickup_node)
            dist_delivery = map_obj.get_distance(task.pickup_node, task.delivery_node)
            total_distance = dist_to_pickup + dist_delivery

            if not self.check_capacity(vehicle, task):
                continue
            if not self.check_battery(vehicle, task, map_obj, total_distance):
                continue

            # Efficiency = weight / distance (higher is better)
            efficiency = task.weight / (total_distance + 1)
            candidates.append((efficiency, vehicle, total_distance))

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            _, best_vehicle, _ = candidates[0]
            self._assign_to_vehicle(best_vehicle, task, map_obj)
            return best_vehicle
        return None

    def _assign_to_vehicle(
        self,
        vehicle: Vehicle,
        task: Task,
        map_obj: TransportMap,
    ) -> None:
        """Append task to vehicle's route (same as nearest-first)."""
        path_to_pickup = map_obj.get_path(vehicle.current_node, task.pickup_node)
        path_to_delivery = map_obj.get_path(task.pickup_node, task.delivery_node)

        if path_to_pickup and path_to_delivery:
            vehicle.current_path_nodes = path_to_pickup[:-1] + path_to_delivery
        elif path_to_pickup:
            vehicle.current_path_nodes = path_to_pickup
        else:
            vehicle.current_path_nodes = [vehicle.current_node]

        vehicle.current_path_index = 0
        vehicle.status = VehicleStatus.MOVING
        vehicle.add_task(task)
        task.status = Task.STATUS_ASSIGNED
        task.assigned_vehicle = vehicle.id

        vehicle.action_plan = [
            {"type": "pickup", "task": task},
            {"type": "deliver", "task": task},
        ]

    def replan(self, fleet: List[Vehicle], active_tasks: List[Task], map_obj: TransportMap) -> None:
        """Greedy strategy does not support replanning."""
        pass
