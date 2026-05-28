import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.models.task import Task
from backend.models.vehicle import Vehicle
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


if __name__ == "__main__":
    unittest.main()
