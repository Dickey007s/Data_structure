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
        seed: int = 42,
    ):
        self.task_count = task_count
        self.time_horizon = time_horizon
        self.weight_range = weight_range
        self.map_nodes = map_nodes or []
        self.seed = seed
        self.generated_count = 0
        self.schedule: List[dict] = []

        random.seed(seed)

    def generate_schedule(self) -> None:
        """Pre-generate task appearance schedule."""
        if self.time_horizon <= 1 or not self.map_nodes:
            return

        num_times = min(self.task_count, self.time_horizon - 1)
        times = sorted(random.sample(range(1, self.time_horizon), num_times))

        self.schedule = []
        for i, t in enumerate(times):
            pickup = random.choice(self.map_nodes)
            delivery_candidates = [n for n in self.map_nodes if n != pickup]
            delivery = random.choice(delivery_candidates) if delivery_candidates else pickup

            weight = round(random.uniform(*self.weight_range), 2)
            ready_time = t
            due_time = t + random.randint(300, 800)

            self.schedule.append({
                "id": i + 1,
                "pickup_node": pickup,
                "delivery_node": delivery,
                "weight": weight,
                "ready_time": ready_time,
                "due_time": due_time,
                "create_time": t,
            })

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

