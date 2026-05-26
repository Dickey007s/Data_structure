# 新能源物流车队协同调度仿真平台 - 系统设计文档

> 版本: v1.0 | 日期: 2026-05-26 | 状态: 已确认

---

## 1. 项目概述

### 1.1 项目背景
基于 2026 大作业要求，构建一个新能源物流车队协同调度仿真系统。系统模拟 10 辆新能源车辆在城市路网中执行约 100 个动态生成的送货任务，支持多种调度策略，提供实时可视化展示。

### 1.2 核心需求
- **车辆约束**: 10 辆车，每辆有电量上限、载重上限、耗电率（空载/满载）
- **任务约束**: 约 100 个任务动态生成，每个任务包含取货点、送货点、货物重量、时间窗
- **充电站**: 多个充电站，支持排队与负荷管理
- **调度策略**: 至少实现 3 种策略（最近优先、最大重量优先、插入启发式）
- **实时可视化**: WebSocket 推送仿真状态，Canvas 实时渲染车辆轨迹
- **评分系统**: 完成时间越早、路径越短，得分越高；超时扣分

### 1.3 技术栈
| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11 + Flask + Flask-SocketIO + NetworkX + NumPy |
| 前端 | HTML5 + CSS3 + Vanilla JavaScript + Canvas 2D API |
| 通信 | WebSocket (Socket.IO) + REST API |
| 仿真 | 离散时间步进 (tick-based) |

---

## 2. 系统架构

### 2.1 总体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层 (Frontend)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ UI 控制面板  │  │ Canvas 渲染器 │  │ Socket.IO 客户端    │  │
│  │ (ui_controller)│ (map/vehicle/ │  │ (socket_client)     │  │
│  │             │  │ task/station) │  │                     │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                    │             │
│         └────────────────┴────────────────────┘             │
│                          │                                  │
│                    HTTP / WebSocket                         │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────┐
│                        后端层 (Backend)                       │
│  ┌───────────────────────┼──────────────────────────────┐   │
│  │     Web 服务层         │  (app.py)                    │   │
│  │  Flask Routes + SocketIO Events                      │   │
│  └───────────────────────┼──────────────────────────────┘   │
│                          │                                   │
│  ┌───────────────────────┼──────────────────────────────┐   │
│  │     仿真引擎层         │  (simulator/)                │   │
│  │  Simulator + EventGenerator + Scoring               │   │
│  └───────────────────────┼──────────────────────────────┘   │
│                          │                                   │
│  ┌───────────────────────┼──────────────────────────────┐   │
│  │     调度策略层         │  (scheduler/)                │   │
│  │  BaseScheduler + NearestFirst + MaxWeight + Insertion│   │
│  └───────────────────────┼──────────────────────────────┘   │
│                          │                                   │
│  ┌───────────────────────┼──────────────────────────────┐   │
│  │     核心数据模型       │  (models/)                   │   │
│  │  Task + Vehicle + ChargingStation + TransportMap    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 目录结构

```
123/
├── backend/
│   ├── __init__.py
│   ├── app.py                    # Flask + SocketIO 服务入口
│   ├── models/
│   │   ├── __init__.py
│   │   ├── task.py              # Task 类
│   │   ├── vehicle.py           # Vehicle 类 + VehicleStatus 枚举
│   │   ├── charging_station.py  # ChargingStation 类
│   │   └── transport_map.py     # TransportMap 类 (图结构)
│   ├── scheduler/
│   │   ├── __init__.py
│   │   ├── base_scheduler.py    # 调度器抽象基类
│   │   ├── nearest_first_scheduler.py
│   │   ├── max_weight_scheduler.py
│   │   └── insertion_scheduler.py
│   ├── simulator/
│   │   ├── __init__.py
│   │   ├── simulator.py         # 主仿真引擎
│   │   ├── event_generator.py   # 动态任务生成器
│   │   └── scoring.py           # 评分系统
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── styles.css
│   └── js/
│       ├── socket_client.js     # WebSocket 客户端封装
│       ├── map_renderer.js      # 地图/道路/节点渲染
│       ├── vehicle_renderer.js  # 车辆/轨迹/电量渲染
│       ├── task_renderer.js     # 任务标记渲染
│       ├── station_renderer.js  # 充电站状态渲染
│       └── ui_controller.js     # UI 逻辑与事件绑定
└── docs/
    └── specs/
        └── 2026-05-26-ev-fleet-scheduler-design.md
```

---

## 3. 核心数据模型 (backend/models/)

### 3.1 Task (任务)

```python
class Task:
    STATUS_PENDING = "pending"
    STATUS_ASSIGNED = "assigned"
    STATUS_PICKING = "picking"
    STATUS_DELIVERING = "delivering"
    STATUS_COMPLETED = "completed"
    STATUS_TIMEOUT = "timeout"
    
    def __init__(self, id: int, pickup_node: int, delivery_node: int, 
                 weight: float, ready_time: int, due_time: int, 
                 create_time: int):
        self.id = id
        self.pickup_node = pickup_node          # 取货节点 ID
        self.delivery_node = delivery_node      # 送货节点 ID
        self.weight = weight                    # 货物重量
        self.ready_time = ready_time            # 最早可取货时间
        self.due_time = due_time                # 最晚送达时间
        self.create_time = create_time          # 任务生成时间
        self.status = self.STATUS_PENDING       # 当前状态
        self.assigned_vehicle = None            # 分配的车辆 ID
        self.completed_time = None              # 完成时间
    
    def is_timeout(self, current_time: int) -> bool:
        """检查任务是否已超时"""
        return (current_time > self.due_time and 
                self.status != self.STATUS_COMPLETED)
    
    def get_score(self) -> float:
        """计算任务完成得分（完成时调用）"""
        if self.status == self.STATUS_COMPLETED:
            time_bonus = max(0, self.due_time - self.completed_time)
            return 100.0 + time_bonus
        elif self.status == self.STATUS_TIMEOUT:
            return -50.0
        return 0.0
```

### 3.2 Vehicle (车辆)

