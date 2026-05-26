# 新能源物流车队协同调度仿真平台 - 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个完整的新能源物流车队协同调度仿真平台，包含 Python 后端仿真引擎（Flask + WebSocket）、3 种调度策略、实时 Canvas 前端可视化，支持 10 辆车/100 任务规模的仿真。

**Architecture:** 后端采用离散时间步进仿真（tick-based），Flask-SocketIO 实时推送状态；前端使用纯 HTML/CSS/JS + Canvas 2D 渲染车辆轨迹、任务状态和充电站负荷。调度策略通过抽象基类实现插件化架构。

**Tech Stack:** Python 3.11 + Flask + Flask-SocketIO + NetworkX + NumPy | HTML5 + CSS3 + Vanilla JS + Canvas 2D + Socket.IO Client

---

## Agent Team 分工

| Agent | 负责阶段 | 交付文件 |
|-------|---------|---------|
| **Backend Agent** | Phase 1-5 | `backend/` 所有 Python 文件 |
| **Frontend Agent** | Phase 6-7 | `frontend/` 所有 HTML/CSS/JS 文件 |
| **Algo Agent** | Phase 3 (深度参与) | `backend/scheduler/*.py` 算法优化 |
| **Integration Agent** | Phase 8 | 联调测试、运行验证 |

---

## 文件结构总览

```
123/
├── backend/
│   ├── __init__.py
│   ├── app.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── task.py
│   │   ├── vehicle.py
│   │   ├── charging_station.py
│   │   └── transport_map.py
│   ├── scheduler/
│   │   ├── __init__.py
│   │   ├── base_scheduler.py
│   │   ├── nearest_first_scheduler.py
│   │   ├── max_weight_scheduler.py
│   │   └── insertion_scheduler.py
│   ├── simulator/
│   │   ├── __init__.py
│   │   ├── simulator.py
│   │   └── event_generator.py
│   └── requirements.txt
└── frontend/
    ├── index.html
    ├── css/
    │   └── styles.css
    └── js/
        ├── socket_client.js
        ├── map_renderer.js
        ├── vehicle_renderer.js
        ├── task_renderer.js
        ├── station_renderer.js
        └── ui_controller.js
```

---

## Phase 1: 项目初始化

### Task 1: 创建目录结构

**负责 Agent:** Backend Agent + Frontend Agent

**Files:**
- Create: `backend/__init__.py`
- Create: `backend/models/__init__.py`
- Create: `backend/scheduler/__init__.py`
- Create: `backend/simulator/__init__.py`
- Create: `frontend/css/.gitkeep`
- Create: `frontend/js/.gitkeep`

- [ ] **Step 1: 创建所有目录和空 init 文件**

```bash
cd /d/Projects/123
mkdir -p backend/models backend/scheduler backend/simulator frontend/css frontend/js
touch backend/__init__.py
touch backend/models/__init__.py
touch backend/scheduler/__init__.py
touch backend/simulator/__init__.py
```

- [ ] **Step 2: 验证目录结构**

```bash
tree -L 3 backend frontend
```

Expected: 显示完整的目录树结构

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "chore: initialize project directory structure"
```

---

### Task 2: 依赖管理

**负责 Agent:** Backend Agent

**Files:**
- Create: `backend/requirements.txt`

- [ ] **Step 1: 创建 requirements.txt**

```bash
cat > backend/requirements.txt << 'EOF'
flask==3.0.0
flask-socketio==5.3.0
flask-cors==4.0.0
networkx==3.2.1
numpy==1.26.0
python-socketio==5.9.0
EOF
```

- [ ] **Step 2: 安装依赖**

```bash
cd /d/Projects/123/backend
pip install -r requirements.txt
```

Expected: 所有包安装成功

- [ ] **Step 3: 验证安装**

```bash
python -c "import flask; import flask_socketio; import networkx; import numpy; print('All dependencies OK')"
```

Expected: `All dependencies OK`

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add Python dependencies"
```

---

## Phase 2: 核心数据模型

### Task 3: Task 模型

**负责 Agent:** Backend Agent

**Files:**
- Create: `backend/models/task.py`

- [ ] **Step 1: 编写 Task 类**

```python
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
```

- [ ] **Step 2: 运行快速验证**

```bash
cd /d/Projects/123
python -c "
from backend.models.task import Task
t = Task(1, 5, 10, 8.5, 10, 100, 5)
print(f'Task created: id={t.id}, status={t.status}')
print(f'Timeout check (at 50): {t.is_timeout(50)}')
print(f'Timeout check (at 101): {t.is_timeout(101)}')
t.status = Task.STATUS_COMPLETED
t.completed_time = 80
print(f'Score: {t.get_score()}')
"
```

Expected:
```
Task created: id=1, status=pending
Timeout check (at 50): False
Timeout check (at 101): True
Score: 120.0
```

- [ ] **Step 3: Commit**

```bash
git add backend/models/task.py
git commit -m "feat(models): add Task model with status, scoring and serialization"
```

---

### Task 4: Vehicle 模型

**负责 Agent:** Backend Agent

**Files:**
- Create: `backend/models/vehicle.py`

- [ ] **Step 1: 编写 VehicleStatus 枚举和 Vehicle 类**

```python
"""Vehicle model - represents an electric delivery vehicle."""

from enum import Enum
from typing import List, Tuple, Optional
from backend.models.task import Task


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
        self.carrying_tasks: List[Task] = []
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

    def add_task(self, task: Task) -> bool:
        """Add task to carrying list."""
        if self.can_carry(task.weight):
            self.carrying_tasks.append(task)
            self.current_load += task.weight
            return True
        return False

    def remove_task(self, task: Task) -> None:
        """Remove completed task and reduce load."""
        if task in self.carrying_tasks:
            self.carrying_tasks.remove(task)
            self.current_load -= task.weight
            self.current_load = max(0.0, self.current_load)

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON transmission."""
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
            "carrying": [t.id for t in self.carrying_tasks],
        }
```

- [ ] **Step 2: 运行验证**

```bash
cd /d/Projects/123
python -c "
from backend.models.vehicle import Vehicle, VehicleStatus
from backend.models.task import Task

v = Vehicle(1, 0, 100.0, 50.0, 0.5, 1.2)
print(f'Vehicle created: id={v.id}, battery={v.current_battery}')
print(f'Consumption (empty): {v.get_consumption_rate()}')

t = Task(1, 5, 10, 10.0, 0, 100, 0)
v.add_task(t)
print(f'After loading: load={v.current_load}, consumption={v.get_consumption_rate():.3f}')
v.move(10.0)
print(f'After moving 10: battery={v.current_battery:.2f}')
print(f'Dict: {v.to_dict()[\"status\"]}')
"
```

Expected:
```
Vehicle created: id=1, battery=100.0
Consumption (empty): 0.5
After loading: load=10.0, consumption=0.640
After moving 10: battery=93.60
Dict: idle
```

- [ ] **Step 3: Commit**

```bash
git add backend/models/vehicle.py
git commit -m "feat(models): add Vehicle model with battery, load and consumption"
```

---

### Task 5: ChargingStation 模型

**负责 Agent:** Backend Agent

**Files:**
- Create: `backend/models/charging_station.py`

- [ ] **Step 1: 编写 ChargingStation 类**

```python
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
```

- [ ] **Step 2: 运行验证**

```bash
cd /d/Projects/123
python -c "
from backend.models.charging_station import ChargingStation
from backend.models.vehicle import Vehicle, VehicleStatus

s = ChargingStation(1, 10, 3, 5.0)
v = Vehicle(1, 10, 100.0, 50.0, 0.5, 1.2)
v.current_battery = 50.0

print(f'Station available: {s.is_available()}')
s.start_charging(v)
print(f'After start: occupied={s.occupied_slots}, status={v.status.value}')

s.tick(5.0)
print(f'After tick: battery={v.current_battery:.1f}')

v2 = Vehicle(2, 10, 100.0, 50.0, 0.5, 1.2)
s.join_queue(v2)
print(f'Queue length: {len(s.waiting_queue)}')
"
```

Expected:
```
Station available: True
After start: occupied=1, status=charging
After tick: battery=75.0
Queue length: 1
```

- [ ] **Step 3: Commit**

```bash
git add backend/models/charging_station.py
git commit -m "feat(models): add ChargingStation with queue and slot management"
```

---

### Task 6: TransportMap 路网模型

**负责 Agent:** Backend Agent

**Files:**
- Create: `backend/models/transport_map.py`

- [ ] **Step 1: 编写 TransportMap 类**

