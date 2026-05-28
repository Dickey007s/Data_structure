"""Event generator - creates tasks dynamically over time."""

import random
from typing import List, Optional
from backend.models.task import Task


class EventGenerator:
    """Generates tasks at random times within the simulation horizon."""

    def __init__(
        self,
        task_count: int,
        time_horizon: int,
        weight_range: tuple = (1.0, 20.0),
        map_nodes: List[int] = None,
        depot_node: Optional[int] = None,
        sub_depot_nodes: List[int] = None,
        service_nodes: List[int] = None,
        single_task_ratio: float = 0.4,
        seed: int = 42,
    ):
        self.task_count = task_count
        self.time_horizon = time_horizon
        self.weight_range = weight_range
        self.map_nodes = map_nodes or []
        self.depot_node = depot_node
        self.sub_depot_nodes = sub_depot_nodes or []
        self.service_nodes = service_nodes or self._default_service_nodes()
        self.single_task_ratio = single_task_ratio
        self.seed = seed
        self.generated_count = 0
        self.schedule: List[dict] = []

        random.seed(seed)

    def _default_service_nodes(self) -> List[int]:
        excluded = {self.depot_node, *self.sub_depot_nodes}
        return [n for n in self.map_nodes if n not in excluded]

    def generate_schedule(self) -> None:
        """Pre-generate task appearance schedule."""
        if self.time_horizon <= 1 or not self.map_nodes:
            return

        num_times = min(self.task_count, self.time_horizon - 1)
        times = sorted(random.sample(range(1, self.time_horizon), num_times))

        self.schedule = []
        for i, t in enumerate(times):
            task_type, pickup, delivery = self._generate_task_endpoints()

            weight = round(random.uniform(*self.weight_range), 2)
            ready_time = t
            due_time = t + random.randint(500, 1200)

            self.schedule.append({
                "id": i + 1,
                "pickup_node": pickup,
                "delivery_node": delivery,
                "task_type": task_type,
                "weight": weight,
                "ready_time": ready_time,
                "due_time": due_time,
                "create_time": t,
            })

    def _generate_task_endpoints(self) -> tuple:
        service_nodes = self.service_nodes or self.map_nodes
        can_generate_single = (
            self.depot_node is not None
            and bool(service_nodes)
            and bool(self.sub_depot_nodes)
        )

        if can_generate_single and random.random() < self.single_task_ratio:
            if random.random() < 0.5:
                return (
                    Task.TYPE_DEPOT_DELIVERY,
                    self.depot_node,
                    random.choice(service_nodes),
                )
            return (
                Task.TYPE_SUB_DEPOT_RETURN,
                random.choice(self.sub_depot_nodes),
                self.depot_node,
            )

        candidates = service_nodes if len(service_nodes) >= 2 else self.map_nodes
        pickup = random.choice(candidates)
        delivery_candidates = [n for n in candidates if n != pickup]
        delivery = random.choice(delivery_candidates) if delivery_candidates else pickup
        return Task.TYPE_PAIRED, pickup, delivery

    def generate(self, current_time: int) -> List[Task]:
        """Generate tasks that should appear at current_time."""
        tasks = []
        while (
            self.schedule
            and self.schedule[0]["create_time"] <= current_time
            and self.generated_count < self.task_count
        ):
            data = self.schedule.pop(0)
            task = Task(**data)
            tasks.append(task)
            self.generated_count += 1
        return tasks

    def peek_next_time(self) -> Optional[int]:
        """View next task generation time."""
        if self.schedule:
            return self.schedule[0]["create_time"]
        return None