```python
from enum import Enum

class VehicleStatus(Enum):
    IDLE = "idle"               # 空闲
    MOVING = "moving"           # 移动中
    CHARGING = "charging"       # 充电中
    LOADING = "loading"         # 取货中
    UNLOADING = "unloading"     # 送货中
    WAITING_CHARGE = "waiting_charge"  # 等待充电

class Vehicle:
    def __init__(self, id: int, start_node: int, max_battery: float, 
                 max_capacity: float, consumption_empty: float, 
                 consumption_full: float):
        self.id = id
        self.start_node = start_node
        self.current_node = start_node
        self.max_battery = max_battery
        self.current_battery = max_battery
        self.max_capacity = max_capacity
        self.current_load = 0.0
        self.consumption_empty = consumption_empty   # 空载耗电率
        self.consumption_full = consumption_full     # 满载耗电率
        self.status = VehicleStatus.IDLE
        self.action_plan = []          # List[Action] 动作序列
        self.carrying_tasks = []       # List[Task] 当前载运的任务
        self.current_path_nodes = []   # List[int] 当前路径节点列表
        self.current_path_index = 0    # 当前路段索引
        self.position = (0.0, 0.0)     # (x, y) 世界坐标
        self.target_position = (0.0, 0.0)
        self.progress = 0.0            # 0.0 ~ 1.0 当前路段进度
    
    def get_consumption_rate(self) -> float:
        """根据当前载重计算单位距离耗电率"""
        load_ratio = (self.current_load / self.max_capacity 
                      if self.max_capacity > 0 else 0)
        return (self.consumption_empty + 
                (self.consumption_full - self.consumption_empty) * load_ratio)
    
    def move(self, distance: float) -> None:
        """移动指定距离，扣除电量"""
        consumption = self.get_consumption_rate() * distance
        self.current_battery = max(0, self.current_battery - consumption)
    
    def can_carry(self, weight: float) -> bool:
        """检查是否还能装载指定重量"""
        return self.current_load + weight <= self.max_capacity
    
    def add_task(self, task: Task) -> bool:
        """添加任务到载重列表"""
        if self.can_carry(task.weight):
            self.carrying_tasks.append(task)
            self.current_load += task.weight
            return True
        return False
    
    def remove_task(self, task: Task) -> None:
        """移除已完成的任务，减少载重"""
        if task in self.carrying_tasks:
            self.carrying_tasks.remove(task)
            self.current_load -= task.weight
            self.current_load = max(0, self.current_load)
    
    def needs_charging(self, map_obj, safety_margin: float = 1.3) -> bool:
        """检查当前电量是否足以继续执行计划（含安全余量）"""
        pass  # 具体实现依赖地图和路径规划
    
    def to_dict(self) -> dict:
        """序列化为字典（用于 JSON/前端传输）"""
        return {
            'id': self.id,
            'node': self.current_node,
            'position': self.position,
            'battery': round(self.current_battery, 2),
            'battery_pct': round(self.current_battery / self.max_battery, 3),
            'load': round(self.current_load, 2),
            'load_pct': round(self.current_load / self.max_capacity, 3) 
                        if self.max_capacity > 0 else 0,
            'status': self.status.value,
            'path': self.current_path_nodes,
            'carrying': [t.id for t in self.carrying_tasks]
        }
```

### 3.3 ChargingStation (充电站)

```python
class ChargingStation:
    def __init__(self, id: int, node_id: int, total_slots: int, 
                 charge_rate: float):
        self.id = id
        self.node_id = node_id              # 所在节点
        self.total_slots = total_slots      # 总充电桩数
        self.occupied_slots = 0             # 已占用数
        self.charge_rate = charge_rate      # 每 tick 充电量 (kWh)
        self.waiting_queue = []             # 等待队列 List[Vehicle]
        self.charging_vehicles = []         # 正在充电 [(Vehicle, start_time)]
    
    def is_available(self) -> bool:
        """是否有空闲充电桩"""
        return self.occupied_slots < self.total_slots
    
    def is_full(self) -> bool:
        """是否已满"""
        return self.occupied_slots >= self.total_slots
    
    def join_queue(self, vehicle) -> None:
        """车辆加入等待队列"""
        if vehicle not in self.waiting_queue:
            self.waiting_queue.append(vehicle)
            vehicle.status = VehicleStatus.WAITING_CHARGE
    
    def start_charging(self, vehicle) -> bool:
        """开始充电，返回是否成功"""
        if self.is_available():
            self.occupied_slots += 1
            self.charging_vehicles.append((vehicle, 0))
            vehicle.status = VehicleStatus.CHARGING
            return True
        return False
    
    def tick(self, dt: float) -> List[Vehicle]:
        """推进充电状态，返回已完成充电的车辆列表"""
        completed = []
        
        # 为每辆充电车辆增加电量
        for i, (vehicle, _) in enumerate(self.charging_vehicles):
            vehicle.current_battery = min(
                vehicle.max_battery,
                vehicle.current_battery + self.charge_rate * dt
            )
            # 检查是否充满
            if vehicle.current_battery >= vehicle.max_battery:
                vehicle.current_battery = vehicle.max_battery
                completed.append(vehicle)
        
        # 移除已充满的车辆
        self.charging_vehicles = [
            (v, t) for v, t in self.charging_vehicles 
            if v.current_battery < v.max_battery
        ]
        self.occupied_slots = len(self.charging_vehicles)
        
        # 从队列中补充新车辆
        while self.waiting_queue and self.is_available():
            vehicle = self.waiting_queue.pop(0)
            self.start_charging(vehicle)
        
        return completed
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'node': self.node_id,
            'occupied': self.occupied_slots,
            'total': self.total_slots,
            'queue': len(self.waiting_queue)
        }
```

### 3.4 TransportMap (路网地图)

```python
import networkx as nx
from typing import List, Tuple, Dict

class TransportMap:
    def __init__(self, width: int, height: int, grid_type: str = "hex"):
        self.graph = nx.Graph()
        self.nodes: Dict[int, Tuple[float, float, str]] = {}  # id -> (x, y, type)
        self.dist_matrix: Dict[Tuple[int, int], float] = {}
        self.width = width          # 世界坐标宽度
        self.height = height        # 世界坐标高度
        self.grid_type = grid_type  # "hex" (六边形) 或 "square" (正方形)
        self.depot_node = 0         # 仓库节点 ID
        self.station_nodes: List[int] = []
    
    def generate_grid(self, num_nodes: int, seed: int = 42) -> None:
        """
        生成网格多边形地图
        - 中心节点为仓库 (depot)
        - 随机选择若干节点作为充电站位置
        - 其余为普通节点
        """
        pass  # 详细算法见实现文档
    
    def add_node(self, node_id: int, x: float, y: float, 
                 node_type: str = "normal") -> None:
        """添加节点到地图"""
        self.nodes[node_id] = (x, y, node_type)
        self.graph.add_node(node_id, pos=(x, y), type=node_type)
    
    def add_road(self, u: int, v: int, distance: float = None) -> None:
        """添加道路（边），距离可选，默认使用欧几里得距离"""
        if distance is None:
            ux, uy, _ = self.nodes[u]
            vx, vy, _ = self.nodes[v]
            distance = ((ux - vx) ** 2 + (uy - vy) ** 2) ** 0.5
        self.graph.add_edge(u, v, weight=distance)
    
    def get_distance(self, u: int, v: int) -> float:
        """获取两点间最短路径距离，缓存结果"""
        if u == v:
            return 0.0
        key = (min(u, v), max(u, v))
        if key not in self.dist_matrix:
            try:
                self.dist_matrix[key] = nx.shortest_path_length(
                    self.graph, u, v, weight='weight'
                )
            except nx.NetworkXNoPath:
                self.dist_matrix[key] = float('inf')
        return self.dist_matrix[key]
    
    def get_path(self, u: int, v: int) -> List[int]:
        """获取最短路径（节点 ID 列表）"""
        try:
            return nx.shortest_path(self.graph, u, v, weight='weight')
        except nx.NetworkXNoPath:
            return []
    
    def find_nearest_station(self, node_id: int) -> int:
        """找到距离指定节点最近的充电站"""
        if not self.station_nodes:
            return None
        
        min_dist = float('inf')
        nearest = self.station_nodes[0]
        for station_node in self.station_nodes:
            dist = self.get_distance(node_id, station_node)
            if dist < min_dist:
                min_dist = dist
                nearest = station_node
        return nearest
    
    def get_node_position(self, node_id: int) -> Tuple[float, float]:
        """获取节点的世界坐标 (x, y)"""
        return self.nodes[node_id][:2]
    
    def to_dict(self) -> dict:
        """序列化为前端可用的地图数据"""
        return {
            'nodes': [
                {'id': nid, 'x': x, 'y': y, 'type': ntype}
                for nid, (x, y, ntype) in self.nodes.items()
            ],
            'edges': [
                {'u': u, 'v': v, 'weight': d['weight']}
                for u, v, d in self.graph.edges(data=True)
            ]
        }
```