```python
"""TransportMap model - road network graph using NetworkX."""

import math
import random
from typing import Dict, List, Tuple, Optional
import networkx as nx


class TransportMap:
    """Road network represented as a graph with grid layout."""

    def __init__(self, width: int, height: int, grid_type: str = "hex"):
        self.graph = nx.Graph()
        self.nodes: Dict[int, Tuple[float, float, str]] = {}
        self.dist_matrix: Dict[Tuple[int, int], float] = {}
        self.width = width
        self.height = height
        self.grid_type = grid_type
        self.depot_node = 0
        self.station_nodes: List[int] = []

    def generate_grid(
        self,
        num_nodes: int,
        num_stations: int = 3,
        connection_prob: float = 0.4,
        seed: int = 42,
    ) -> None:
        """Generate a grid-like road network."""
        random.seed(seed)

        # Calculate grid dimensions
        cols = int(math.sqrt(num_nodes))
        rows = (num_nodes + cols - 1) // cols

        # Generate nodes in a grid
        node_id = 0
        for row in range(rows):
            for col in range(cols):
                if node_id >= num_nodes:
                    break

                x = (col / max(cols - 1, 1)) * self.width
                y = (row / max(rows - 1, 1)) * self.height

                # First node is depot
                node_type = "depot" if node_id == 0 else "normal"
                self.add_node(node_id, x, y, node_type)
                node_id += 1

        # Add some random connections for irregularity
        extra_nodes = num_nodes - node_id
        for i in range(extra_nodes):
            x = random.uniform(0, self.width)
            y = random.uniform(0, self.height)
            self.add_node(node_id, x, y, "normal")
            node_id += 1

        # Connect neighboring nodes
        for node_id in self.nodes:
            x, y, _ = self.nodes[node_id]
            # Find nearest nodes
            neighbors = []
            for other_id in self.nodes:
                if other_id == node_id:
                    continue
                ox, oy, _ = self.nodes[other_id]
                dist = math.sqrt((x - ox) ** 2 + (y - oy) ** 2)
                neighbors.append((dist, other_id))

            neighbors.sort()
            # Connect to 2-4 nearest neighbors
            num_connections = random.randint(2, 4)
            for dist, other_id in neighbors[:num_connections]:
                if not self.graph.has_edge(node_id, other_id):
                    self.add_road(node_id, other_id, dist)

        # Assign station nodes (pick from non-depot nodes)
        non_depot = [n for n in self.nodes if n != self.depot_node]
        if len(non_depot) >= num_stations:
            self.station_nodes = sorted(random.sample(non_depot, num_stations))
            for sid in self.station_nodes:
                x, y, _ = self.nodes[sid]
                self.nodes[sid] = (x, y, "station")
                self.graph.nodes[sid]["type"] = "station"

    def add_node(self, node_id: int, x: float, y: float, node_type: str = "normal") -> None:
        """Add a node to the map."""
        self.nodes[node_id] = (x, y, node_type)
        self.graph.add_node(node_id, pos=(x, y), type=node_type)

    def add_road(self, u: int, v: int, distance: float = None) -> None:
        """Add a road (edge) between two nodes."""
        if distance is None:
            ux, uy, _ = self.nodes[u]
            vx, vy, _ = self.nodes[v]
            distance = math.sqrt((ux - vx) ** 2 + (uy - vy) ** 2)
        self.graph.add_edge(u, v, weight=round(distance, 2))

    def get_distance(self, u: int, v: int) -> float:
        """Get shortest path distance between two nodes."""
        if u == v:
            return 0.0
        key = (min(u, v), max(u, v))
        if key not in self.dist_matrix:
            try:
                self.dist_matrix[key] = nx.shortest_path_length(
                    self.graph, u, v, weight="weight"
                )
            except nx.NetworkXNoPath:
                self.dist_matrix[key] = float("inf")
        return self.dist_matrix[key]

    def get_path(self, u: int, v: int) -> List[int]:
        """Get shortest path as list of node IDs."""
        try:
            return nx.shortest_path(self.graph, u, v, weight="weight")
        except nx.NetworkXNoPath:
            return []

    def find_nearest_station(self, node_id: int) -> Optional[int]:
        """Find nearest charging station to given node."""
        if not self.station_nodes:
            return None

        min_dist = float("inf")
        nearest = self.station_nodes[0]
        for station_node in self.station_nodes:
            dist = self.get_distance(node_id, station_node)
            if dist < min_dist:
                min_dist = dist
                nearest = station_node
        return nearest

    def get_node_position(self, node_id: int) -> Tuple[float, float]:
        """Get world coordinates of a node."""
        return self.nodes[node_id][:2]

    def to_dict(self) -> dict:
        """Serialize to dictionary for frontend."""
        return {
            "nodes": [
                {"id": nid, "x": round(x, 2), "y": round(y, 2), "type": ntype}
                for nid, (x, y, ntype) in self.nodes.items()
            ],
            "edges": [
                {"u": u, "v": v, "weight": round(d["weight"], 2)}
                for u, v, d in self.graph.edges(data=True)
            ],
        }
```

- [ ] **Step 2: 运行验证**

```bash
cd /d/Projects/123
python -c "
from backend.models.transport_map import TransportMap

m = TransportMap(100, 100)
m.generate_grid(20, num_stations=3)
print(f'Nodes: {len(m.nodes)}, Edges: {m.graph.number_of_edges()}')
print(f'Stations: {m.station_nodes}')
print(f'Distance 0->5: {m.get_distance(0, 5):.2f}')
print(f'Path 0->5: {m.get_path(0, 5)}')
print(f'Nearest station to 0: {m.find_nearest_station(0)}')
data = m.to_dict()
print(f'JSON nodes: {len(data[\"nodes\"])}, edges: {len(data[\"edges\"])}')
"
```

Expected: 成功生成地图，显示节点数、边数、路径和距离

- [ ] **Step 3: Commit**

```bash
git add backend/models/transport_map.py
git commit -m "feat(models): add TransportMap with grid generation and pathfinding"
```

---

## Phase 3: 调度策略层

### Task 7: 调度器基类

**负责 Agent:** Algo Agent

**Files:**
- Create: `backend/scheduler/base_scheduler.py`

- [ ] **Step 1: 编写 BaseScheduler**

```python
"""Base scheduler interface for task assignment strategies."""

from abc import ABC, abstractmethod
from typing import List, Optional
from backend.models.task import Task
from backend.models.vehicle import Vehicle, VehicleStatus
from backend.models.transport_map import TransportMap


class BaseScheduler(ABC):
    """Abstract base class for task scheduling strategies."""

    @abstractmethod
    def assign_task(
        self,
        task: Task,
        fleet: List[Vehicle],
        map_obj: TransportMap,
    ) -> Optional[Vehicle]:
        """Assign task to the most suitable vehicle.

        Args:
            task: The task to assign
            fleet: List of available vehicles
            map_obj: The transport map

        Returns:
            The assigned vehicle, or None if no vehicle available
        """
        pass

    @abstractmethod
    def replan(
        self,
        fleet: List[Vehicle],
        active_tasks: List[Task],
        map_obj: TransportMap,
    ) -> None:
        """Replan routes for all vehicles (optional periodic re-optimization)."""
        pass

    def check_capacity(self, vehicle: Vehicle, task: Task) -> bool:
        """Check if vehicle can carry the task weight."""
        return vehicle.can_carry(task.weight)

    def check_battery(
        self,
        vehicle: Vehicle,
        task: Task,
        map_obj: TransportMap,
        planned_distance: float,
        safety_margin: float = 1.2,
    ) -> bool:
        """Check if vehicle has enough battery for planned route plus safety margin."""
        consumption = vehicle.get_consumption_rate() * planned_distance

        nearest_station = map_obj.find_nearest_station(task.delivery_node)
        if nearest_station is None:
            return vehicle.current_battery >= consumption

        dist_to_station = map_obj.get_distance(task.delivery_node, nearest_station)
        consumption_to_station = vehicle.consumption_empty * dist_to_station * safety_margin

        return vehicle.current_battery >= consumption + consumption_to_station

    def check_time_window(self, vehicle: Vehicle, task: Task, arrival_time: int) -> bool:
        """Check if arrival time satisfies task time window."""
        return arrival_time <= task.due_time
```

- [ ] **Step 2: Commit**

```bash
git add backend/scheduler/base_scheduler.py
git commit -m "feat(scheduler): add BaseScheduler abstract interface"
```

---

### Task 8: 最近优先调度器

**负责 Agent:** Algo Agent

**Files:**
- Create: `backend/scheduler/nearest_first_scheduler.py`

- [ ] **Step 1: 编写 NearestFirstScheduler**

