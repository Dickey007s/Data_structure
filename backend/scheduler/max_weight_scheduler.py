"""Max-weight-first scheduling strategy with capacity-aware selection."""

from typing import List, Optional
from backend.models.task import Task
from backend.models.vehicle import Vehicle, VehicleStatus
from backend.models.transport_map import TransportMap
from backend.scheduler.base_scheduler import BaseScheduler


class MaxWeightScheduler(BaseScheduler):
    """Prioritize heavy tasks, selecting vehicle with best capacity-distance ratio."""

    def assign_task(
        self,
        task: Task,
        fleet: List[Vehicle],
        map_obj: TransportMap,
    ) -> Optional[Vehicle]:
        """Assign heavy tasks to vehicles with best capacity-distance balance."""
        candidates = []

        for vehicle in fleet:
            if vehicle.status not in [VehicleStatus.IDLE, VehicleStatus.MOVING]:
                continue

            dist_to_pickup = map_obj.get_distance(vehicle.current_node, task.pickup_node)
            dist_depot = map_obj.get_distance(task.pickup_node, map_obj.depot_node)
            dist_delivery = map_obj.get_distance(map_obj.depot_node, task.delivery_node)
            total_distance = dist_to_pickup + dist_depot + dist_delivery

            if not self.check_capacity(vehicle, task):
                continue
            if not self.check_battery(vehicle, task, map_obj, total_distance):
                continue

            # Composite score: heavy tasks favor vehicles with more remaining capacity
            # and sufficient battery, not just the nearest one
            remaining_capacity = vehicle.max_capacity - vehicle.current_load
            capacity_ratio = remaining_capacity / max(vehicle.max_capacity, 1)
            battery_ratio = vehicle.current_battery / max(vehicle.max_battery, 1)

            # Efficiency = task_weight * capacity_bonus * battery_bonus / distance
            # This makes heavy tasks prefer "stronger" vehicles (more capacity/battery)
            efficiency = (
                task.weight
                * (1.0 + capacity_ratio)
                * (0.8 + battery_ratio)
                / (total_distance + 1)
            )
            candidates.append((efficiency, total_distance, vehicle))

        if candidates:
            # Sort by efficiency descending; break ties by shorter distance
            candidates.sort(key=lambda x: (-x[0], x[1]))
            _, _, best_vehicle = candidates[0]
            self._assign_to_vehicle(best_vehicle, task, map_obj)
            return best_vehicle
        return None

    def _assign_to_vehicle(
        self,
        vehicle: Vehicle,
        task: Task,
        map_obj: TransportMap,
    ) -> None:
        """Append task to vehicle's route."""
        vehicle.action_plan.append({"type": "pickup", "task": task})
        vehicle.action_plan.append({"type": "move", "target": map_obj.depot_node})
        vehicle.action_plan.append({"type": "deliver", "task": task})

        # Rebuild full path from action plan
        vehicle.current_path_nodes = [vehicle.current_node]
        current = vehicle.current_node

        for action in vehicle.action_plan:
            if action["type"] == "pickup":
                target = action["task"].pickup_node
            elif action["type"] == "deliver":
                target = action["task"].delivery_node
            elif action["type"] == "move":
                target = action["target"]
            else:
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
            vehicle.status = VehicleStatus.MOVING

        task.status = Task.STATUS_ASSIGNED
        task.assigned_vehicle = vehicle.id

    def replan(self, fleet: List[Vehicle], active_tasks: List[Task], map_obj: TransportMap) -> None:
        """Greedy strategy does not support replanning."""
        pass