---

## 4. 调度策略层 (backend/scheduler/)

### 4.1 BaseScheduler (抽象基类)

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from models.task import Task
from models.vehicle import Vehicle
from models.transport_map import TransportMap

class BaseScheduler(ABC):
    """调度器抽象基类，定义统一接口"""
    
    @abstractmethod
    def assign_task(self, task: Task, fleet: List[Vehicle], 
                    map_obj: TransportMap) -> Optional[Vehicle]:
        """
        将任务分配给最合适的车辆
        Args:
            task: 待分配的任务
            fleet: 可用车辆列表
            map_obj: 地图对象
        Returns:
            分配到的车辆，如果无可用车辆则返回 None
        """
        pass
    
    @abstractmethod
    def replan(self, fleet: List[Vehicle], active_tasks: List[Task], 
               map_obj: TransportMap) -> None:
        """重新规划所有车辆路径（可选，用于周期性重优化）"""
        pass
    
    def check_capacity(self, vehicle: Vehicle, task: Task) -> bool:
        """检查载重约束"""
        return vehicle.can_carry(task.weight)
    
    def check_battery(self, vehicle: Vehicle, task: Task, 
                      map_obj: TransportMap, 
                      planned_distance: float) -> bool:
        """
        检查电量约束
        - 需能完成任务路径
        - 任务完成后需能到达最近的充电站（安全余量 1.2x）
        """
        consumption = vehicle.get_consumption_rate() * planned_distance
        nearest_station = map_obj.find_nearest_station(task.delivery_node)
        if nearest_station is None:
            return vehicle.current_battery >= consumption
        
        dist_to_station = map_obj.get_distance(task.delivery_node, 
                                                nearest_station)
        consumption_to_station = (vehicle.consumption_empty * 
                                   dist_to_station * 1.2)
        return vehicle.current_battery >= consumption + consumption_to_station
    
    def check_time_window(self, vehicle: Vehicle, task: Task, 
                          arrival_time: int) -> bool:
        """检查时间窗约束"""
        return arrival_time <= task.due_time
```

### 4.2 NearestFirstScheduler (最近任务优先)

```python
class NearestFirstScheduler(BaseScheduler):
    """
    最近任务优先策略
    - 遍历所有车辆，计算到达取货点的距离
    - 选择距离最近的可用车辆
    - 将任务追加到车辆路径末尾
    """
    
    def assign_task(self, task, fleet, map_obj):
        best_vehicle = None
        min_cost = float('inf')
        
        for vehicle in fleet:
            # 仅考虑空闲或移动中的车辆
            if vehicle.status not in [VehicleStatus.IDLE, VehicleStatus.MOVING]:
                continue
            
            # 计算从当前位置到取货点再到送货点的距离
            dist_to_pickup = map_obj.get_distance(vehicle.current_node, 
                                                   task.pickup_node)
            dist_delivery = map_obj.get_distance(task.pickup_node, 
                                                  task.delivery_node)
            total_distance = dist_to_pickup + dist_delivery
            
            # 约束检查
            if not self.check_capacity(vehicle, task):
                continue
            if not self.check_battery(vehicle, task, map_obj, total_distance):
                continue
            
            # 选择距离最小的
            if total_distance < min_cost:
                min_cost = total_distance
                best_vehicle = vehicle
        
        if best_vehicle:
            self._assign_to_vehicle(best_vehicle, task, map_obj)
            return best_vehicle
        return None
    
    def _assign_to_vehicle(self, vehicle, task, map_obj):
        """将任务追加到车辆路径末尾"""
        # 构建路径: 当前位置 -> 取货点 -> 送货点
        path_to_pickup = map_obj.get_path(vehicle.current_node, 
                                           task.pickup_node)
        path_to_delivery = map_obj.get_path(task.pickup_node, 
                                             task.delivery_node)
        
        vehicle.current_path_nodes = (path_to_pickup[:-1] + 
                                       path_to_delivery)
        vehicle.current_path_index = 0
        vehicle.status = VehicleStatus.MOVING
        vehicle.add_task(task)
        task.status = Task.STATUS_ASSIGNED
        task.assigned_vehicle = vehicle.id
    
    def replan(self, fleet, active_tasks, map_obj):
        pass  # 贪婪策略不支持重规划
```

### 4.3 MaxWeightScheduler (最大重量优先)

```python
class MaxWeightScheduler(BaseScheduler):
    """
    最大重量优先策略
    - 优先处理重量大的任务（单位载重收益高）
    - 在可承载的车辆中选择效率最高的（距离/载重比最优）
    """
    
    def assign_task(self, task, fleet, map_obj):
        candidates = []
        
        for vehicle in fleet:
            if vehicle.status not in [VehicleStatus.IDLE, VehicleStatus.MOVING]:
                continue
            
            dist_to_pickup = map_obj.get_distance(vehicle.current_node, 
                                                   task.pickup_node)
            dist_delivery = map_obj.get_distance(task.pickup_node, 
                                                  task.delivery_node)
            total_distance = dist_to_pickup + dist_delivery
            
            if not self.check_capacity(vehicle, task):
                continue
            if not self.check_battery(vehicle, task, map_obj, total_distance):
                continue
            
            # 效率 = 重量 / 总距离
            efficiency = task.weight / (total_distance + 1)
            candidates.append((efficiency, vehicle, total_distance))
        
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            _, best_vehicle, _ = candidates[0]
            self._assign_to_vehicle(best_vehicle, task, map_obj)
            return best_vehicle
        return None
    
    def _assign_to_vehicle(self, vehicle, task, map_obj):
        # 与 NearestFirstScheduler 相同
        pass
    
    def replan(self, fleet, active_tasks, map_obj):
        pass