```python
"""Nearest-first scheduling strategy."""

from typing import List, Optional
from backend.models.task import Task
from backend.models.vehicle import Vehicle, VehicleStatus
from backend.models.transport_map import TransportMap
from backend.scheduler.base_scheduler import BaseScheduler


class NearestFirstScheduler(BaseScheduler):
    """Assign task to the vehicle nearest to the pickup point."""

    def assign_task(
        self,
        task: Task,
        fleet: List[Vehicle],
        map_obj: TransportMap,
    ) -> Optional[Vehicle]:
        """Assign task to nearest available vehicle."""
        best_vehicle = None
        min_cost = float("inf")

        for vehicle in fleet:
            if vehicle.status not in [VehicleStatus.IDLE, VehicleStatus.MOVING]:
                continue

            # Calculate distance: current -> pickup -> delivery
            dist_to_pickup = map_obj.get_distance(vehicle.current_node, task.pickup_node)
            dist_delivery = map_obj.get_distance(task.pickup_node, task.delivery_node)
            total_distance = dist_to_pickup + dist_delivery

            # Constraint checks
            if not self.check_capacity(vehicle, task):
                continue
            if not self.check_battery(vehicle, task, map_obj, total_distance):
                continue

            if total_distance < min_cost:
                min_cost = total_distance
                best_vehicle = vehicle

        if best_vehicle:
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
        # Build path: current -> pickup -> delivery
        path_to_pickup = map_obj.get_path(vehicle.current_node, task.pickup_node)
        path_to_delivery = map_obj.get_path(task.pickup_node, task.delivery_node)

        if path_to_pickup and path_to_delivery:
            # Merge paths (avoid duplicate pickup node)
            vehicle.current_path_nodes = path_to_pickup[:-1] + path_to_delivery
        elif path_to_pickup:
            vehicle.current_path_nodes = path_to_pickup
        else:
            vehicle.current_path_nodes = [vehicle.current_node]

        vehicle.current_path_index = 0
        vehicle.status = VehicleStatus.MOVING
        vehicle.add_task(task)
        task.status = Task.STATUS_ASSIGNED
        task.assigned_vehicle = vehicle.id

        # Build action plan
        vehicle.action_plan = [
            {"type": "pickup", "task": task},
            {"type": "deliver", "task": task},
        ]

    def replan(self, fleet: List[Vehicle], active_tasks: List[Task], map_obj: TransportMap) -> None:
        """Greedy strategy does not support replanning."""
        pass
```

- [ ] **Step 2: Commit**

```bash
git add backend/scheduler/nearest_first_scheduler.py
git commit -m "feat(scheduler): add nearest-first greedy strategy"
```

---

### Task 9: 最大重量优先调度器

**负责 Agent:** Algo Agent

**Files:**
- Create: `backend/scheduler/max_weight_scheduler.py`

- [ ] **Step 1: 编写 MaxWeightScheduler**

```python
"""Max-weight-first scheduling strategy."""

from typing import List, Optional
from backend.models.task import Task
from backend.models.vehicle import Vehicle, VehicleStatus
from backend.models.transport_map import TransportMap
from backend.scheduler.base_scheduler import BaseScheduler


class MaxWeightScheduler(BaseScheduler):
    """Prioritize heavy tasks, selecting most efficient vehicle."""

    def assign_task(
        self,
        task: Task,
        fleet: List[Vehicle],
        map_obj: TransportMap,
    ) -> Optional[Vehicle]:
        """Assign task to vehicle with best weight/distance ratio."""
        candidates = []

        for vehicle in fleet:
            if vehicle.status not in [VehicleStatus.IDLE, VehicleStatus.MOVING]:
                continue

            dist_to_pickup = map_obj.get_distance(vehicle.current_node, task.pickup_node)
            dist_delivery = map_obj.get_distance(task.pickup_node, task.delivery_node)
            total_distance = dist_to_pickup + dist_delivery

            if not self.check_capacity(vehicle, task):
                continue
            if not self.check_battery(vehicle, task, map_obj, total_distance):
                continue

            # Efficiency = weight / distance (higher is better)
            efficiency = task.weight / (total_distance + 1)
            candidates.append((efficiency, vehicle, total_distance))

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            _, best_vehicle, _ = candidates[0]
            self._assign_to_vehicle(best_vehicle, task, map_obj)
            return best_vehicle
        return None

    def _assign_to_vehicle(
        self,
        vehicle: Vehicle,
        task: Task,
        map_obj: TransportMap,
    ) -> None:
        """Append task to vehicle's route (same as nearest-first)."""
        path_to_pickup = map_obj.get_path(vehicle.current_node, task.pickup_node)
        path_to_delivery = map_obj.get_path(task.pickup_node, task.delivery_node)

        if path_to_pickup and path_to_delivery:
            vehicle.current_path_nodes = path_to_pickup[:-1] + path_to_delivery
        elif path_to_pickup:
            vehicle.current_path_nodes = path_to_pickup
        else:
            vehicle.current_path_nodes = [vehicle.current_node]

        vehicle.current_path_index = 0
        vehicle.status = VehicleStatus.MOVING
        vehicle.add_task(task)
        task.status = Task.STATUS_ASSIGNED
        task.assigned_vehicle = vehicle.id

        vehicle.action_plan = [
            {"type": "pickup", "task": task},
            {"type": "deliver", "task": task},
        ]

    def replan(self, fleet: List[Vehicle], active_tasks: List[Task], map_obj: TransportMap) -> None:
        """Greedy strategy does not support replanning."""
        pass
```

- [ ] **Step 2: Commit**

```bash
git add backend/scheduler/max_weight_scheduler.py
git commit -m "feat(scheduler): add max-weight-first greedy strategy"
```

---

### Task 10: 插入启发式调度器

**负责 Agent:** Algo Agent

**Files:**
- Create: `backend/scheduler/insertion_scheduler.py`

- [ ] **Step 1: 编写 InsertionScheduler**

```python
"""Insertion heuristic scheduling strategy."""

from typing import List, Optional, Tuple
from backend.models.task import Task
from backend.models.vehicle import Vehicle, VehicleStatus
from backend.models.transport_map import TransportMap
from backend.scheduler.base_scheduler import BaseScheduler


class InsertionScheduler(BaseScheduler):
    """Insert new task into the best position of existing routes."""

    def assign_task(
        self,
        task: Task,
        fleet: List[Vehicle],
        map_obj: TransportMap,
    ) -> Optional[Vehicle]:
        """Find best insertion position across all vehicles."""
        best_cost = float("inf")
        best_vehicle = None
        best_insertion = None  # (pickup_idx, delivery_idx)

        for vehicle in fleet:
            # Vehicle with no route: direct assignment
            if not vehicle.action_plan:
                cost = self._calculate_direct_cost(vehicle, task, map_obj)
                if cost is not None and cost < best_cost:
                    best_cost = cost
                    best_vehicle = vehicle
                    best_insertion = (0, 1)
                continue

            # Try all possible insertion positions
            n = len(vehicle.action_plan)
            for p_idx in range(n + 1):
                for d_idx in range(p_idx, n + 2):
                    cost = self._calculate_insertion_cost(
                        vehicle, task, p_idx, d_idx, map_obj
                    )
                    if cost is not None and cost < best_cost:
                        best_cost = cost
                        best_vehicle = vehicle
                        best_insertion = (p_idx, d_idx)

        if best_vehicle and best_insertion:
            self._apply_insertion(best_vehicle, task, best_insertion)
            return best_vehicle
        return None

    def _calculate_direct_cost(
        self,
        vehicle: Vehicle,
        task: Task,
        map_obj: TransportMap,
    ) -> Optional[float]:
        """Calculate cost for direct assignment to empty vehicle."""
        if not self.check_capacity(vehicle, task):
            return None

        dist = (
            map_obj.get_distance(vehicle.current_node, task.pickup_node)
            + map_obj.get_distance(task.pickup_node, task.delivery_node)
        )

        if not self.check_battery(vehicle, task, map_obj, dist):
            return None

        return dist

    def _calculate_insertion_cost(
        self,
        vehicle: Vehicle,
        task: Task,
        p_idx: int,
        d_idx: int,
        map_obj: TransportMap,
    ) -> Optional[float]:
        """Calculate marginal cost of inserting task at given positions."""
        if not self.check_capacity(vehicle, task):
            return None

        # Build tentative action plan
        new_plan = vehicle.action_plan.copy()
        new_plan.insert(p_idx, {"type": "pickup", "task": task})
        new_plan.insert(d_idx + 1, {"type": "deliver", "task": task})

        # Simulate route to calculate total distance
        total_dist = 0.0
        current_node = vehicle.current_node

        for action in new_plan:
            if action["type"] == "pickup":
                target = action["task"].pickup_node
            elif action["type"] == "deliver":
                target = action["task"].delivery_node
            elif action["type"] == "move":
                target = action["target"]
            else:
                continue

            dist = map_obj.get_distance(current_node, target)
            if dist == float("inf"):
                return None
            total_dist += dist
            current_node = target

        if not self.check_battery(vehicle, task, map_obj, total_dist):
            return None

        # Marginal cost = total distance with insertion
        return total_dist

    def _apply_insertion(
        self,
        vehicle: Vehicle,
        task: Task,
        insertion: Tuple[int, int],
    ) -> None:
        """Apply the insertion to vehicle's action plan."""
        p_idx, d_idx = insertion
        vehicle.action_plan.insert(p_idx, {"type": "pickup", "task": task})
        vehicle.action_plan.insert(d_idx + 1, {"type": "deliver", "task": task})

        # Rebuild path from action plan
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
                path = vehicle.current_path_nodes
                path.append(target)
                current = target

        vehicle.current_path_index = 0
        if len(vehicle.current_path_nodes) > 1:
            vehicle.status = VehicleStatus.MOVING

        vehicle.add_task(task)
        task.status = Task.STATUS_ASSIGNED
        task.assigned_vehicle = vehicle.id

    def replan(self, fleet: List[Vehicle], active_tasks: List[Task], map_obj: TransportMap) -> None:
        """Periodic re-optimization (placeholder for future improvement)."""
        pass
```

