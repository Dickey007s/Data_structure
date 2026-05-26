"""Task model - represents a delivery order."""

from typing import Optional


class Task:
    """A delivery task with pickup, delivery, weight and time window."""

    STATUS_PENDING = "pending"
    STATUS_ASSIGNED = "assigned"
    STATUS_PICKING = "picking"
    STATUS_DELIVERING = "delivering"
    STATUS_COMPLETED = "completed"
    STATUS_TIMEOUT = "timeout"

    def __init__(
        self,
        id: int,
        pickup_node: int,
        delivery_node: int,
        weight: float,
        ready_time: int,
        due_time: int,
        create_time: int,
    ):
        self.id = id
        self.pickup_node = pickup_node
        self.delivery_node = delivery_node
        self.weight = weight
        self.ready_time = ready_time
        self.due_time = due_time
        self.create_time = create_time
        self.status = self.STATUS_PENDING
        self.assigned_vehicle: Optional[int] = None
        self.completed_time: Optional[int] = None

    def is_timeout(self, current_time: int) -> bool:
        """Check if task has exceeded its due time without completion."""
        return (
            current_time > self.due_time
            and self.status != self.STATUS_COMPLETED
        )

    def get_score(self) -> float:
        """Calculate task completion score."""
        if self.status == self.STATUS_COMPLETED and self.completed_time is not None:
            time_bonus = max(0, self.due_time - self.completed_time)
            return 100.0 + time_bonus
        elif self.status == self.STATUS_TIMEOUT:
            return -50.0
        return 0.0

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON transmission."""
        return {
            "id": self.id,
            "pickup": self.pickup_node,
            "delivery": self.delivery_node,
            "weight": round(self.weight, 2),
            "status": self.status,
            "ready_time": self.ready_time,
            "due_time": self.due_time,
            "assigned_vehicle": self.assigned_vehicle,
        }