```

### 4.4 InsertionScheduler (插入启发式)

```python
class InsertionScheduler(BaseScheduler):
    """
    插入启发式策略
    - 将新任务插入到现有路径的最优位置
    - 取货点和送货点可以插入到路径的任意位置
    - 选择使总路径增加最少的插入方案
    """
    
    def assign_task(self, task, fleet, map_obj):
        best_cost = float('inf')
        best_vehicle = None
        best_insertion = None  # (pickup_idx, delivery_idx)
        
        for vehicle in fleet:
            # 如果车辆当前没有路径，直接分配
            if not vehicle.action_plan:
                cost = self._calculate_direct_cost(vehicle, task, map_obj)
                if cost is not None and cost < best_cost:
                    best_cost = cost
                    best_vehicle = vehicle
                    best_insertion = (0, 1)
                continue
            
            # 尝试在所有可能的位置插入
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
            self._apply_insertion(best_vehicle, task, best_insertion, map_obj)
            return best_vehicle
        return None
    
    def _calculate_direct_cost(self, vehicle, task, map_obj):
        """计算直接分配的成本（车辆当前无任务）"""
        if not self.check_capacity(vehicle, task):
            return None
        
        dist = (map_obj.get_distance(vehicle.current_node, task.pickup_node) +
                map_obj.get_distance(task.pickup_node, task.delivery_node))
        
        if not self.check_battery(vehicle, task, map_obj, dist):
            return None
        
        return dist
    
    def _calculate_insertion_cost(self, vehicle, task, p_idx, d_idx, map_obj):
        """
        计算在指定位置插入取货和送货的边际成本
        - pickup_idx: 取货动作插入位置
        - delivery_idx: 送货动作插入位置（必须在取货之后）
        """
        pass  # 详细实现见计划文档
    
    def _apply_insertion(self, vehicle, task, insertion, map_obj):
        """将任务插入到车辆的 action_plan"""
        p_idx, d_idx = insertion
        # 构建新的 action_plan
        pass
    
    def replan(self, fleet, active_tasks, map_obj):
        """周期性重优化所有车辆路径"""
        pass
```

---

## 5. 仿真引擎 (backend/simulator/)

### 5.1 Simulator (主仿真器)

```python
import threading
import time
from typing import List, Dict, Optional, Callable