- [ ] **Step 2: Commit**

```bash
git add backend/scheduler/insertion_scheduler.py
git commit -m "feat(scheduler): add insertion heuristic strategy"
```

---

## Phase 4: 仿真引擎

### Task 11: 任务生成器

**负责 Agent:** Backend Agent

**Files:**
- Create: `backend/simulator/event_generator.py`

- [ ] **Step 1: 编写 EventGenerator**

```python
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
            due_time = t + random.randint(30, 150)

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
```

- [ ] **Step 2: Commit**

```bash
git add backend/simulator/event_generator.py
git commit -m "feat(simulator): add EventGenerator for dynamic task creation"
```

---

### Task 12: 主仿真器

**负责 Agent:** Backend Agent

**Files:**
- Create: `backend/simulator/simulator.py`

- [ ] **Step 1: 编写 Simulator 类（完整版）**

```python
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

        self._emit_state: Optional[Callable] = None
        self._emit_finished: Optional[Callable] = None

    def initialize(
        self,
        map_config: dict,
        fleet_config: List[dict],
        station_config: List[dict],
        scheduler_type: str,
    ) -> None:
        """Initialize simulation environment."""
        # Create map
        self.map = TransportMap(map_config["width"], map_config["height"])
        self.map.generate_grid(
            map_config["num_nodes"],
            num_stations=len(station_config),
        )

        # Add charging stations
        for sc in station_config:
            station = ChargingStation(**sc)
            self.charging_stations.append(station)
            if sc["node_id"] not in self.map.station_nodes:
                self.map.station_nodes.append(sc["node_id"])
            if sc["node_id"] in self.map.nodes:
                x, y, _ = self.map.nodes[sc["node_id"]]
                self.map.nodes[sc["node_id"]] = (x, y, "station")

        # Create fleet
        for fc in fleet_config:
            vehicle = Vehicle(**fc)
            vehicle.position = self.map.get_node_position(fc["start_node"])
            self.fleet.append(vehicle)

        # Set scheduler
        self.scheduler = self._create_scheduler(scheduler_type)

        # Create event generator
        self.event_generator = EventGenerator(
            task_count=self.config.get("task_count", 100),
            time_horizon=self.config.get("time_horizon", 1000),
            map_nodes=list(self.map.nodes.keys()),
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
            station.tick(self.tick_interval)

        # 4. Check timeout tasks
        for task in self.active_tasks[:]:
            if task.is_timeout(self.current_time):
                task.status = Task.STATUS_TIMEOUT
                self.failed_tasks.append(task)
                self.active_tasks.remove(task)

        # 5. Handle low battery
        self._handle_low_battery()

        # 6. Calculate score
        score = self._calculate_score()

        return self._get_state_snapshot(score)

    def _update_vehicle(self, vehicle: Vehicle) -> None:
        """Update a single vehicle's state."""
        if vehicle.status == VehicleStatus.MOVING:
            self._update_moving(vehicle)
        elif vehicle.status == VehicleStatus.IDLE:
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

        current_pos = self.map.get_node_position(current_node_id)
        next_pos = self.map.get_node_position(next_node_id)
        segment_distance = self.map.get_distance(current_node_id, next_node_id)

        speed = self.config.get("vehicle_speed", 10.0)
        if segment_distance > 0:
            vehicle.progress += (speed * self.tick_interval) / segment_distance

        if vehicle.progress >= 1.0:
            vehicle.current_path_index += 1
            vehicle.progress = 0.0
            vehicle.current_node = next_node_id
            vehicle.move(segment_distance)

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

    def _on_arrive_at_node(self, vehicle: Vehicle) -> None:
        """Handle vehicle arriving at destination node."""
        vehicle.status = VehicleStatus.IDLE
        vehicle.progress = 0.0
        vehicle.current_path_nodes = []
        vehicle.current_path_index = 0

        # Check if at charging station
        for station in self.charging_stations:
            if station.node_id == vehicle.current_node:
                if station.is_available():
                    station.start_charging(vehicle)
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
            vehicle.status = VehicleStatus.LOADING
            task.status = Task.STATUS_PICKING
            vehicle.add_task(task)
            task.status = Task.STATUS_DELIVERING
            vehicle.status = VehicleStatus.IDLE

        elif action_type == "deliver":
            task = action["task"]
            vehicle.status = VehicleStatus.UNLOADING
            vehicle.remove_task(task)
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
                else:
                    station.join_queue(vehicle)

    def _handle_low_battery(self) -> None:
        """Plan charging for vehicles with low battery."""
        for vehicle in self.fleet:
            if vehicle.status not in [VehicleStatus.IDLE, VehicleStatus.MOVING]:
                continue

            nearest_station = self.map.find_nearest_station(vehicle.current_node)
            if nearest_station is None:
                continue

            dist_to_station = self.map.get_distance(vehicle.current_node, nearest_station)
            consumption_to_station = (
                vehicle.get_consumption_rate() * dist_to_station * 1.5
            )

            if vehicle.current_battery <= consumption_to_station:
                station = next(
                    (s for s in self.charging_stations if s.node_id == nearest_station),
                    None,
                )
                if station:
                    vehicle.action_plan.insert(0, {"type": "move", "target": nearest_station})
                    vehicle.action_plan.insert(1, {"type": "charge", "station_id": station.id})
                    if vehicle.status == VehicleStatus.IDLE:
                        self._execute_next_action(vehicle)

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
        """Check if simulation is complete."""
        total_tasks = self.config.get("task_count", 100)
        completed_or_failed = len(self.completed_tasks) + len(self.failed_tasks)
        all_tasks_processed = completed_or_failed >= total_tasks
        no_active = len(self.active_tasks) == 0
        return all_tasks_processed and no_active

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
```

- [ ] **Step 2: Commit**

```bash
git add backend/simulator/simulator.py
git commit -m "feat(simulator): add main Simulator with tick loop and state management"
```

---

## Phase 5: Web 服务层

### Task 13: Flask + SocketIO 服务

**负责 Agent:** Backend Agent

**Files:**
- Create: `backend/app.py`

- [ ] **Step 1: 编写 app.py**

