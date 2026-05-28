"""Vehicle model - represents an electric delivery vehicle."""

from enum import Enum
from typing import List, Tuple, Optional


class VehicleStatus(Enum):
    """Vehicle status enumeration."""

    IDLE = "idle"
    MOVING = "moving"
    CHARGING = "charging"
    LOADING = "loading"
    UNLOADING = "unloading"
    WAITING_CHARGE = "waiting_charge"


class Vehicle:
    """An electric vehicle with battery, capacity and action plan."""

    def __init__(
        self,
        id: int,
        start_node: int,
        max_battery: float,
        max_capacity: float,
        consumption_empty: float,
        consumption_full: float,
    ):
        self.id = id
        self.start_node = start_node
        self.current_node = start_node
        self.max_battery = max_battery
        self.current_battery = max_battery
        self.max_capacity = max_capacity
        self.current_load = 0.0
        self.consumption_empty = consumption_empty
        self.consumption_full = consumption_full
        self.status = VehicleStatus.IDLE
        self.action_plan: List[dict] = []
        self.carrying_tasks: List = []
        self.current_path_nodes: List[int] = []
        self.current_path_index = 0
        self.position: Tuple[float, float] = (0.0, 0.0)
        self.target_position: Tuple[float, float] = (0.0, 0.0)
        self.progress = 0.0

    def get_consumption_rate(self) -> float:
        """Calculate consumption rate based on current load."""
        if self.max_capacity <= 0:
            return self.consumption_empty
        load_ratio = self.current_load / self.max_capacity
        return (
            self.consumption_empty
            + (self.consumption_full - self.consumption_empty) * load_ratio
        )

    def move(self, distance: float) -> None:
        """Move by distance and deduct battery."""
        consumption = self.get_consumption_rate() * distance
        self.current_battery = max(0.0, self.current_battery - consumption)

    def can_carry(self, weight: float) -> bool:
        """Check if vehicle can carry additional weight."""
        return self.current_load + weight <= self.max_capacity

    def add_task(self, task) -> bool:
        """Add task to carrying list."""
        if self.can_carry(task.weight):
            self.carrying_tasks.append(task)
            self.current_load += task.weight
            return True
        return False

    def remove_task(self, task) -> None:
        """Remove completed task and reduce load."""
        if task in self.carrying_tasks:
            self.carrying_tasks.remove(task)
            self.current_load -= task.weight
            self.current_load = max(0.0, self.current_load)

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON transmission."""
        # Infer next target node for preview line rendering
        next_target = None
        route_target = None
        if self.action_plan:
            action = self.action_plan[0]
            action_type = action.get("type")
            if action_type == "pickup":
                route_target = action["task"].pickup_node
            elif action_type == "deliver":
                route_target = action["task"].delivery_node
            elif action_type in ("move", "depot_return"):
                route_target = action["target"]
            elif action_type == "charge":
                route_target = self.current_node

        if self.current_path_nodes:
            next_target = self.current_path_nodes[-1]
        elif route_target is not None:
            next_target = route_target

        return {
            "id": self.id,
            "node": self.current_node,
            "position": self.position,
            "battery": round(self.current_battery, 2),
            "battery_pct": round(self.current_battery / self.max_battery, 3)
            if self.max_battery > 0
            else 0,
            "load": round(self.current_load, 2),
            "load_pct": round(self.current_load / self.max_capacity, 3)
            if self.max_capacity > 0
            else 0,
            "status": self.status.value,
            "path": self.current_path_nodes,
            "path_index": self.current_path_index,
            "route_target": route_target,
            "next_target": next_target,
            "carrying": [t.id for t in self.carrying_tasks],
        }