class Simulator:
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
        self.tick_interval = config.get('tick_interval', 1)      # 仿真时间单位
        self.sim_speed = config.get('sim_speed', 1.0)           # 加速倍数
        self.real_time_step = 0.1 / self.sim_speed              # 真实时间间隔(秒)
        
        # 回调函数（由 app.py 注入）
        self._emit_state: Optional[Callable] = None
        self._emit_finished: Optional[Callable] = None
    
    def initialize(self, map_config: dict, fleet_config: List[dict], 
                   station_config: List[dict], scheduler_type: str) -> None:
        """初始化仿真环境"""
        # 创建地图
        self.map = TransportMap(map_config['width'], map_config['height'])
        self.map.generate_grid(map_config['num_nodes'])
        
        # 添加充电站
        for sc in station_config:
            station = ChargingStation(**sc)
            self.charging_stations.append(station)
            self.map.station_nodes.append(sc['node_id'])
            # 更新节点类型
            if sc['node_id'] in self.map.nodes:
                x, y, _ = self.map.nodes[sc['node_id']]
                self.map.nodes[sc['node_id']] = (x, y, 'station')
        
        # 创建车队
        for fc in fleet_config:
            vehicle = Vehicle(**fc)
            vehicle.position = self.map.get_node_position(fc['start_node'])
            self.fleet.append(vehicle)
        
        # 设置调度器
        self.scheduler = self._create_scheduler(scheduler_type)
        
        # 创建事件生成器
        self.event_generator = EventGenerator(
            task_count=self.config.get('task_count', 100),
            time_horizon=self.config.get('time_horizon', 1000),
            map_nodes=list(self.map.nodes.keys())
        )
        self.event_generator.generate_schedule()
    
    def _create_scheduler(self, scheduler_type: str) -> BaseScheduler:
        if scheduler_type == 'nearest':
            return NearestFirstScheduler()
        elif scheduler_type == 'max_weight':
            return MaxWeightScheduler()
        elif scheduler_type == 'insertion':
            return InsertionScheduler()
        else:
            raise ValueError(f"Unknown scheduler type: {scheduler_type}")
    
    def tick(self) -> dict:
        """推进一个仿真时间步，返回状态快照"""
        self.current_time += self.tick_interval
        
        # 1. 生成新任务
        new_tasks = self.event_generator.generate(self.current_time)
        for task in new_tasks:
            self.active_tasks.append(task)
            # 立即尝试分配
            assigned = self.scheduler.assign_task(task, self.fleet, self.map)
            if not assigned:
                task.status = Task.STATUS_PENDING
        
        # 2. 更新每辆车
        for vehicle in self.fleet:
            self._update_vehicle(vehicle)
        
        # 3. 更新充电站
        for station in self.charging_stations:
            station.tick(self.tick_interval)
        
        # 4. 检查超时任务
        for task in self.active_tasks[:]:
            if task.is_timeout(self.current_time):
                task.status = Task.STATUS_TIMEOUT
                self.failed_tasks.append(task)
                self.active_tasks.remove(task)
        
        # 5. 检查是否需要充电并规划路径
        self._handle_low_battery()
        
        # 6. 计算分数
        score = self._calculate_score()
        
        return self._get_state_snapshot(score)
    
    def _update_vehicle(self, vehicle: Vehicle) -> None:
        """更新单辆车状态"""
        if vehicle.status == VehicleStatus.MOVING:
            self._update_moving(vehicle)
        elif vehicle.status == VehicleStatus.CHARGING:
            # 充电状态由 ChargingStation.tick 管理
            pass
        elif vehicle.status == VehicleStatus.WAITING_CHARGE:
            # 等待状态，不做任何事
            pass
        elif vehicle.status == VehicleStatus.IDLE:
            # 尝试执行下一个动作
            self._execute_next_action(vehicle)
        elif vehicle.status in [VehicleStatus.LOADING, VehicleStatus.UNLOADING]:
            # 装卸货动作在到达节点时处理
            pass
    
    def _update_moving(self, vehicle: Vehicle) -> None:
        """更新移动中的车辆"""
        if not vehicle.current_path_nodes:
            vehicle.status = VehicleStatus.IDLE
            return
        
        if vehicle.current_path_index >= len(vehicle.current_path_nodes) - 1:
            # 已到达终点
            vehicle.current_node = vehicle.current_path_nodes[-1]
            vehicle.position = self.map.get_node_position(vehicle.current_node)
            vehicle.progress = 0.0
            self._on_arrive_at_node(vehicle)
            return
        
        # 沿当前路段移动
        current_node_id = vehicle.current_path_nodes[vehicle.current_path_index]
        next_node_id = vehicle.current_path_nodes[vehicle.current_path_index + 1]
        
        current_pos = self.map.get_node_position(current_node_id)
        next_pos = self.map.get_node_position(next_node_id)
        segment_distance = self.map.get_distance(current_node_id, next_node_id)
        
        # 更新进度
        speed = self.config.get('vehicle_speed', 10.0)
        vehicle.progress += (speed * self.tick_interval) / segment_distance
        
        # 插值更新位置
        if vehicle.progress >= 1.0:
            # 到达下一段
            vehicle.current_path_index += 1
            vehicle.progress = 0.0
            vehicle.current_node = next_node_id
            
            # 扣除电量
            vehicle.move(segment_distance)
            
            # 检查是否到达最终节点
            if vehicle.current_path_index >= len(vehicle.current_path_nodes) - 1:
                self._on_arrive_at_node(vehicle)
        else:
            # 插值位置
            t = vehicle.progress
            vehicle.position = (
                current_pos[0] + (next_pos[0] - current_pos[0]) * t,
                current_pos[1] + (next_pos[1] - current_pos[1]) * t
            )
            
            # 扣除电量（按实际移动距离）
            actual_distance = segment_distance * (speed * self.tick_interval / segment_distance)
            vehicle.move(min(actual_distance, segment_distance))
    
    def _on_arrive_at_node(self, vehicle: Vehicle) -> None:
        """车辆到达目标节点时的处理"""
        vehicle.status = VehicleStatus.IDLE
        vehicle.progress = 0.0
        vehicle.current_path_nodes = []
        vehicle.current_path_index = 0
        
        # 检查当前节点是否为充电站
        for station in self.charging_stations:
            if station.node_id == vehicle.current_node:
                if station.is_available():
                    station.start_charging(vehicle)
                else:
                    station.join_queue(vehicle)
                return
        
        # 执行动作计划中的下一个动作
        self._execute_next_action(vehicle)
    
    def _execute_next_action(self, vehicle: Vehicle) -> None:
        """执行 action_plan 中的下一个动作"""
        if not vehicle.action_plan:
            return
        
        action = vehicle.action_plan.pop(0)
        action_type = action['type']
        
        if action_type == 'pickup':
            task = action['task']
            vehicle.status = VehicleStatus.LOADING
            task.status = Task.STATUS_PICKING
            # 简化为立即完成取货
            vehicle.add_task(task)
            task.status = Task.STATUS_DELIVERING
            vehicle.status = VehicleStatus.IDLE
            
        elif action_type == 'deliver':
            task = action['task']
            vehicle.status = VehicleStatus.UNLOADING
            vehicle.remove_task(task)
            task.status = Task.STATUS_COMPLETED
            task.completed_time = self.current_time
            self.completed_tasks.append(task)
            if task in self.active_tasks:
                self.active_tasks.remove(task)
            vehicle.status = VehicleStatus.IDLE
            
        elif action_type == 'move':
            target_node = action['target']
            vehicle.current_path_nodes = self.map.get_path(
                vehicle.current_node, target_node
            )
            vehicle.current_path_index = 0
            vehicle.status = VehicleStatus.MOVING
            
        elif action_type == 'charge':
            station_id = action['station_id']
            station = next((s for s in self.charging_stations 
                           if s.id == station_id), None)
            if station:
                if station.is_available():
                    station.start_charging(vehicle)
                else:
                    station.join_queue(vehicle)
    
    def _handle_low_battery(self) -> None:
        """处理低电量车辆，规划前往充电站"""
        for vehicle in self.fleet:
            if vehicle.status not in [VehicleStatus.IDLE, VehicleStatus.MOVING]:
                continue
            
            # 检查剩余电量是否足够返回最近充电站
            nearest_station = self.map.find_nearest_station(vehicle.current_node)
            if nearest_station is None:
                continue
            
            dist_to_station = self.map.get_distance(vehicle.current_node, 
                                                     nearest_station)
            consumption_to_station = (vehicle.get_consumption_rate() * 
                                       dist_to_station * 1.5)
            
            if vehicle.current_battery <= consumption_to_station:
                # 电量不足，前往充电
                vehicle.action_plan.insert(0, {
                    'type': 'move',
                    'target': nearest_station
                })
                vehicle.action_plan.insert(1, {
                    'type': 'charge',
                    'station_id': next(s.id for s in self.charging_stations 
                                      if s.node_id == nearest_station)
                })
                if vehicle.status == VehicleStatus.IDLE:
                    self._execute_next_action(vehicle)
    
    def _calculate_score(self) -> float:
        """计算当前总分"""
        score = 0.0
        for task in self.completed_tasks:
            score += task.get_score()
        for task in self.failed_tasks:
            score += task.get_score()
        return score
    
    def _get_state_snapshot(self, score: float) -> dict:
        """获取当前状态快照（用于前端展示和 WebSocket 传输）"""
        return {
            'time': self.current_time,
            'score': round(score, 2),
            'vehicles': [v.to_dict() for v in self.fleet],
            'tasks': [
                {
                    'id': t.id,
                    'pickup': t.pickup_node,
                    'delivery': t.delivery_node,
                    'weight': round(t.weight, 2),
                    'status': t.status,
                    'ready_time': t.ready_time,
                    'due_time': t.due_time,
                    'assigned_vehicle': t.assigned_vehicle
                }
                for t in (self.active_tasks + self.completed_tasks + 
                         self.failed_tasks)
            ],
            'stations': [s.to_dict() for s in self.charging_stations],
            'stats': {
                'completed': len(self.completed_tasks),
                'failed': len(self.failed_tasks),
                'pending': len([t for t in self.active_tasks 
                               if t.status == Task.STATUS_PENDING]),
                'active': len([t for t in self.active_tasks 
                              if t.status != Task.STATUS_PENDING]),
                'total_tasks': (len(self.completed_tasks) + 
                               len(self.failed_tasks) + 
                               len(self.active_tasks))
            }
        }
    
    def run(self) -> None:
        """运行仿真主循环"""
        self.running = True
        while self.running:
            start_time = time.time()
            
            state = self.tick()
            
            # 通过 WebSocket 发送状态
            if self._emit_state:
                self._emit_state(state)
            
            # 检查结束条件
            if self._check_finished():
                self.running = False
                if self._emit_finished:
                    final_score = self._calculate_score()
                    self._emit_finished({'final_score': final_score})
                break
            
            # 控制仿真速度
            elapsed = time.time() - start_time
            sleep_time = max(0, self.real_time_step - elapsed)
            time.sleep(sleep_time)
    
    def _check_finished(self) -> bool:
        """检查仿真是否结束"""
        total_tasks = self.config.get('task_count', 100)
        completed_or_failed = len(self.completed_tasks) + len(self.failed_tasks)
        all_tasks_processed = completed_or_failed >= total_tasks
        no_active = len(self.active_tasks) == 0
        return all_tasks_processed and no_active
    
    def pause(self) -> None:
        """暂停仿真"""
        self.running = False
    
    def reset(self) -> None:
        """重置仿真状态"""
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