```python
"""Flask + SocketIO web service for EV Fleet Simulation."""

import os
import threading
from typing import Optional

from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS

from backend.simulator.simulator import Simulator

app = Flask(__name__, static_folder="../frontend")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Global simulator instance and thread
simulator: Optional[Simulator] = None
sim_thread: Optional[threading.Thread] = None


@app.route("/")
def index():
    """Serve frontend main page."""
    return send_from_directory("../frontend", "index.html")


@app.route("/<path:path>")
def serve_static(path):
    """Serve frontend static resources."""
    return send_from_directory("../frontend", path)


@app.route("/api/map", methods=["GET"])
def get_map():
    """Get map configuration data."""
    if simulator and simulator.map:
        return jsonify(simulator.map.to_dict())
    return jsonify({"error": "Simulator not initialized"}), 400


@app.route("/api/config", methods=["POST"])
def initialize_simulation():
    """Initialize simulation environment."""
    global simulator

    config = request.json
    simulator = Simulator(config)
    simulator.initialize(
        map_config=config["map"],
        fleet_config=config["fleet"],
        station_config=config["stations"],
        scheduler_type=config.get("scheduler", "insertion"),
    )

    simulator._emit_state = lambda state: socketio.emit("state_update", state)
    simulator._emit_finished = lambda data: socketio.emit("simulation_finished", data)

    return jsonify({
        "status": "initialized",
        "task_count": len(simulator.event_generator.schedule),
        "map_nodes": len(simulator.map.nodes),
        "fleet_size": len(simulator.fleet),
    })


@app.route("/api/start", methods=["POST"])
def start_simulation():
    """Start simulation in background thread."""
    global sim_thread

    if not simulator:
        return jsonify({"error": "Simulator not initialized"}), 400

    if simulator.running:
        return jsonify({"error": "Simulation already running"}), 400

    def run_sim():
        simulator.run()

    sim_thread = threading.Thread(target=run_sim, daemon=True)
    sim_thread.start()

    return jsonify({"status": "started", "time": simulator.current_time})


@app.route("/api/pause", methods=["POST"])
def pause_simulation():
    """Pause simulation."""
    if simulator:
        simulator.pause()
    return jsonify({"status": "paused"})


@app.route("/api/reset", methods=["POST"])
def reset_simulation():
    """Reset simulation."""
    global simulator, sim_thread

    if simulator:
        simulator.reset()

    if sim_thread and sim_thread.is_alive():
        sim_thread.join(timeout=2.0)

    simulator = None
    sim_thread = None

    return jsonify({"status": "reset"})


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get current statistics."""
    if not simulator:
        return jsonify({"error": "Simulator not initialized"}), 400

    return jsonify({
        "time": simulator.current_time,
        "score": simulator._calculate_score(),
        "completed": len(simulator.completed_tasks),
        "failed": len(simulator.failed_tasks),
        "active": len(simulator.active_tasks),
    })


@socketio.on("connect")
def handle_connect():
    """Client connected."""
    print(f"Client connected: {request.sid}")
    emit("connected", {
        "message": "Connected to EV Fleet Simulation Server",
        "version": "1.0",
    })


@socketio.on("disconnect")
def handle_disconnect():
    """Client disconnected."""
    print(f"Client disconnected: {request.sid}")


@socketio.on("request_state")
def handle_request_state():
    """Client requests current state."""
    if simulator:
        state = simulator._get_state_snapshot(simulator._calculate_score())
        emit("state_update", state)


if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
```

- [ ] **Step 2: 验证后端启动**

```bash
cd /d/Projects/123
python backend/app.py &
```

Expected: Flask 服务器启动，监听端口 5000

```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://0.0.0.0:5000
```

- [ ] **Step 3: 测试 API**

```bash
curl -X POST http://localhost:5000/api/config \
  -H "Content-Type: application/json" \
  -d '{
    "map": {"width": 100, "height": 100, "num_nodes": 30},
    "fleet": [{"id": 1, "start_node": 0, "max_battery": 100, "max_capacity": 50, "consumption_empty": 0.5, "consumption_full": 1.2}],
    "stations": [{"id": 1, "node_id": 10, "total_slots": 3, "charge_rate": 5}],
    "scheduler": "nearest",
    "task_count": 10,
    "time_horizon": 200,
    "sim_speed": 1
  }'
```

Expected: `{"status": "initialized", ...}`

- [ ] **Step 4: Commit**

```bash
git add backend/app.py
git commit -m "feat(api): add Flask + SocketIO web service"
```

---

## Phase 6: 前端基础

### Task 14: HTML 页面结构

**负责 Agent:** Frontend Agent

**Files:**
- Create: `frontend/index.html`

- [ ] **Step 1: 编写 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>新能源物流车队协同调度仿真</title>
    <link rel="stylesheet" href="css/styles.css">
</head>
<body>
    <div class="app-container">
        <header class="header">
            <h1>新能源物流车队协同调度仿真平台</h1>
            <div class="status-bar">
                <span id="sim-time">时间: 0</span>
                <span id="sim-score">得分: 0</span>
                <span id="sim-status">状态: 就绪</span>
            </div>
        </header>

        <div class="main-content">
            <aside class="control-panel">
                <div class="panel-section">
                    <h3>仿真控制</h3>
                    <button id="btn-init" class="btn btn-primary">初始化</button>
                    <button id="btn-start" class="btn btn-success" disabled>开始</button>
                    <button id="btn-pause" class="btn btn-warning" disabled>暂停</button>
                    <button id="btn-reset" class="btn btn-danger">重置</button>
                </div>

                <div class="panel-section">
                    <h3>参数设置</h3>
                    <label>车辆数量: <input type="number" id="config-vehicles" value="10" min="1" max="20"></label>
                    <label>任务数量: <input type="number" id="config-tasks" value="100" min="10" max="500"></label>
                    <label>仿真速度: <input type="range" id="config-speed" value="1" min="0.5" max="10" step="0.5"></label>
                    <label>调度策略:
                        <select id="config-scheduler">
                            <option value="insertion">插入启发式</option>
                            <option value="nearest">最近优先</option>
                            <option value="max_weight">最大重量优先</option>
                        </select>
                    </label>
                </div>

                <div class="panel-section">
                    <h3>实时统计</h3>
                    <div class="stat-item">已完成: <span id="stat-completed">0</span></div>
                    <div class="stat-item">已超时: <span id="stat-failed">0</span></div>
                    <div class="stat-item">待分配: <span id="stat-pending">0</span></div>
                    <div class="stat-item">运输中: <span id="stat-active">0</span></div>
                </div>
            </aside>

            <main class="map-container">
                <canvas id="sim-canvas"></canvas>
                <div class="legend">
                    <div class="legend-item"><span class="icon depot"></span> 仓库</div>
                    <div class="legend-item"><span class="icon station"></span> 充电站</div>
                    <div class="legend-item"><span class="icon pickup"></span> 取货点</div>
                    <div class="legend-item"><span class="icon delivery"></span> 送货点</div>
                    <div class="legend-item"><span class="icon vehicle"></span> 车辆</div>
                </div>
            </main>

            <aside class="info-panel">
                <div class="panel-section">
                    <h3>车辆状态</h3>
                    <div id="vehicle-list" class="scrollable-list"></div>
                </div>
                <div class="panel-section">
                    <h3>任务列表</h3>
                    <div id="task-list" class="scrollable-list"></div>
                </div>
                <div class="panel-section">
                    <h3>充电站状态</h3>
                    <div id="station-list" class="scrollable-list"></div>
                </div>
            </aside>
        </div>

        <footer class="log-panel">
            <h4>运行日志</h4>
            <div id="log-output" class="log-content"></div>
        </footer>
    </div>

    <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
    <script src="js/socket_client.js"></script>
    <script src="js/map_renderer.js"></script>
    <script src="js/vehicle_renderer.js"></script>
    <script src="js/task_renderer.js"></script>
    <script src="js/station_renderer.js"></script>
    <script src="js/ui_controller.js"></script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "feat(frontend): add main HTML page structure"
```

---

### Task 15: CSS 样式

**负责 Agent:** Frontend Agent

**Files:**
- Create: `frontend/css/styles.css`

- [ ] **Step 1: 编写 styles.css**

```css
:root {
    --bg-primary: #1a1a2e;
    --bg-secondary: #16213e;
    --bg-panel: #0f3460;
    --accent: #e94560;
    --success: #00d9ff;
    --warning: #f9a826;
    --text-primary: #eaeaea;
    --text-secondary: #a0a0a0;
    --border: #2d3561;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    overflow: hidden;
    height: 100vh;
}

.app-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 24px;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
}

.header h1 {
    font-size: 1.2rem;
    font-weight: 600;
    color: var(--success);
}

.status-bar {
    display: flex;
    gap: 24px;
    font-size: 0.9rem;
}

.status-bar span {
    padding: 4px 12px;
    background: var(--bg-panel);
    border-radius: 4px;
}

.main-content {
    display: flex;
    flex: 1;
    overflow: hidden;
}

.control-panel, .info-panel {
    width: 260px;
    background: var(--bg-secondary);
    padding: 16px;
    overflow-y: auto;
    border-right: 1px solid var(--border);
    flex-shrink: 0;
}

.info-panel {
    border-right: none;
    border-left: 1px solid var(--border);
}

.panel-section {
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border);
}

.panel-section h3 {
    font-size: 0.9rem;
    margin-bottom: 12px;
    color: var(--success);
    text-transform: uppercase;
    letter-spacing: 1px;
}

.btn {
    width: 100%;
    padding: 10px;
    margin-bottom: 8px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 600;
    transition: all 0.2s;
}

.btn-primary {
    background: var(--bg-panel);
    color: var(--success);
    border: 1px solid var(--success);
}

.btn-success {
    background: #0d7377;
    color: white;
}

.btn-warning {
    background: var(--warning);
    color: var(--bg-primary);
}

.btn-danger {
    background: var(--accent);
    color: white;
}

.btn:hover {
    opacity: 0.85;
    transform: translateY(-1px);
}

.btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
}

