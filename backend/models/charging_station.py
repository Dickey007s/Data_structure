"""ChargingStation model - represents a charging facility."""

from typing import List, Tuple
from backend.models.vehicle import Vehicle, VehicleStatus


class ChargingStation:
    """A charging station with limited slots and waiting queue."""

    def __init__(
        self,
        id: int,
        node_id: int,
        total_slots: int,
        charge_rate: float,
    ):
        self.id = id
        self.node_id = node_id
        self.total_slots = total_slots
        self.occupied_slots = 0
        self.charge_rate = charge_rate
        self.waiting_queue: List[Vehicle] = []
        self.charging_vehicles: List[Tuple[Vehicle, int]] = []

    def is_available(self) -> bool:
        """Check if station has free slots."""
        return self.occupied_slots < self.total_slots

    def is_full(self) -> bool:
        """Check if all slots are occupied."""
        return self.occupied_slots >= self.total_slots

    def join_queue(self, vehicle: Vehicle) -> None:
        """Add vehicle to waiting queue."""
        if vehicle not in self.waiting_queue:
            self.waiting_queue.append(vehicle)
            vehicle.status = VehicleStatus.WAITING_CHARGE

    def start_charging(self, vehicle: Vehicle) -> bool:
        """Start charging a vehicle."""
        if self.is_available():
            self.occupied_slots += 1
            self.charging_vehicles.append((vehicle, 0))
            vehicle.status = VehicleStatus.CHARGING
            return True
        return False

    def tick(self, dt: float) -> List[Vehicle]:
        """Advance charging state, return completed vehicles."""
        completed = []

        # Charge each vehicle
        for vehicle, _ in self.charging_vehicles:
            vehicle.current_battery = min(
                vehicle.max_battery,
                vehicle.current_battery + self.charge_rate * dt,
            )

        # Remove fully charged vehicles
        still_charging = []
        for vehicle, start_time in self.charging_vehicles:
            if vehicle.current_battery >= vehicle.max_battery:
                vehicle.current_battery = vehicle.max_battery
                vehicle.status = VehicleStatus.IDLE
                completed.append(vehicle)
            else:
                still_charging.append((vehicle, start_time))

        self.charging_vehicles = still_charging
        self.occupied_slots = len(self.charging_vehicles)

        # Fill slots from queue
        while self.waiting_queue and self.is_available():
            vehicle = self.waiting_queue.pop(0)
            self.start_charging(vehicle)

        return completed

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "node": self.node_id,
            "occupied": self.occupied_slots,
            "total": self.total_slots,
            "queue": len(self.waiting_queue),
        }