### 5.2 EventGenerator (任务生成器)

```python
import random
from typing import List

class EventGenerator:
    """动态任务生成器 - 预生成任务时间表并按时刻激活"""
    
    def __init__(self, task_count: int, time_horizon: int,
                 weight_range: tuple = (1.0, 20.0),
                 map_nodes: List[int] = None,
                 seed: int = 42):
        self.task_count = task_count
        self.time_horizon = time_horizon
        self.weight_range = weight_range
        self.map_nodes = map_nodes or []
        self.seed = seed
        self.generated_count = 0
        self.schedule: List[dict] = []  # 预生成的任务时间表
        
        random.seed(seed)
    
    def generate_schedule(self) -> None:
        """
        预生成任务出现时间表
        - 在 [1, time_horizon] 内随机生成 task_count 个时间点
        - 每个任务随机选择取货点和送货点（不同节点）
        - 随机生成货物重量和时间窗
        """
        if self.time_horizon <= 1 or not self.map_nodes:
            return
        
        # 生成不重复的随机时间点
        num_times = min(self.task_count, self.time_horizon - 1)
        times = sorted(random.sample(range(1, self.time_horizon), num_times))
        
        self.schedule = []
        for i, t in enumerate(times):
            # 随机选择取货点和送货点（确保不同）
            pickup = random.choice(self.map_nodes)
            delivery_candidates = [n for n in self.map_nodes if n != pickup]
            delivery = random.choice(delivery_candidates) if delivery_candidates else pickup
            
            # 随机重量
            weight = round(random.uniform(*self.weight_range), 2)
            
            # 时间窗：ready_time = 生成时间, due_time = ready + 随机偏移
            ready_time = t
            due_time = t + random.randint(30, 150)
            
            self.schedule.append({
                'id': i + 1,
                'pickup_node': pickup,
                'delivery_node': delivery,
                'weight': weight,
                'ready_time': ready_time,
                'due_time': due_time,
                'create_time': t
            })
    
    def generate(self, current_time: int) -> List[Task]:
        """
        生成当前时刻应激活的任务
        - 返回所有 create_time <= current_time 且未生成的任务
        """
        tasks = []
        while (self.schedule and 
               self.schedule[0]['create_time'] <= current_time and
               self.generated_count < self.task_count):
            data = self.schedule.pop(0)
            task = Task(**data)
            tasks.append(task)
            self.generated_count += 1
        return tasks
    
    def peek_next_time(self) -> Optional[int]:
        """查看下一个任务的生成时间（用于优化）"""
        if self.schedule:
            return self.schedule[0]['create_time']
        return None
```

---

## 6. Web 服务层 (backend/app.py)

```python
from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import threading
import os

app = Flask(__name__, static_folder='../frontend')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 全局仿真实例和线程
simulator: Optional[Simulator] = None
sim_thread: Optional[threading.Thread] = None

# ============================================================
# REST API 路由
# ============================================================

@app.route('/')
def index():
    """服务前端主页面"""
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """服务前端静态资源"""
    return send_from_directory('../frontend', path)

@app.route('/api/map', methods=['GET'])
def get_map():
    """获取地图配置数据"""
    if simulator and simulator.map:
        return jsonify(simulator.map.to_dict())
    return jsonify({'error': 'Simulator not initialized'}), 400

@app.route('/api/config', methods=['POST'])
def initialize_simulation():
    """
    初始化仿真环境
    Request Body:
        - map: {width, height, num_nodes}
        - fleet: List[{id, start_node, max_battery, max_capacity, ...}]
        - stations: List[{id, node_id, total_slots, charge_rate}]
        - scheduler: str ("nearest" | "max_weight" | "insertion")
        - task_count: int
        - time_horizon: int
        - sim_speed: float
    """
    global simulator
    
    config = request.json
    simulator = Simulator(config)
    simulator.initialize(
        map_config=config['map'],
        fleet_config=config['fleet'],
        station_config=config['stations'],
        scheduler_type=config.get('scheduler', 'insertion')
    )
    
    # 注入 WebSocket 回调
    simulator._emit_state = lambda state: socketio.emit('state_update', state)
    simulator._emit_finished = lambda data: socketio.emit('simulation_finished', data)
    
    return jsonify({
        'status': 'initialized',
        'task_count': len(simulator.event_generator.schedule),
        'map_nodes': len(simulator.map.nodes),
        'fleet_size': len(simulator.fleet)
    })

@app.route('/api/start', methods=['POST'])
def start_simulation():
    """启动仿真（在后台线程中运行）"""
    global sim_thread
    
    if not simulator:
        return jsonify({'error': 'Simulator not initialized'}), 400
    
    if simulator.running:
        return jsonify({'error': 'Simulation already running'}), 400
    
    def run_sim():
        simulator.run()
    
    sim_thread = threading.Thread(target=run_sim, daemon=True)
    sim_thread.start()
    
    return jsonify({'status': 'started', 'time': simulator.current_time})

@app.route('/api/pause', methods=['POST'])
def pause_simulation():
    """暂停仿真"""
    if simulator:
        simulator.pause()
    return jsonify({'status': 'paused'})

@app.route('/api/reset', methods=['POST'])
def reset_simulation():
    """重置仿真（终止当前仿真并清除状态）"""
    global simulator, sim_thread
    
    if simulator:
        simulator.reset()
    
    if sim_thread and sim_thread.is_alive():
        sim_thread.join(timeout=2.0)
    
    simulator = None
    sim_thread = None
    
    return jsonify({'status': 'reset'})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取当前统计信息"""
    if not simulator:
        return jsonify({'error': 'Simulator not initialized'}), 400
    
    return jsonify({
        'time': simulator.current_time,
        'score': simulator._calculate_score(),
        'completed': len(simulator.completed_tasks),
        'failed': len(simulator.failed_tasks),
        'active': len(simulator.active_tasks)
    })

@app.route('/api/vehicle/<int:vehicle_id>', methods=['GET'])
def get_vehicle_detail(vehicle_id):
    """获取指定车辆的详细信息"""
    if not simulator:
        return jsonify({'error': 'Simulator not initialized'}), 400
    
    vehicle = next((v for v in simulator.fleet if v.id == vehicle_id), None)
    if not vehicle:
        return jsonify({'error': 'Vehicle not found'}), 404
    
    return jsonify({
        **vehicle.to_dict(),
        'action_plan': vehicle.action_plan,
        'carrying_tasks': [
            {'id': t.id, 'pickup': t.pickup_node, 
             'delivery': t.delivery_node, 'weight': t.weight}
            for t in vehicle.carrying_tasks
        ]
    })

# ============================================================
# WebSocket 事件
# ============================================================

@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    print(f'Client connected: {request.sid}')
    emit('connected', {
        'message': 'Connected to EV Fleet Simulation Server',
        'version': '1.0'
    })

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开"""
    print(f'Client disconnected: {request.sid}')

@socketio.on('request_state')
def handle_request_state():
    """客户端请求当前状态"""
    if simulator:
        state = simulator._get_state_snapshot(simulator._calculate_score())
        emit('state_update', state)

# ============================================================
# 启动
# ============================================================

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
```