label {
    display: block;
    margin-bottom: 12px;
    font-size: 0.85rem;
    color: var(--text-secondary);
}

input, select {
    width: 100%;
    padding: 6px;
    margin-top: 4px;
    background: var(--bg-primary);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text-primary);
}

.map-container {
    flex: 1;
    position: relative;
    background: #0d1b2a;
    overflow: hidden;
}

#sim-canvas {
    width: 100%;
    height: 100%;
    display: block;
}

.legend {
    position: absolute;
    top: 16px;
    right: 16px;
    background: rgba(22, 33, 62, 0.9);
    padding: 12px;
    border-radius: 8px;
    font-size: 0.8rem;
    backdrop-filter: blur(4px);
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}

.icon {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    display: inline-block;
}

.icon.depot {
    background: #ffd700;
    box-shadow: 0 0 6px #ffd700;
}

.icon.station {
    background: #00ff88;
}

.icon.pickup {
    background: var(--warning);
}

.icon.delivery {
    background: var(--accent);
}

.icon.vehicle {
    background: var(--success);
}

.stat-item {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    font-size: 0.85rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.scrollable-list {
    max-height: 200px;
    overflow-y: auto;
    font-size: 0.8rem;
}

.scrollable-list::-webkit-scrollbar {
    width: 4px;
}

.scrollable-list::-webkit-scrollbar-thumb {
    background: var(--border);
    border-radius: 2px;
}

.log-panel {
    height: 120px;
    background: var(--bg-secondary);
    border-top: 1px solid var(--border);
    padding: 12px 24px;
    flex-shrink: 0;
}

.log-panel h4 {
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-bottom: 8px;
}

.log-content {
    height: 80px;
    overflow-y: auto;
    font-family: 'Consolas', monospace;
    font-size: 0.75rem;
    color: var(--text-secondary);
    line-height: 1.6;
}

.list-item {
    padding: 4px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    display: flex;
    justify-content: space-between;
}

.list-item .badge {
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 0.7rem;
}

.badge-pending { background: var(--warning); color: #000; }
.badge-assigned { background: var(--success); color: #000; }
.badge-completed { background: #00ff88; color: #000; }
.badge-timeout { background: var(--accent); color: #fff; }
```

- [ ] **Step 2: Commit**

```bash
git add frontend/css/styles.css
git commit -m "feat(frontend): add dark theme CSS with grid layout"
```

---

## Phase 7: 前端 JavaScript

### Task 16: Socket.IO 客户端

**负责 Agent:** Frontend Agent

**Files:**
- Create: `frontend/js/socket_client.js`

- [ ] **Step 1: 编写 SocketClient**

```javascript
/**
 * SocketClient - WebSocket wrapper using Socket.IO
 */
class SocketClient {
    constructor(serverUrl = 'http://localhost:5000') {
        this.socket = io(serverUrl);
        this.callbacks = {};
        this.connected = false;
        this.setupListeners();
    }

    setupListeners() {
        this.socket.on('connect', () => {
            console.log('Connected to simulation server');
            this.connected = true;
            this.trigger('connected', {});
        });

        this.socket.on('state_update', (state) => {
            this.trigger('state_update', state);
        });

        this.socket.on('simulation_finished', (data) => {
            this.trigger('finished', data);
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.connected = false;
            this.trigger('disconnected', {});
        });

        this.socket.on('error', (error) => {
            console.error('Socket error:', error);
            this.trigger('error', error);
        });
    }

    on(event, callback) {
        if (!this.callbacks[event]) {
            this.callbacks[event] = [];
        }
        this.callbacks[event].push(callback);
    }

    trigger(event, data) {
        if (this.callbacks[event]) {
            this.callbacks[event].forEach(cb => cb(data));
        }
    }

    requestState() {
        this.socket.emit('request_state');
    }

    disconnect() {
        this.socket.disconnect();
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/socket_client.js
git commit -m "feat(frontend): add Socket.IO client wrapper"
```

---

### Task 17: 地图渲染器

**负责 Agent:** Frontend Agent

**Files:**
- Create: `frontend/js/map_renderer.js`

- [ ] **Step 1: 编写 MapRenderer**

```javascript
/**
 * MapRenderer - Renders road network, nodes and grid background
 */
class MapRenderer {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.nodes = [];
        this.edges = [];
        this.scale = 1;
        this.offsetX = 0;
        this.offsetY = 0;
        this.padding = 40;
        this.setupCanvas();
    }

    setupCanvas() {
        const resize = () => {
            const rect = this.canvas.parentElement.getBoundingClientRect();
            this.canvas.width = rect.width;
            this.canvas.height = rect.height;
            if (this.nodes.length > 0) {
                this.fitToView();
            }
        };
        window.addEventListener('resize', resize);
        resize();
    }

    setMapData(nodes, edges) {
        this.nodes = nodes;
        this.edges = edges;
        this.fitToView();
    }

    fitToView() {
        if (this.nodes.length === 0) return;

        const xs = this.nodes.map(n => n.x);
        const ys = this.nodes.map(n => n.y);
        const minX = Math.min(...xs);
        const maxX = Math.max(...xs);
        const minY = Math.min(...ys);
        const maxY = Math.max(...ys);

        const mapWidth = maxX - minX || 1;
        const mapHeight = maxY - minY || 1;

        const scaleX = (this.canvas.width - this.padding * 2) / mapWidth;
        const scaleY = (this.canvas.height - this.padding * 2) / mapHeight;
        this.scale = Math.min(scaleX, scaleY);

        this.offsetX = this.padding - minX * this.scale;
        this.offsetY = this.padding - minY * this.scale;
    }

    render() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.drawGrid();
        this.drawRoads();
        this.drawNodes();
    }

    drawGrid() {
        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
        this.ctx.lineWidth = 1;
        const gridSize = 30;

        for (let x = 0; x < this.canvas.width; x += gridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.canvas.height);
            this.ctx.stroke();
        }
        for (let y = 0; y < this.canvas.height; y += gridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.canvas.width, y);
            this.ctx.stroke();
        }
    }

    drawRoads() {
        this.ctx.strokeStyle = 'rgba(100, 150, 200, 0.3)';
        this.ctx.lineWidth = 2;

        for (const edge of this.edges) {
            const u = this.nodes.find(n => n.id === edge.u);
            const v = this.nodes.find(n => n.id === edge.v);
            if (u && v) {
                const posU = this.worldToScreen(u.x, u.y);
                const posV = this.worldToScreen(v.x, v.y);

                this.ctx.beginPath();
                this.ctx.moveTo(posU.x, posU.y);
                this.ctx.lineTo(posV.x, posV.y);
                this.ctx.stroke();
            }
        }
    }

    drawNodes() {
        for (const node of this.nodes) {
            const pos = this.worldToScreen(node.x, node.y);
            const radius = node.type === 'depot' ? 10 : 6;

            this.ctx.save();

            switch (node.type) {
                case 'depot':
                    this.ctx.fillStyle = '#ffd700';
                    this.ctx.shadowColor = '#ffd700';
                    this.ctx.shadowBlur = 15;
                    break;
                case 'station':
                    this.ctx.fillStyle = '#00ff88';
                    this.ctx.shadowColor = '#00ff88';
                    this.ctx.shadowBlur = 10;
                    break;
                default:
                    this.ctx.fillStyle = '#4a5568';
                    this.ctx.shadowBlur = 0;
            }

            this.ctx.beginPath();
            this.ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
            this.ctx.fill();

            this.ctx.restore();
        }
    }

    worldToScreen(x, y) {
        return {
            x: x * this.scale + this.offsetX,
            y: y * this.scale + this.offsetY
        };
    }

    screenToWorld(screenX, screenY) {
        return {
            x: (screenX - this.offsetX) / this.scale,
            y: (screenY - this.offsetY) / this.scale
        };
    }

    getNodePosition(nodeId) {
        const node = this.nodes.find(n => n.id === nodeId);
        return node ? [node.x, node.y] : [0, 0];
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/map_renderer.js
git commit -m "feat(frontend): add MapRenderer with grid, roads and nodes"
```

---

### Task 18: 车辆渲染器

**负责 Agent:** Frontend Agent

**Files:**
- Create: `frontend/js/vehicle_renderer.js`

- [ ] **Step 1: 编写 VehicleRenderer**

```javascript
/**
 * VehicleRenderer - Renders vehicles, paths and battery indicators
 */
class VehicleRenderer {
    constructor(ctx, mapRenderer) {
        this.ctx = ctx;
        this.mapRenderer = mapRenderer;
        this.vehicles = [];
    }

    updateVehicles(vehicleData) {
        this.vehicles = vehicleData;
    }

    render() {
        for (const vehicle of this.vehicles) {
            this.drawPath(vehicle);
        }
        for (const vehicle of this.vehicles) {
            this.drawVehicle(vehicle);
        }
    }

    drawVehicle(vehicle) {
        const pos = this.mapRenderer.worldToScreen(
            vehicle.position[0],
            vehicle.position[1]
        );

        this.ctx.save();

        // Battery indicator ring
        const batteryPct = vehicle.battery_pct;
        const batteryColor = batteryPct > 0.3 ? '#00d9ff' :
                            batteryPct > 0.1 ? '#f9a826' : '#e94560';

        this.ctx.strokeStyle = batteryColor;
        this.ctx.lineWidth = 3;
        this.ctx.beginPath();
        this.ctx.arc(pos.x, pos.y, 16, -Math.PI / 2,
                     -Math.PI / 2 + Math.PI * 2 * batteryPct);
        this.ctx.stroke();

        // Vehicle body
        this.ctx.fillStyle = '#00d9ff';
        this.ctx.shadowBlur = 15;
        this.ctx.shadowColor = '#00d9ff';
        this.ctx.beginPath();
        this.ctx.arc(pos.x, pos.y, 12, 0, Math.PI * 2);
        this.ctx.fill();

        // Load indicator
        if (vehicle.load_pct > 0) {
            this.ctx.fillStyle = `rgba(233, 69, 96, ${vehicle.load_pct * 0.6})`;
            this.ctx.beginPath();
            this.ctx.arc(pos.x, pos.y, 8, 0, Math.PI * 2);
            this.ctx.fill();
        }

        // Vehicle ID
        this.ctx.fillStyle = '#1a1a2e';
        this.ctx.font = 'bold 10px sans-serif';
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        this.ctx.shadowBlur = 0;
        this.ctx.fillText(vehicle.id, pos.x, pos.y);

        this.ctx.restore();
    }

    drawPath(vehicle) {
        if (!vehicle.path || vehicle.path.length < 2) return;

        this.ctx.save();
        this.ctx.strokeStyle = 'rgba(0, 217, 255, 0.12)';
        this.ctx.lineWidth = 2;
        this.ctx.setLineDash([5, 5]);

        this.ctx.beginPath();
        const start = this.mapRenderer.worldToScreen(
            ...this.mapRenderer.getNodePosition(vehicle.path[0])
        );
        this.ctx.moveTo(start.x, start.y);

        for (let i = 1; i < vehicle.path.length; i++) {
            const pos = this.mapRenderer.worldToScreen(
                ...this.mapRenderer.getNodePosition(vehicle.path[i])
            );
            this.ctx.lineTo(pos.x, pos.y);
        }

        this.ctx.stroke();
        this.ctx.restore();
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/vehicle_renderer.js
git commit -m "feat(frontend): add VehicleRenderer with battery ring and path"
```

---

### Task 19: 任务渲染器

**负责 Agent:** Frontend Agent

**Files:**
- Create: `frontend/js/task_renderer.js`

- [ ] **Step 1: 编写 TaskRenderer**

```javascript
/**
 * TaskRenderer - Renders task markers (pickup/delivery points)
 */
class TaskRenderer {
    constructor(ctx, mapRenderer) {
        this.ctx = ctx;
        this.mapRenderer = mapRenderer;
        this.tasks = [];
    }

    updateTasks(taskData) {
        this.tasks = taskData;
    }

    render() {
        for (const task of this.tasks) {
            if (task.status === 'completed') continue;
            this.drawTaskMarker(task);
        }
    }

    drawTaskMarker(task) {
        const pickupPos = this.mapRenderer.worldToScreen(
            ...this.mapRenderer.getNodePosition(task.pickup)
        );
        const deliveryPos = this.mapRenderer.worldToScreen(
            ...this.mapRenderer.getNodePosition(task.delivery)
        );

        this.ctx.save();

        // Pickup - orange triangle
        if (task.status === 'pending' || task.status === 'assigned') {
            this.ctx.fillStyle = '#f9a826';
            this.ctx.shadowBlur = 8;
            this.ctx.shadowColor = '#f9a826';
            this.drawTriangle(pickupPos.x, pickupPos.y, 8);
        }

        // Delivery - red square
        if (task.status !== 'completed') {
            this.ctx.fillStyle = '#e94560';
            this.ctx.shadowBlur = 8;
            this.ctx.shadowColor = '#e94560';
            this.ctx.fillRect(deliveryPos.x - 6, deliveryPos.y - 6, 12, 12);
        }

        // Connection line for assigned tasks
        if (task.status !== 'pending' && task.status !== 'completed') {
            this.ctx.strokeStyle = 'rgba(249, 168, 38, 0.2)';
            this.ctx.lineWidth = 1;
            this.ctx.setLineDash([3, 3]);
            this.ctx.beginPath();
            this.ctx.moveTo(pickupPos.x, pickupPos.y);
            this.ctx.lineTo(deliveryPos.x, deliveryPos.y);
            this.ctx.stroke();
        }

        this.ctx.restore();
    }

    drawTriangle(x, y, size) {
        this.ctx.beginPath();
        this.ctx.moveTo(x, y - size);
        this.ctx.lineTo(x - size, y + size);
        this.ctx.lineTo(x + size, y + size);
        this.ctx.closePath();
        this.ctx.fill();
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/task_renderer.js
git commit -m "feat(frontend): add TaskRenderer with pickup/delivery markers"
```

---

### Task 20: 充电站渲染器

**负责 Agent:** Frontend Agent

**Files:**
- Create: `frontend/js/station_renderer.js`

- [ ] **Step 1: 编写 StationRenderer**

```javascript
/**
 * StationRenderer - Renders charging stations with occupancy info
 */
class StationRenderer {
    constructor(ctx, mapRenderer) {
        this.ctx = ctx;
        this.mapRenderer = mapRenderer;
        this.stations = [];
    }

    updateStations(stationData) {
        this.stations = stationData;
    }

    render() {
        for (const station of this.stations) {
            this.drawStation(station);
        }
    }

    drawStation(station) {
        const nodePos = this.mapRenderer.worldToScreen(
            ...this.mapRenderer.getNodePosition(station.node)
        );

        this.ctx.save();

        // Outer ring - capacity indicator
        const capacityPct = station.occupied / station.total;
        this.ctx.strokeStyle = capacityPct > 0.8 ? '#e94560' : '#00ff88';
        this.ctx.lineWidth = 4;
        this.ctx.beginPath();
        this.ctx.arc(nodePos.x, nodePos.y, 20, 0, Math.PI * 2);
        this.ctx.stroke();

        // Fill occupancy
        this.ctx.fillStyle = `rgba(0, 255, 136, ${capacityPct * 0.3})`;
        this.ctx.beginPath();
        this.ctx.arc(nodePos.x, nodePos.y, 20, 0, Math.PI * 2);
        this.ctx.fill();

        // Queue count
        if (station.queue > 0) {
            this.ctx.fillStyle = '#f9a826';
            this.ctx.font = 'bold 12px sans-serif';
            this.ctx.textAlign = 'center';
            this.ctx.fillText(
                `+${station.queue}`,
                nodePos.x,
                nodePos.y - 25
            );
        }

        // Slot count
        this.ctx.fillStyle = '#fff';
        this.ctx.font = '10px sans-serif';
        this.ctx.textAlign = 'center';
        this.ctx.fillText(
            `${station.occupied}/${station.total}`,
            nodePos.x,
            nodePos.y + 4
        );

        this.ctx.restore();
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/station_renderer.js
git commit -m "feat(frontend): add StationRenderer with occupancy ring"
```

---

### Task 21: UI 控制器

**负责 Agent:** Frontend Agent

**Files:**
- Create: `frontend/js/ui_controller.js`

- [ ] **Step 1: 编写 UIController**

```javascript
/**
 * UIController - Main UI logic, event handling and render loop
 */
class UIController {
    constructor() {
        this.socketClient = new SocketClient();
        this.mapRenderer = new MapRenderer(document.getElementById('sim-canvas'));
        this.vehicleRenderer = new VehicleRenderer(
            this.mapRenderer.ctx,
            this.mapRenderer
        );
        this.taskRenderer = new TaskRenderer(
            this.mapRenderer.ctx,
            this.mapRenderer
        );
        this.stationRenderer = new StationRenderer(
            this.mapRenderer.ctx,
            this.mapRenderer
        );

        this.isRunning = false;
        this.animationId = null;

        this.setupEventListeners();
        this.setupSocketListeners();
    }

    setupEventListeners() {
        document.getElementById('btn-init').addEventListener('click', () => this.initialize());
        document.getElementById('btn-start').addEventListener('click', () => this.start());
        document.getElementById('btn-pause').addEventListener('click', () => this.pause());
        document.getElementById('btn-reset').addEventListener('click', () => this.reset());
    }

    setupSocketListeners() {
        this.socketClient.on('connected', () => {
            this.log('已连接到仿真服务器');
        });

        this.socketClient.on('state_update', (state) => {
            this.updateUI(state);
        });

        this.socketClient.on('finished', (data) => {
            this.isRunning = false;
            this.log(`仿真结束！最终得分: ${data.final_score.toFixed(1)}`);
            document.getElementById('btn-start').disabled = false;
            document.getElementById('btn-pause').disabled = true;
            this.stopRenderLoop();
        });

        this.socketClient.on('disconnected', () => {
            this.log('与服务器断开连接');
        });
    }

    async initialize() {
        const numVehicles = parseInt(document.getElementById('config-vehicles').value);
        const fleet = Array.from({length: numVehicles}, (_, i) => ({
            id: i + 1,
            start_node: 0,
            max_battery: 100,
            max_capacity: 50,
            consumption_empty: 0.5,
            consumption_full: 1.2
        }));

        const config = {
            map: {width: 100, height: 100, num_nodes: 50},
            fleet: fleet,
            stations: [
                {id: 1, node_id: 10, total_slots: 3, charge_rate: 5},
                {id: 2, node_id: 25, total_slots: 3, charge_rate: 5},
                {id: 3, node_id: 40, total_slots: 2, charge_rate: 8}
            ],
            scheduler: document.getElementById('config-scheduler').value,
            task_count: parseInt(document.getElementById('config-tasks').value),
            time_horizon: 2000,
            tick_interval: 1,
            sim_speed: parseFloat(document.getElementById('config-speed').value)
        };

        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            });
            const data = await response.json();

            if (data.status === 'initialized') {
                this.log(`仿真初始化完成，预生成 ${data.task_count} 个任务`);
                document.getElementById('btn-start').disabled = false;

                const mapResponse = await fetch('/api/map');
                const mapData = await mapResponse.json();
                this.mapRenderer.setMapData(mapData.nodes, mapData.edges);
                this.render();
            }
        } catch (error) {
            this.log(`初始化失败: ${error.message}`);
        }
    }

    async start() {
        try {
            await fetch('/api/start', {method: 'POST'});
            this.isRunning = true;
            this.log('仿真开始运行');
            document.getElementById('btn-start').disabled = true;
            document.getElementById('btn-pause').disabled = false;
            this.startRenderLoop();
        } catch (error) {
            this.log(`启动失败: ${error.message}`);
        }
    }

    async pause() {
        try {
            await fetch('/api/pause', {method: 'POST'});
            this.isRunning = false;
            this.log('仿真已暂停');
            document.getElementById('btn-start').disabled = false;
            document.getElementById('btn-pause').disabled = true;
            this.stopRenderLoop();
        } catch (error) {
            this.log(`暂停失败: ${error.message}`);
        }
    }

    async reset() {
        try {
            await fetch('/api/reset', {method: 'POST'});
            this.isRunning = false;
            this.stopRenderLoop();
            this.log('仿真已重置');
            document.getElementById('btn-start').disabled = true;
            document.getElementById('btn-pause').disabled = true;

            this.vehicleRenderer.updateVehicles([]);
            this.taskRenderer.updateTasks([]);
            this.stationRenderer.updateStations([]);
            this.updateStats({completed: 0, failed: 0, pending: 0, active: 0});
            this.clearLists();
            this.mapRenderer.render();
        } catch (error) {
            this.log(`重置失败: ${error.message}`);
        }
    }

    updateUI(state) {
        document.getElementById('sim-time').textContent = `时间: ${state.time}`;
        document.getElementById('sim-score').textContent = `得分: ${state.score.toFixed(1)}`;
        document.getElementById('sim-status').textContent = `状态: ${this.isRunning ? '运行中' : '暂停'}`;

        this.updateStats(state.stats);
        this.updateLists(state);

        this.vehicleRenderer.updateVehicles(state.vehicles);
        this.taskRenderer.updateTasks(state.tasks);
        this.stationRenderer.updateStations(state.stations);
    }

    updateStats(stats) {
        document.getElementById('stat-completed').textContent = stats.completed || 0;
        document.getElementById('stat-failed').textContent = stats.failed || 0;
        document.getElementById('stat-pending').textContent = stats.pending || 0;
        document.getElementById('stat-active').textContent = stats.active || 0;
    }

    updateLists(state) {
        // Vehicle list
        const vehicleList = document.getElementById('vehicle-list');
        vehicleList.innerHTML = state.vehicles.map(v => `
            <div class="list-item">
                <span>车辆 ${v.id}</span>
                <span class="badge badge-${v.status}">${v.status}</span>
            </div>
        `).join('');

        // Task list (show last 10)
        const taskList = document.getElementById('task-list');
        const recentTasks = state.tasks.slice(-10);
        taskList.innerHTML = recentTasks.map(t => `
            <div class="list-item">
                <span>任务 ${t.id}</span>
                <span class="badge badge-${t.status}">${t.status}</span>
            </div>
        `).join('');

        // Station list
        const stationList = document.getElementById('station-list');
        stationList.innerHTML = state.stations.map(s => `
            <div class="list-item">
                <span>充电站 ${s.id}</span>
                <span>${s.occupied}/${s.total} (+${s.queue})</span>
            </div>
        `).join('');
    }

    clearLists() {
        document.getElementById('vehicle-list').innerHTML = '';
        document.getElementById('task-list').innerHTML = '';
        document.getElementById('station-list').innerHTML = '';
    }

    startRenderLoop() {
        const loop = () => {
            if (!this.isRunning) return;
            this.render();
            this.animationId = requestAnimationFrame(loop);
        };
        loop();
    }

    stopRenderLoop() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }

    render() {
        this.mapRenderer.render();
        this.vehicleRenderer.render();
        this.taskRenderer.render();
        this.stationRenderer.render();
    }

    log(message) {
        const logOutput = document.getElementById('log-output');
        const entry = document.createElement('div');
        entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        logOutput.appendChild(entry);
        logOutput.scrollTop = logOutput.scrollHeight;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    new UIController();
});
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/ui_controller.js
git commit -m "feat(frontend): add UIController with render loop and event handling"
```

---

## Phase 8: 集成与验证

### Task 22: 端到端测试

**负责 Agent:** Integration Agent

**Files:**
- Modify: `backend/app.py` (if needed)

- [ ] **Step 1: 启动后端服务**

```bash
cd /d/Projects/123
python backend/app.py
```

Expected: 服务启动在 http://localhost:5000

- [ ] **Step 2: 浏览器访问并测试**

打开浏览器访问 `http://localhost:5000`

测试步骤:
1. 点击"初始化"按钮
2. 确认地图渲染（网格、节点、道路）
3. 点击"开始"按钮
4. 观察车辆移动、任务生成、状态更新
5. 观察实时统计数据变化
6. 点击"暂停"按钮
7. 点击"重置"按钮

- [ ] **Step 3: 验证 WebSocket 实时推送**

浏览器控制台应显示:
```
Connected to simulation server
[state updates flowing...]
```

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "test: verify end-to-end simulation with WebSocket"
```

---

## 附录: Self-Review Checklist

### Spec Coverage
- [x] Task model with status and scoring
- [x] Vehicle model with battery, load, consumption
- [x] ChargingStation with queue and slots
- [x] TransportMap with grid generation and pathfinding
- [x] BaseScheduler interface
- [x] NearestFirst scheduler
- [x] MaxWeight scheduler
- [x] Insertion scheduler
- [x] EventGenerator for dynamic tasks
- [x] Simulator with tick loop
- [x] Flask REST API
- [x] Socket.IO WebSocket events
- [x] HTML structure
- [x] CSS dark theme
- [x] Canvas renderers (map, vehicle, task, station)
- [x] UI controller with render loop

### Placeholder Scan
- [x] No "TBD", "TODO" in code
- [x] No vague "implement later" statements
- [x] All functions have complete signatures
- [x] All test commands are explicit

### Type Consistency
- [x] `Vehicle.to_dict()` format matches frontend expectations
- [x] `Task.to_dict()` format matches frontend expectations
- [x] `ChargingStation.to_dict()` format matches frontend expectations
- [x] `TransportMap.to_dict()` format matches frontend expectations
- [x] WebSocket `state_update` event format consistent across backend/frontend
- [x] REST API response formats consistent

---

## 执行选项

Plan complete and saved to `docs/superpowers/plans/2026-05-26-ev-fleet-scheduler-plan.md`.

**Two execution options:**

**1. Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration. Use `superpowers:subagent-driven-development` skill.

**2. Inline Execution** - Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints for review.

**Which approach?**
