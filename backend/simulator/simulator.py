"""Main simulation engine."""

import time
from typing import List, Dict, Optional, Callable

from backend.models.task import Task
from backend.models.vehicle import Vehicle, VehicleStatus
from backend.models.charging_station import ChargingStation
from backend.models.transport_map import TransportMap
from backend.scheduler.base_scheduler import BaseScheduler
from backend.scheduler.nearest_first_scheduler import NearestFirstScheduler
from backend.scheduler.max_weight_scheduler import MaxWeightScheduler
from backend.scheduler.insertion_scheduler import InsertionScheduler
from backend.simulator.event_generator import EventGenerator


class Simulator:
    """Discrete-event simulation engine for EV fleet scheduling."""

    def __init__(self, config: dict):
        self.current_time = 0
        self.config = config
        self.map: Optional[TransportMap] = None
        self.fleet: List[Vehicle] = []
        self.charging_stations: List[ChargingStation] = []
        self.active_tasks: List[Task] = []
        self.completed_tasks: List[Task] = []
        self.failed_tasks: List[Task] = []
        self.scheduler: Optional[BaseScheduler] = None
        self.event_generator: Optional[EventGenerator] = None
        self.running = False
        self.tick_interval = config.get("tick_interval", 1)
        self.sim_speed = config.get("sim_speed", 1.0)
        self.real_time_step = 0.1 / self.sim_speed
        self.scheduler_type = config.get("scheduler", "insertion")

        self._emit_state: Optional[Callable] = None
        self._emit_finished: Optional[Callable] = None

        # Metrics tracking
        self.total_distance_traveled: List[float] = []
        self.total_charging_time = 0.0
        self.charging_count = 0
        self.vehicle_moving_time: List[float] = []
        self._charging_start_times: Dict[int, float] = {}

        # Return-to-depot phase tracking
        self._return_phase = False
        self._all_returned = False

    def initialize(
        self,
        map_config: dict,
        fleet_config: List[dict],
        station_config: List[dict],
        scheduler_type: str,
        seed: int = 42,
    ) -> None:
        """Initialize simulation environment."""
        self.scheduler_type = scheduler_type

        # Create map
        self.map = TransportMap(map_config["width"], map_config["height"])
        self.map.generate_grid(
            map_config["num_nodes"],
            num_stations=len(station_config),
            seed=seed,
        )

        # Add charging stations (use actual station nodes from generated map)
        for i, sc in enumerate(station_config):
            node_id = self.map.station_nodes[i % len(self.map.station_nodes)]
            station = ChargingStation(
                id=sc.get("id", i),
                node_id=node_id,
                total_slots=sc.get("total_slots", 2),
                charge_rate=sc.get("charge_rate", 10.0),
            )
            self.charging_stations.append(station)

        # Create fleet - all vehicles start at depot
        for fc in fleet_config:
            vehicle = Vehicle(**fc)
            vehicle.start_node = self.map.depot_node
            vehicle.current_node = self.map.depot_node
            vehicle.position = self.map.get_node_position(self.map.depot_node)
            self.fleet.append(vehicle)

        # Initialize metrics arrays
        self.total_distance_traveled = [0.0] * len(self.fleet)
        self.vehicle_moving_time = [0.0] * len(self.fleet)

        # Set scheduler
        self.scheduler = self._create_scheduler(scheduler_type)

        # Create event generator with same seed for reproducible comparisons
        self.event_generator = EventGenerator(
            task_count=self.config.get("task_count", 100),
            time_horizon=self.config.get("time_horizon", 1000),
            map_nodes=list(self.map.nodes.keys()),
            seed=seed,
        )
        self.event_generator.generate_schedule()

    def _create_scheduler(self, scheduler_type: str) -> BaseScheduler:
        """Factory method for schedulers."""
        if scheduler_type == "nearest":
            return NearestFirstScheduler()
        elif scheduler_type == "max_weight":
            return MaxWeightScheduler()
        elif scheduler_type == "insertion":
            return InsertionScheduler()
        else:
            raise ValueError(f"Unknown scheduler type: {scheduler_type}")

    def tick(self) -> dict:
        """Advance one simulation tick and return state snapshot."""
        try:
            self.current_time += self.tick_interval

            # 1. Generate new tasks
            if self.event_generator:
                new_tasks = self.event_generator.generate(self.current_time)
                for task in new_tasks:
                    self.active_tasks.append(task)
                    if self.scheduler:
                        assigned = self.scheduler.assign_task(task, self.fleet, self.map)
                        if not assigned:
                            task.status = Task.STATUS_PENDING

            # 2. Update each vehicle
            for vehicle in self.fleet:
                self._update_vehicle(vehicle)

            # 3. Update charging stations
            for station in self.charging_stations:
                completed = station.tick(self.tick_interval)
                # Record charging completion time
                for vehicle in completed:
                    if vehicle.id in self._charging_start_times:
                        duration = self.current_time - self._charging_start_times[vehicle.id]
                        self.total_charging_time += duration
                        del self._charging_start_times[vehicle.id]

            # 4. Check timeout tasks
            for task in self.active_tasks[:]:
                if task.is_timeout(self.current_time):
                    task.status = Task.STATUS_TIMEOUT
                    self.failed_tasks.append(task)
                    self.active_tasks.remove(task)

            # 5. Handle low battery
            self._handle_low_battery()

            # 6. Check if all tasks are done and trigger return-to-depot
            self._check_return_phase()

            # 7. Handle return-to-depot for vehicles
            if self._return_phase:
                self._handle_return_to_depot()

            # 8. Calculate score
            score = self._calculate_score()

            return self._get_state_snapshot(score)
        except Exception as e:
            import traceback
            print(f"[Simulator.tick] Error at time {self.current_time}: {e}")
            traceback.print_exc()
            return self._get_state_snapshot(self._calculate_score())

    def _update_vehicle(self, vehicle: Vehicle) -> None:
        """Update a single vehicle's state."""
        if vehicle.status == VehicleStatus.MOVING:
            self._update_moving(vehicle)
        elif vehicle.status == VehicleStatus.IDLE:
            # Idle vehicle with no pending tasks -> return to depot by default
            if (
                not vehicle.action_plan
                and vehicle.current_node != self.map.depot_node
                and not self._return_phase
            ):
                vehicle.action_plan.append(
                    {"type": "depot_return", "target": self.map.depot_node}
                )
            self._execute_next_action(vehicle)

    def _update_moving(self, vehicle: Vehicle) -> None:
        """Update a moving vehicle."""
        if not vehicle.current_path_nodes:
            vehicle.status = VehicleStatus.IDLE
            return

        if vehicle.current_path_index >= len(vehicle.current_path_nodes) - 1:
            vehicle.current_node = vehicle.current_path_nodes[-1]
            vehicle.position = self.map.get_node_position(vehicle.current_node)
            vehicle.progress = 0.0
            self._on_arrive_at_node(vehicle)
            return

        current_node_id = vehicle.current_path_nodes[vehicle.current_path_index]
        next_node_id = vehicle.current_path_nodes[vehicle.current_path_index + 1]

        # Check battery: stop if depleted or cannot reach next node
        segment_distance = self.map.get_distance(current_node_id, next_node_id)
        consumption = vehicle.get_consumption_rate() * segment_distance
        if vehicle.current_battery <= 0 or vehicle.current_battery < consumption * 0.5:
            vehicle.status = VehicleStatus.IDLE
            vehicle.current_path_nodes = []
            vehicle.current_path_index = 0
            vehicle.progress = 0.0
            return

        current_pos = self.map.get_node_position(current_node_id)
        next_pos = self.map.get_node_position(next_node_id)

        speed = self.config.get("vehicle_speed", 10.0)
        if segment_distance > 0:
            vehicle.progress += (speed * self.tick_interval) / segment_distance

        if vehicle.progress >= 1.0:
            vehicle.current_path_index += 1
            vehicle.progress = 0.0
            vehicle.current_node = next_node_id
            vehicle.move(segment_distance)

            # Track distance and moving time
            if vehicle.id < len(self.total_distance_traveled):
                self.total_distance_traveled[vehicle.id] += segment_distance
                self.vehicle_moving_time[vehicle.id] += self.tick_interval

            if vehicle.current_path_index >= len(vehicle.current_path_nodes) - 1:
                self._on_arrive_at_node(vehicle)
        else:
            t = vehicle.progress
            vehicle.position = (
                current_pos[0] + (next_pos[0] - current_pos[0]) * t,
                current_pos[1] + (next_pos[1] - current_pos[1]) * t,
            )
            move_dist = speed * self.tick_interval
            vehicle.move(min(move_dist, segment_distance))

            # Track partial distance and moving time
            if vehicle.id < len(self.total_distance_traveled):
                self.total_distance_traveled[vehicle.id] += min(move_dist, segment_distance)
                self.vehicle_moving_time[vehicle.id] += self.tick_interval

    def _on_arrive_at_node(self, vehicle: Vehicle) -> None:
        """Handle vehicle arriving at destination node."""
        vehicle.status = VehicleStatus.IDLE
        vehicle.progress = 0.0
        vehicle.current_path_nodes = []
        vehicle.current_path_index = 0

        # Check if at charging station
        for station in self.charging_stations:
            if station.node_id == vehicle.current_node:
                if vehicle.action_plan and vehicle.action_plan[0].get("type") == "charge":
                    vehicle.action_plan.pop(0)
                if station.is_available():
                    station.start_charging(vehicle)
                    self._charging_start_times[vehicle.id] = self.current_time
                    self.charging_count += 1
                else:
                    station.join_queue(vehicle)
                return

        self._execute_next_action(vehicle)

    def _execute_next_action(self, vehicle: Vehicle) -> None:
        """Execute next action from action_plan."""
        if not vehicle.action_plan:
            return

        action = vehicle.action_plan.pop(0)
        action_type = action["type"]

        if action_type == "pickup":
            task = action["task"]
            # Wait if task is not yet ready
            if self.current_time < task.ready_time:
                vehicle.action_plan.insert(0, action)
                return
            # Skip if task already timed out
            if task.status == Task.STATUS_TIMEOUT:
                vehicle.status = VehicleStatus.IDLE
                return
            vehicle.status = VehicleStatus.LOADING
            task.status = Task.STATUS_PICKING
            if task not in vehicle.carrying_tasks:
                vehicle.add_task(task)
            task.status = Task.STATUS_DELIVERING
            vehicle.status = VehicleStatus.IDLE

        elif action_type == "deliver":
            task = action["task"]
            vehicle.status = VehicleStatus.UNLOADING
            vehicle.remove_task(task)
            # Only count as completed if not already timed out
            if task.status == Task.STATUS_TIMEOUT:
                vehicle.status = VehicleStatus.IDLE
                return
            task.status = Task.STATUS_COMPLETED
            task.completed_time = self.current_time
            self.completed_tasks.append(task)
            if task in self.active_tasks:
                self.active_tasks.remove(task)
            vehicle.status = VehicleStatus.IDLE

        elif action_type == "move":
            target_node = action["target"]
            vehicle.current_path_nodes = self.map.get_path(
                vehicle.current_node, target_node
            )
            vehicle.current_path_index = 0
            if len(vehicle.current_path_nodes) > 1:
                vehicle.status = VehicleStatus.MOVING

        elif action_type == "charge":
            station_id = action["station_id"]
            station = next(
                (s for s in self.charging_stations if s.id == station_id), None
            )
            if station:
                if station.is_available():
                    station.start_charging(vehicle)
                    self._charging_start_times[vehicle.id] = self.current_time
                    self.charging_count += 1
                else:
                    station.join_queue(vehicle)

        elif action_type == "depot_return":
            target_node = action["target"]
            vehicle.current_path_nodes = self.map.get_path(
                vehicle.current_node, target_node
            )
            vehicle.current_path_index = 0
            if len(vehicle.current_path_nodes) > 1:
                vehicle.status = VehicleStatus.MOVING

    def _handle_low_battery(self) -> None:
        """Plan charging for vehicles with low battery."""
        for vehicle in self.fleet:
            if vehicle.status not in [VehicleStatus.IDLE, VehicleStatus.MOVING]:
                continue

            if any(a.get("type") == "charge" for a in vehicle.action_plan):
                continue
            if any(s.node_id == vehicle.current_node for s in self.charging_stations):
                continue

            nearest_station = self.map.find_nearest_station(vehicle.current_node)
            if nearest_station is None:
                continue

            dist_to_station = self.map.get_distance(vehicle.current_node, nearest_station)
            if dist_to_station == float("inf"):
                continue

            consumption_to_station = (
                vehicle.get_consumption_rate() * dist_to_station * 2.0
            )

            battery_threshold = max(
                consumption_to_station,
                vehicle.max_battery * 0.25,
            )

            if vehicle.current_battery <= battery_threshold:
                station = next(
                    (s for s in self.charging_stations if s.node_id == nearest_station),
                    None,
                )
                if station:
                    vehicle.action_plan.insert(0, {"type": "move", "target": nearest_station})
                    vehicle.action_plan.insert(1, {"type": "charge", "station_id": station.id})
                    if vehicle.status == VehicleStatus.IDLE:
                        self._execute_next_action(vehicle)

    def _check_return_phase(self) -> None:
        """Check if all tasks are processed and enter return-to-depot phase."""
        if self._return_phase or self._all_returned:
            return

        total_tasks = self.config.get("task_count", 100)
        completed_or_failed = len(self.completed_tasks) + len(self.failed_tasks)
        all_tasks_processed = completed_or_failed >= total_tasks
        no_active = len(self.active_tasks) == 0

        if all_tasks_processed and no_active:
            self._return_phase = True

    def _handle_return_to_depot(self) -> None:
        """Command all vehicles to return to depot. Charge first if battery insufficient."""
        depot = self.map.depot_node
        all_returned = True

        for vehicle in self.fleet:
            # Skip vehicles already at depot and idle
            if vehicle.current_node == depot and vehicle.status == VehicleStatus.IDLE:
                continue

            # Skip vehicles currently charging or waiting to charge
            if vehicle.status in [VehicleStatus.CHARGING, VehicleStatus.WAITING_CHARGE]:
                all_returned = False
                continue

            # Skip vehicles already moving toward a destination (depot or station)
            if vehicle.status == VehicleStatus.MOVING and vehicle.current_path_nodes:
                all_returned = False
                continue

            # Skip vehicles already have a return-to-depot plan in queue
            if any(a.get("type") == "depot_return" for a in vehicle.action_plan):
                all_returned = False
                continue

            # Vehicle is idle but not at depot - plan return
            all_returned = False

            # Clear any remaining task-related plans
            vehicle.action_plan = []
            vehicle.current_path_nodes = []
            vehicle.current_path_index = 0
            vehicle.progress = 0.0

            # Calculate battery needed to return to depot
            dist_to_depot = self.map.get_distance(vehicle.current_node, depot)
            if dist_to_depot == float("inf"):
                dist_to_depot = 0

            consumption_to_depot = vehicle.get_consumption_rate() * dist_to_depot * 1.5

            if vehicle.current_battery >= consumption_to_depot and dist_to_depot > 0:
                # Direct return
                vehicle.action_plan = [{"type": "depot_return", "target": depot}]
                self._execute_next_action(vehicle)
            else:
                # Need to charge first
                nearest_station = self.map.find_nearest_station(vehicle.current_node)
                if nearest_station is not None:
                    station = next(
                        (s for s in self.charging_stations if s.node_id == nearest_station),
                        None,
                    )
                    if station:
                        vehicle.action_plan = [
                            {"type": "depot_return", "target": nearest_station},
                            {"type": "charge", "station_id": station.id},
                            {"type": "depot_return", "target": depot},
                        ]
                        self._execute_next_action(vehicle)

        self._all_returned = all_returned

    def _calculate_score(self) -> float:
        """Calculate total score."""
        score = 0.0
        for task in self.completed_tasks:
            score += task.get_score()
        for task in self.failed_tasks:
            score += task.get_score()
        return score

    def _get_state_snapshot(self, score: float) -> dict:
        """Get current state snapshot for frontend."""
        return {
            "time": self.current_time,
            "score": round(score, 2),
            "vehicles": [v.to_dict() for v in self.fleet],
            "tasks": [
                {
                    "id": t.id,
                    "pickup": t.pickup_node,
                    "delivery": t.delivery_node,
                    "weight": round(t.weight, 2),
                    "status": t.status,
                    "ready_time": t.ready_time,
                    "due_time": t.due_time,
                    "assigned_vehicle": t.assigned_vehicle,
                }
                for t in (self.active_tasks + self.completed_tasks + self.failed_tasks)
            ],
            "stations": [s.to_dict() for s in self.charging_stations],
            "stats": {
                "completed": len(self.completed_tasks),
                "failed": len(self.failed_tasks),
                "pending": len([t for t in self.active_tasks if t.status == Task.STATUS_PENDING]),
                "active": len([t for t in self.active_tasks if t.status != Task.STATUS_PENDING]),
                "total_tasks": (
                    len(self.completed_tasks)
                    + len(self.failed_tasks)
                    + len(self.active_tasks)
                ),
            },
        }

    def run(self) -> None:
        """Run simulation main loop."""
        self.running = True
        while self.running:
            start_time = time.time()

            state = self.tick()

            if self._emit_state:
                self._emit_state(state)

            if self._check_finished():
                self.running = False
                if self._emit_finished:
                    final_score = self._calculate_score()
                    self._emit_finished({"final_score": final_score})
                break

            elapsed = time.time() - start_time
            sleep_time = max(0, self.real_time_step - elapsed)
            time.sleep(sleep_time)

    def _check_finished(self) -> bool:
        """Check if simulation is complete (all tasks done + all vehicles returned to depot)."""
        total_tasks = self.config.get("task_count", 100)
        completed_or_failed = len(self.completed_tasks) + len(self.failed_tasks)
        all_tasks_processed = completed_or_failed >= total_tasks
        no_active = len(self.active_tasks) == 0
        if not all_tasks_processed or not no_active:
            return False
        return self._all_returned

    def pause(self) -> None:
        """Pause simulation."""
        self.running = False

    def reset(self) -> None:
        """Reset simulation state."""
        self.running = False
        self.current_time = 0
        self.fleet = []
        self.charging_stations = []
        self.active_tasks = []
        self.completed_tasks = []
        self.failed_tasks = []
        self.map = None
        self.scheduler = None
        self.event_generator = None
        self.total_distance_traveled = []
        self.total_charging_time = 0.0
        self.charging_count = 0
        self.vehicle_moving_time = []
        self._charging_start_times = {}
        self._return_phase = False
        self._all_returned = False