---

## 7. 前端可视化层 (frontend/)

### 7.1 页面结构 (index.html)

见上文设计，采用三栏布局：
- **左侧**: 控制面板（仿真控制、参数设置、实时统计）
- **中间**: Canvas 地图（占据主要区域，显示路网、车辆、任务、充电站）
- **右侧**: 信息面板（车辆状态列表、任务列表、充电站状态）
- **底部**: 运行日志

### 7.2 样式主题 (css/styles.css)

- **配色方案**: 深色主题 (Dark Mode)
  - 背景: `#1a1a2e` (深蓝黑)
  - 面板: `#16213e` (深蓝)
  - 强调色: `#e94560` (珊瑚红) / `#00d9ff` (青色)
  - 文字: `#eaeaea` (主文字) / `#a0a0a0` (次要文字)

- **关键元素样式**:
  - 仓库节点: 金色发光圆点
  - 充电站: 绿色圆环 + 占用指示
  - 取货点: 橙色三角形
  - 送货点: 红色正方形
  - 车辆: 青色圆点 + 电量环 + 载重指示

### 7.3 JavaScript 模块

#### SocketClient (js/socket_client.js)
- 封装 Socket.IO 连接
- 事件订阅/发布机制
- 自动重连处理

#### MapRenderer (js/map_renderer.js)
- Canvas 地图渲染
- 网格背景、道路、节点
- 世界坐标到屏幕坐标的转换
- 缩放和平移（可选）

#### VehicleRenderer (js/vehicle_renderer.js)
- 车辆图标渲染（含 ID）
- 电量指示环（颜色根据电量变化）
- 载重指示（填充比例）
- 规划路径虚线
- 移动轨迹（可选）

#### TaskRenderer (js/task_renderer.js)
- 取货点标记（橙色三角形）
- 送货点标记（红色正方形）
- 已分配任务的连线
- 状态颜色区分

#### StationRenderer (js/station_renderer.js)
- 充电站外圈（容量指示）
- 占用填充
- 排队数量显示

#### UIController (js/ui_controller.js)
- 按钮事件绑定
- 参数配置
- 统计面板更新
- 日志输出
- 渲染循环管理 (requestAnimationFrame)

---

## 8. 数据流与交互时序

### 8.1 仿真初始化流程

```
用户访问页面
    │
    ▼
前端加载 → 连接 WebSocket
    │
    ▼
用户点击"初始化"
    │
    ▼
前端 POST /api/config → 后端创建 Simulator
    │                           │
    │                           ▼
    │                    生成地图、车队、充电站
    │                           │
    │                           ▼
    │                    预生成任务时间表
    │                           │
    │◄───────────────── 返回初始化成功
    │
    ▼
前端 GET /api/map → 获取地图数据
    │
    ▼
前端渲染地图
```

### 8.2 仿真运行流程

```
用户点击"开始"
    │
    ▼
前端 POST /api/start
    │
    ▼
后端启动仿真线程 → tick() 循环
    │
    ├── 生成新任务 → 调度器分配
    │
    ├── 更新车辆位置/电量
    │
    ├── 更新充电站状态
    │
    ├── 检查超时任务
    │
    └── 计算得分
    │
    ▼
WebSocket emit 'state_update'
    │
    ▼
前端接收 → 更新所有 Renderer → Canvas 重绘
    │
    ▼
用户看到实时动画
```

### 8.3 状态更新频率

- **后端 tick 频率**: 每 0.1 秒一个 tick（可调速）
- **前端渲染帧率**: 60 FPS (requestAnimationFrame)
- **WebSocket 传输**: 每个 tick 推送一次完整状态

---

## 9. Agent Team 协作分工

### 9.1 团队结构

```
┌─────────────────────────────────────────────────────────────┐
│                      项目总负责人 (Team Lead)                  │
│                    - 架构设计、进度管理、代码审查               │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  Backend Agent │   │ Frontend Agent  │   │  Algo Agent     │
│  (后端开发)     │   │  (前端开发)      │   │  (算法优化)      │
├───────────────┤   ├─────────────────┤   ├─────────────────┤
│ • 数据模型     │   │ • HTML/CSS 结构  │   │ • 调度策略实现   │
│ • 仿真引擎     │   │ • Canvas 渲染    │   │ • 路径规划优化   │
│ • Web 服务     │   │ • WebSocket 通信 │   │ • 评分系统调优   │
│ • API 设计     │   │ • UI 交互逻辑    │   │ • 算法对比分析   │
└───────────────┘   └─────────────────┘   └─────────────────┘
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              │
                              ▼
                   ┌────────────────────┐
                   │   Integration      │
                   │   (集成测试)        │
                   └────────────────────┘
```

### 9.2 各 Agent 职责与交付物

#### Backend Agent
- **核心职责**: 实现所有 Python 后端代码
- **交付文件**:
  - `backend/models/*.py` - 数据模型
  - `backend/simulator/*.py` - 仿真引擎
  - `backend/app.py` - Web 服务
  - `backend/requirements.txt` - 依赖
- **关键函数**:
  - `TransportMap.generate_grid()` - 地图生成
  - `Simulator.tick()` - 仿真推进
  - `Simulator._update_vehicle()` - 车辆状态更新
  - `EventGenerator.generate_schedule()` - 任务生成

#### Frontend Agent
- **核心职责**: 实现所有前端可视化代码
- **交付文件**:
  - `frontend/index.html`
  - `frontend/css/styles.css`
  - `frontend/js/*.js`
- **关键函数**:
  - `MapRenderer.render()` - 地图渲染
  - `VehicleRenderer.drawVehicle()` - 车辆渲染
  - `UIController.updateUI()` - UI 更新
  - `SocketClient.setupListeners()` - WebSocket 监听

#### Algo Agent
- **核心职责**: 实现和优化调度算法
- **交付文件**:
  - `backend/scheduler/*.py` - 所有调度策略
  - `backend/simulator/scoring.py` - 评分系统
