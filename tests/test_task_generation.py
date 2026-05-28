import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.models.task import Task
from backend.models.transport_map import TransportMap
from backend.simulator.event_generator import EventGenerator


class TaskGenerationTest(unittest.TestCase):
    def test_map_marks_two_fixed_sub_depots(self):
        transport_map = TransportMap(1000, 800)

        transport_map.generate_grid(64, num_stations=3, num_sub_depots=2, seed=42)

        self.assertEqual(2, len(transport_map.sub_depot_nodes))
        self.assertNotIn(transport_map.depot_node, transport_map.sub_depot_nodes)
        self.assertTrue(
            all(transport_map.nodes[n][2] == "sub_depot" for n in transport_map.sub_depot_nodes)
        )

    def test_generator_creates_single_point_tasks_with_valid_endpoints(self):
        generator = EventGenerator(
            task_count=20,
            time_horizon=100,
            map_nodes=[0, 1, 2, 3, 4, 5],
            depot_node=0,
            sub_depot_nodes=[1, 2],
            service_nodes=[3, 4, 5],
            single_task_ratio=1.0,
            seed=7,
        )

        generator.generate_schedule()
        generated_types = {item["task_type"] for item in generator.schedule}

        self.assertLessEqual(generated_types, {
            Task.TYPE_DEPOT_DELIVERY,
            Task.TYPE_SUB_DEPOT_RETURN,
        })
        self.assertIn(Task.TYPE_DEPOT_DELIVERY, generated_types)
        self.assertIn(Task.TYPE_SUB_DEPOT_RETURN, generated_types)

        for item in generator.schedule:
            if item["task_type"] == Task.TYPE_DEPOT_DELIVERY:
                self.assertEqual(0, item["pickup_node"])
                self.assertIn(item["delivery_node"], [3, 4, 5])
            elif item["task_type"] == Task.TYPE_SUB_DEPOT_RETURN:
                self.assertIn(item["pickup_node"], [1, 2])
                self.assertEqual(0, item["delivery_node"])

    def test_generator_keeps_existing_paired_task_shape(self):
        generator = EventGenerator(
            task_count=10,
            time_horizon=50,
            map_nodes=[0, 1, 2, 3, 4],
            depot_node=0,
            sub_depot_nodes=[1, 2],
            service_nodes=[3, 4],
            single_task_ratio=0.0,
            seed=11,
        )

        generator.generate_schedule()

        self.assertTrue(generator.schedule)
        for item in generator.schedule:
            self.assertEqual(Task.TYPE_PAIRED, item["task_type"])
            self.assertIn(item["pickup_node"], [3, 4])
            self.assertIn(item["delivery_node"], [3, 4])
            self.assertNotEqual(item["pickup_node"], item["delivery_node"])


if __name__ == "__main__":
    unittest.main()
