import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.models.task import Task
from backend.models.vehicle import Vehicle, VehicleStatus
from backend.scheduler.nearest_first_scheduler import NearestFirstScheduler
from backend.simulator.simulator import Simulator


class SimpleMap:
    depot_node = 0
    station_nodes = []

    def __init__(self):
        self.nodes = {
            0: (0.0, 0.0, "depot"),
            1: (10.0, 0.0, "normal"),
            2: (20.0, 0.0, "normal"),
            3: (30.0, 0.0, "normal"),
        }

    def get_distance(self, start, end):
        if start == end:
            return 0.0
        return 10.0

    def get_path(self, start, end):
        if start == end:
            return [start]
        if {start, end} == {0, 1}:
            return [start, end]
        if {start, end} == {0, 2}:
            return [start, end]
        if {start, end} == {1, 3}:
            return [start, 3]
        if {start, end} == {2, 3}:
            return [start, 3]
        return [start, 0, end]

    def find_nearest_station(self, node_id):
        return None

    def get_node_position(self, node_id):
        return self.nodes[node_id][:2]


class TaskLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.sim = Simulator({
            "tick_interval": 1,
            "vehicle_speed": 10.0,
            "task_count": 1,
        })
        self.sim.map = SimpleMap()
        self.vehicle = Vehicle(
            id=0,
            start_node=0,
            max_battery=1000.0,
            max_capacity=50.0,
            consumption_empty=0.0,
            consumption_full=0.0,
        )
        self.vehicle.position = self.sim.map.get_node_position(0)
        self.task = Task(
            id=1,
            pickup_node=1,
            delivery_node=2,
            weight=10.0,
            ready_time=0,
            due_time=100,
            create_time=0,
        )
        self.sim.fleet = [self.vehicle]
        self.sim.active_tasks = [self.task]

        assigned = NearestFirstScheduler().assign_task(
            self.task,
            self.sim.fleet,
            self.sim.map,
        )
        self.assertIs(assigned, self.vehicle)

    def test_task_markers_follow_pickup_depot_delivery_lifecycle(self):
        self.assertEqual(Task.STATUS_ASSIGNED, self.task.status)
        self.assertEqual(0.0, self.vehicle.current_load)

        self.sim.tick()
        self.assertEqual(1, self.vehicle.current_node)
        self.assertEqual(Task.STATUS_PICKING, self.task.status)
        self.assertEqual(10.0, self.vehicle.current_load)

        self.sim.tick()
        self.assertEqual(0, self.vehicle.current_node)
        self.assertEqual(Task.STATUS_DELIVERING, self.task.status)
        self.assertEqual(10.0, self.vehicle.current_load)

        self.sim.tick()
        self.assertEqual(2, self.vehicle.current_node)
        self.assertEqual(Task.STATUS_COMPLETED, self.task.status)
        self.assertEqual(0.0, self.vehicle.current_load)
        self.assertNotIn(self.task, self.sim.active_tasks)

    def test_assigning_to_moving_vehicle_does_not_reset_current_edge(self):
        moving_vehicle = Vehicle(
            id=1,
            start_node=0,
            max_battery=1000.0,
            max_capacity=50.0,
            consumption_empty=0.0,
            consumption_full=0.0,
        )
        moving_vehicle.status = VehicleStatus.MOVING
        moving_vehicle.current_node = 0
        moving_vehicle.position = (5.0, 0.0)
        moving_vehicle.current_path_nodes = [0, 1, 2]
        moving_vehicle.current_path_index = 0
        moving_vehicle.action_plan = [{"type": "move", "target": 2}]
        original_path = list(moving_vehicle.current_path_nodes)

        new_task = Task(
            id=2,
            pickup_node=3,
            delivery_node=2,
            weight=10.0,
            ready_time=0,
            due_time=100,
            create_time=0,
        )

        assigned = NearestFirstScheduler().assign_task(
            new_task,
            [moving_vehicle],
            self.sim.map,
        )

        self.assertIs(assigned, moving_vehicle)
        self.assertEqual(original_path, moving_vehicle.current_path_nodes)
        self.assertEqual(0, moving_vehicle.current_path_index)
        self.assertEqual((5.0, 0.0), moving_vehicle.position)
        self.assertEqual(Task.STATUS_ASSIGNED, new_task.status)

    def test_moving_vehicle_switches_to_updated_plan_at_next_node(self):
        rerouted_task = Task(
            id=3,
            pickup_node=3,
            delivery_node=2,
            weight=10.0,
            ready_time=0,
            due_time=100,
            create_time=0,
        )
        self.vehicle.status = VehicleStatus.MOVING
        self.vehicle.current_node = 0
        self.vehicle.position = self.sim.map.get_node_position(0)
        self.vehicle.current_path_nodes = [0, 1, 2]
        self.vehicle.current_path_index = 0
        self.vehicle.action_plan = [{"type": "pickup", "task": rerouted_task}]

        self.sim._update_vehicle(self.vehicle)

        self.assertEqual(1, self.vehicle.current_node)
        self.assertEqual([1, 3], self.vehicle.current_path_nodes)
        self.assertEqual(0, self.vehicle.current_path_index)
        self.assertEqual(VehicleStatus.MOVING, self.vehicle.status)

    def test_low_battery_reroute_waits_until_next_node_when_moving(self):
        class Station:
            id = 0
            node_id = 3

        self.sim.charging_stations = [Station()]
        self.sim.map.find_nearest_station = lambda node_id: 3
        self.vehicle.status = VehicleStatus.MOVING
        self.vehicle.current_node = 0
        self.vehicle.position = (5.0, 0.0)
        self.vehicle.current_battery = 1.0
        self.vehicle.current_path_nodes = [0, 1, 2]
        self.vehicle.current_path_index = 0
        self.vehicle.action_plan = []

        self.sim._handle_low_battery()

        self.assertEqual(VehicleStatus.MOVING, self.vehicle.status)
        self.assertEqual([0, 1, 2], self.vehicle.current_path_nodes)
        self.assertEqual(0, self.vehicle.current_path_index)
        self.assertEqual((5.0, 0.0), self.vehicle.position)
        self.assertEqual("move", self.vehicle.action_plan[0]["type"])
        self.assertEqual(3, self.vehicle.action_plan[0]["target"])
        self.assertEqual("charge", self.vehicle.action_plan[1]["type"])


if __name__ == "__main__":
    unittest.main()