- **关键函数**:
  - `NearestFirstScheduler.assign_task()`
  - `MaxWeightScheduler.assign_task()`
  - `InsertionScheduler._calculate_insertion_cost()`
  - `InsertionScheduler._apply_insertion()`

#### Team Lead
- **核心职责**: 架构设计、接口定义、进度协调、代码审查
- **交付物**:
  - 本设计文档
  - 实现计划
  - 接口契约（前后端数据格式）

### 9.3 协作接口契约

#### REST API 规范

| 端点 | 方法 | 请求体 | 响应 |
|------|------|--------|------|
| `/api/config` | POST | `{map, fleet, stations, scheduler, ...}` | `{status, task_count}` |
| `/api/start` | POST | - | `{status, time}` |
| `/api/pause` | POST | - | `{status}` |
| `/api/reset` | POST | - | `{status}` |
| `/api/map` | GET | - | `{nodes, edges}` |
| `/api/stats` | GET | - | `{time, score, completed, failed, active}` |

#### WebSocket 事件

| 事件名 | 方向 | 数据格式 |
|--------|------|----------|
| `connect` | C→S | - |
| `connected` | S→C | `{message, version}` |
| `state_update` | S→C | `{time, score, vehicles, tasks, stations, stats}` |
| `simulation_finished` | S→C | `{final_score}` |
| `request_state` | C→S | - |

#### 状态快照格式 (state_update)

```json
{
  "time": 150,
  "score": 8750.5,
  "vehicles": [
    {
      "id": 1,
      "node": 12,
      "position": [45.2, 78.5],
      "battery": 65.5,
      "battery_pct": 0.655,
      "load": 15.0,
      "load_pct": 0.3,
      "status": "moving",
      "path": [12, 15, 18, 22],
      "carrying": [3, 7]
    }
  ],
  "tasks": [
    {
      "id": 1,
      "pickup": 5,
      "delivery": 23,
      "weight": 8.5,
      "status": "delivering",
      "ready_time": 10,
      "due_time": 120,
      "assigned_vehicle": 2
    }
  ],
  "stations": [
    {
      "id": 1,
      "node": 10,
      "occupied": 2,
      "total": 3,
      "queue": 1
    }
  ],
  "stats": {
    "completed": 45,
    "failed": 3,
    "pending": 12,
    "active": 40,
    "total_tasks": 100
  }
}
```

---

## 10. 实现阶段划分

### 阶段 1: 基础设施搭建 (Day 1)
- **Backend Agent**: 创建项目结构，实现 TransportMap 和基础模型
- **Frontend Agent**: 搭建 HTML/CSS 框架，初始化 Canvas
- **Team Lead**: 确认接口契约

### 阶段 2: 核心仿真引擎 (Day 2-3)
- **Backend Agent**: 实现 Vehicle, Task, ChargingStation 完整逻辑
- **Algo Agent**: 实现基础调度策略 (NearestFirst, MaxWeight)
- **Backend Agent**: 实现 Simulator.tick() 和事件生成

### 阶段 3: 前端可视化 (Day 3-4)
- **Frontend Agent**: 实现 MapRenderer, VehicleRenderer
- **Frontend Agent**: 实现 TaskRenderer, StationRenderer
- **Frontend Agent**: 实现 UIController 和 WebSocket 通信

### 阶段 4: 调度算法优化 (Day 4-5)
- **Algo Agent**: 实现 InsertionScheduler
- **Algo Agent**: 实现评分系统和路径优化
- **Backend Agent**: 集成所有调度器到 Simulator

### 阶段 5: 集成与测试 (Day 5-6)
- **Team Lead**: 前后端联调
- **All Agents**: 端到端测试
- **Frontend Agent**: UI 美化与响应式调整
- **Algo Agent**: 多种规模测试 (小规模 20节点/3车, 中规模 50节点/10车, 大规模 100节点/20车)

### 阶段 6: 文档与交付 (Day 7)
- **Team Lead**: 编写项目报告
- **Frontend Agent**: 录制展示视频
- **All Agents**: 代码审查与优化

---

## 11. 扩展性设计

### 11.1 新增调度策略
1. 继承 `BaseScheduler`
2. 实现 `assign_task()` 方法
3. 在 `Simulator._create_scheduler()` 中注册

### 11.2 新增节点类型
1. 在 `TransportMap.generate_grid()` 中生成新类型节点
2. 在渲染器中添加对应的绘制逻辑
3. 在约束检查中处理新类型

### 11.3 地图规模扩展
- 通过 `map_config.num_nodes` 参数控制
- NetworkX 图结构支持任意规模
- Canvas 渲染自动适配（可添加缩放功能）

---

## 12. 风险评估与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| NetworkX 大规模图性能下降 | 高 | 预计算距离矩阵，使用稀疏存储 |
| 前端 Canvas 渲染卡顿 | 中 | 减少绘制元素，使用脏矩形优化 |
| WebSocket 连接不稳定 | 中 | 添加重连机制，支持状态恢复 |
| 调度算法效率低 | 中 | 先实现基础版本，再逐步优化 |
| 多车辆路径冲突 | 低 | V2 版本添加冲突检测与避让 |

---

## 附录 A: 完整文件清单

### Python 文件 (backend/)
| 文件 | 类/函数 | 行数预估 |
|------|---------|---------|
| `models/task.py` | Task | ~60 |
| `models/vehicle.py` | VehicleStatus, Vehicle | ~120 |
| `models/charging_station.py` | ChargingStation | ~80 |
| `models/transport_map.py` | TransportMap | ~120 |
| `scheduler/base_scheduler.py` | BaseScheduler | ~50 |
| `scheduler/nearest_first_scheduler.py` | NearestFirstScheduler | ~60 |
| `scheduler/max_weight_scheduler.py` | MaxWeightScheduler | ~60 |
| `scheduler/insertion_scheduler.py` | InsertionScheduler | ~120 |
| `simulator/simulator.py` | Simulator | ~250 |
| `simulator/event_generator.py` | EventGenerator | ~80 |
| `simulator/scoring.py` | ScoreCalculator | ~40 |
| `app.py` | Flask app, routes | ~150 |

### 前端文件 (frontend/)
| 文件 | 类/函数 | 行数预估 |
|------|---------|---------|
| `index.html` | 页面结构 | ~150 |
| `css/styles.css` | 样式定义 | ~300 |
| `js/socket_client.js` | SocketClient | ~60 |
| `js/map_renderer.js` | MapRenderer | ~150 |
| `js/vehicle_renderer.js` | VehicleRenderer | ~120 |
| `js/task_renderer.js` | TaskRenderer | ~100 |
| `js/station_renderer.js` | StationRenderer | ~80 |
| `js/ui_controller.js` | UIController | ~200 |

**总计**: ~2200 行代码

---

> **文档结束** - 本设计文档经确认后，将作为实现计划的基础。
