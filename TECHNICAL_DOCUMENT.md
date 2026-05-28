# 新能源物流车队协同调度仿真系统 — 核心技术文档

> 本文档面向具备 Python/算法背景的开发者，系统梳理后端核心逻辑、调度算法原理与架构设计，用于项目报告撰写与后续技术迭代。

---

## 1. 项目概述

### 1.1 问题背景

城市末端物流配送场景中，新能源（电动）货车面临双重约束：
- **容量约束**：车辆载重/容积有限，需合理分配任务避免超载
- **电量约束**：续航里程有限，需规划充电时机与路线，避免中途断电

本系统通过离散事件仿真（Discrete-Event Simulation, DES），在随机生成的城市道路网络上，对比三种任务调度策略的优劣，为实际物流调度决策提供量化依据。

### 1.2 系统能力边界

| 能力 | 说明 |
|------|------|
| 地图生成 | 基于网格的随机道路网络，含仓库、子仓库、充电站 |
| 任务生成 | 支持三类任务（分拣派送、单点送货、仓库取货），带时间窗口 |
| 车辆仿真 | 电量消耗与负载成正比，支持途中充电与排队 |
| 调度策略 | 三种可插拔调度器，支持算法性能对比实验 |
| 实时可视化 | WebSocket 推送仿真状态，前端 Canvas 渲染 |

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (Frontend)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ MapRenderer │  │TaskRenderer │  │ VehicleRenderer     │  │
│  │ (道路网络)   │  │ (任务标记)   │  │ (车辆/路径/电量)     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                        ↑ WebSocket (Socket.IO)               │
└────────────────────────┼────────────────────────────────────┘
                         │
┌────────────────────────┼────────────────────────────────────┐
│                        │         后端 (Flask + SocketIO)     │
│  ┌─────────────────────┼─────────────────────────────────┐  │
│  │                     ↓                                  │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │  │
│  │  │  HTTP API │  │  /api/start  │  │  /api/compare (对比实验) │ │  │
│  │  │  /api/config│  │  /api/pause  │  │                        │ │  │
│  │  └──────────┘  └──────────┘  └──────────────────────┘ │  │
│  │                        │                               │  │
│  │                   Simulator (主仿真引擎)                 │  │
│  │                        │                               │  │
│  │  ┌─────────────────────┼─────────────────────────────┐ │  │
│  │  │                     ↓                              │ │  │
│  │  │  EventGenerator ──→ 生成带时间窗口的随机任务序列    │ │  │
│  │  │  Scheduler      ──→ 分配任务到车辆 (可插拔策略)    │ │  │
│  │  │  VehicleUpdater ──→ 更新车辆位置/电量/状态        │ │  │
│  │  │  StationManager ──→ 管理充电站占用与排队          │ │  │
│  │  │  ScoreKeeper    ──→ 计算得分与超时判定            │ │  │
│  │  └───────────────────────────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| 数据模型 | `models/*.py` | Task、Vehicle、TransportMap、ChargingStation 的定义与序列化 |
| 调度器 | `scheduler/*.py` | 任务分配策略的抽象基类与三种实现 |
| 仿真引擎 | `simulator/simulator.py` | 主循环：每 tick 推进仿真状态 |
| 事件生成 | `simulator/event_generator.py` | 预生成任务出现的时间表 |
| Web 服务 | `app.py` | Flask HTTP API + SocketIO 实时推送 |

---

## 3. 核心数据模型

### 3.1 任务模型 (`Task`)

```python
class Task:
    TYPE_PAIRED = "paired"            # 分拣派送：取货点 → 仓库 → 送货点
    TYPE_DEPOT_DELIVERY = "depot_delivery"   # 单点送货：仓库 → 送货点
    TYPE_SUB_DEPOT_RETURN = "sub_depot_return" # 仓库取货：子仓库 → 仓库

    STATUS_PENDING = "pending"
    STATUS_ASSIGNED = "assigned"
    STATUS_PICKING = "picking"        # 车辆到达取货点，装载中
    STATUS_DELIVERING = "delivering"  # 已回仓库，正在去送货点
    STATUS_COMPLETED = "completed"
    STATUS_TIMEOUT = "timeout"
```

**状态机流转**：

```
生成 → PENDING → ASSIGNED → PICKING → DELIVERING → COMPLETED
                                    ↘
                                     TIMEOUT (due_time 到期未完成)
```

**评分公式**：
- 完成得分：`100 + max(0, due_time - completed_time)`（提前完成有额外奖励）
- 超时惩罚：`-50`

### 3.2 车辆模型 (`Vehicle`)

```python
class Vehicle:
    status: VehicleStatus            # idle / moving / charging / waiting_charge
    current_node: int                # 当前所在图节点
    position: Tuple[float, float]    # 连续坐标（用于前端动画插值）
    current_battery: float           # 剩余电量
    current_load: float              # 当前载重
    action_plan: List[dict]          # 待执行动作队列
    current_path_nodes: List[int]    # 当前行进路径（节点序列）
    current_path_index: int          # 在路径中的当前位置
    progress: float                  # 当前路段进度 [0, 1)
    carrying_tasks: List[Task]       # 已装载但未完成的任务
```

**电量消耗模型**：

```
consumption_rate = consumption_empty + (consumption_full - consumption_empty) × (current_load / max_capacity)
实际消耗 = consumption_rate × 行驶距离
```

空载和满载的能耗率不同，负载越大耗电越快。

### 3.3 地图模型 (`TransportMap`)

基于 NetworkX 构建的网格图：
- 节点类型：`normal`（普通道路）、`depot`（仓库）、`station`（充电站）、`sub_depot`（子仓库）
- 边连接：上下左右四连通 + 40% 概率对角线连接
- 预计算： Floyd-Warshall 全局最短路径距离矩阵（加速调度器中的距离查询）

```python
def get_path(start, end) -> List[int]:
    """返回节点序列表示的最短路径"""

def get_distance(start, end) -> float:
    """返回预计算的最短距离"""

def find_nearest_station(node_id) -> int:
    """返回距离指定节点最近的充电站"""
```

### 3.4 充电站模型 (`ChargingStation`)

- 有限充电桩（slots），满时车辆进入等待队列
- 每 tick 为充电中车辆补充电量：`battery += charge_rate × dt`
- 充满后自动释放桩位，队列中下一辆车接入

---

## 4. 调度算法详解

调度器是系统的核心决策模块。所有调度器继承 `BaseScheduler`，实现统一的 `assign_task(task, fleet, map_obj)` 接口。

### 4.1 调度器抽象基类 (`BaseScheduler`)

**通用能力**（所有子类共享）：

| 方法 | 功能 |
|------|------|
| `check_capacity()` | 检查车辆剩余容量是否够装新任务（含已分配任务的预留负载） |
| `check_battery()` | 检查电量是否足够跑完全程（含安全余量） |
| `check_time_window()` | 检查能否在截止前到达 |
| `build_task_actions()` | 为任务构建动作序列：`pickup → move(depot) → deliver` |
| `refresh_vehicle_path()` | 根据 action_plan 重建车辆的完整路径节点序列 |
| `get_action_target()` | 解析动作的目标节点（静态方法，供 Simulator 复用） |

**动作序列设计**：

每个任务被分解为三个物理动作：
```python
[
    {"type": "pickup", "task": task},      # 到达取货点，装载货物
    {"type": "move", "target": depot_node},  # 返回仓库（途经仓库）
    {"type": "deliver", "task": task},       # 到达送货点，卸载货物
]
```

车辆按顺序执行 action_plan 中的动作，Simulator 负责推进执行。

### 4.2 最近优先调度 (Nearest First)

**核心思想**：每来一个新任务，分配给距离取货点最近的可用车辆。

```python
total_distance = dist(车辆当前位置, 取货点)
               + dist(取货点, 仓库)
               + dist(仓库, 送货点)

选择 total_distance 最小的车辆
```

**特点**：
- 贪婪策略，单次决策最优
- 不考虑车辆当前已有任务
- 不考虑任务重量差异
- 计算复杂度：O(n)，n 为车辆数

**适用场景**：任务分布均匀、车辆数量充足、负载差异小的场景。

### 4.3 最大重量优先调度 (Max Weight)

**核心思想**：重货优先分配给"强壮"的车辆（容量大、电量足），轻货可以分配给弱一点但距离近的车。

```python
efficiency = task.weight
           × (1 + remaining_capacity_ratio)
           × (0.8 + remaining_battery_ratio)
           ÷ (total_distance + 1)

选择 efficiency 最高的车辆
```

**公式解读**：
- `task.weight`：重量越大越需要优先分配（防止重货没人接）
- `(1 + remaining_capacity_ratio)`：剩余容量越多越优先（大车的容量红利）
- `(0.8 + remaining_battery_ratio)`：电量越充足越优先（避免派没电的车）
- `/(total_distance + 1)`：距离仍然是负向因素

**特点**：
- 复合评分，平衡了重量、容量、电量、距离四个维度
- 重货不会堆积到最后没人接
- 计算复杂度：O(n log n)（排序）

**适用场景**：任务重量差异大、车辆容量 heterogenous 的场景。

### 4.4 插入启发式调度 (Insertion) — 核心算法

**核心思想**：不只是在空车或末尾追加任务，而是在现有路线的**任意位置**插入新任务，使得总行驶距离增加最少。

**算法流程**：

```
对每个可用车辆:
    如果车辆没有任务:
        计算直接分配成本 = 车辆位置→取货点→仓库→送货点
    否则:
        对 pickup 插入位置 p_idx ∈ [0, n+1]:
            对 deliver 插入位置 d_idx ∈ [p_idx, n+2]:
                构建临时计划（在 p_idx 插入 pickup，在 d_idx 插入 deliver）
                模拟执行完整计划，计算总行驶距离
                记录最小成本及对应插入位置

选择成本最小的 (车辆, p_idx, d_idx) 执行插入
```

**双重循环复杂度**：若车辆已有 n 个动作，尝试的插入位置数为 `(n+1)(n+2)/2 ≈ O(n²/2)`。

**为什么优于前两种？**

| 场景 | 最近优先 | 插入启发式 |
|------|----------|-----------|
| 车 A 正在去东北方向执行任务 | 新东北任务可能分配给更近但去西南的车 B | 新任务插入车 A 的现有路线，顺路取货 |
| 多任务车辆 | 只能在末尾追加，路线可能绕远 | 在中间插入，动态优化整条路线 |

**边际成本计算**：

`_calculate_insertion_cost` 构建临时 action_plan，逐 action 模拟：
```python
current_node = vehicle.current_node
total_dist = 0
for action in new_plan:
    target = get_action_target(action)
    total_dist += get_distance(current_node, target)
    current_node = target
```

选择使 `total_dist` 最小的插入位置。若超出电量或容量约束，则该位置无效。

**适用场景**：任务密集、车辆复用率高、需要降低空驶率的场景。通常也是三种算法中综合表现最好的。

---

## 5. 仿真引擎主循环

### 5.1 每 tick 执行顺序

```python
def tick() -> dict:
    self.current_time += 1

    # 1. 生成新任务
    new_tasks = event_generator.generate(current_time)
    for task in new_tasks:
        scheduler.assign_task(task, fleet, map)
        if 未分配成功:
            task.status = PENDING

    # 2. 重试待分配任务
    for task in pending_tasks:
        scheduler.assign_task(task, fleet, map)

    # 3. 更新每辆车状态
    for vehicle in fleet:
        _update_vehicle(vehicle)

    # 4. 更新充电站
    for station in charging_stations:
        station.tick(dt)

    # 5. 检查超时
    for task in active_tasks:
        if current_time > task.due_time:
            task.status = TIMEOUT

    # 6. 低电量处理
    _handle_low_battery()

    # 7. 检查是否所有任务完成，触发返仓
    _check_return_phase()

    return state_snapshot
```

### 5.2 车辆状态更新 (`_update_vehicle`)

```
if status == MOVING:
    _update_moving(vehicle)
elif status == IDLE:
    如果没有任务且不在仓库:
        action_plan.append({depot_return})
    _execute_next_action(vehicle)
```

### 5.3 移动更新 (`_update_moving`)

车辆沿 `current_path_nodes` 移动：
1. 计算当前路段长度与所需电量
2. 推进 `progress`（按车速与段长比例）
3. 当 `progress >= 1.0`：到达下一节点
   - 更新 `current_node`
   - 扣除电量
   - `_consume_arrived_actions()`：消耗目标为当前节点的动作
   - `_sync_route_after_node()`：重新同步后续路线
4. 如果电量不足以到达下一站：紧急停车

### 5.4 动作执行 (`_execute_next_action`)

车辆 IDLE 且有 action_plan 时：
```
pop 第一个 action:
    pickup:   如果不在取货点 → 规划路径去取货点 → 设 MOVING
    deliver:  如果不在送货点 → 规划路径去送货点 → 设 MOVING
    move:     如果不在目标点 → 规划路径去目标点 → 设 MOVING
    charge:   去充电站排队/充电
    depot_return: 规划路径回仓库 → 设 MOVING
```

### 5.5 低电量处理策略

当车辆电量低于阈值时（`max(到最近充电站的往返消耗, 25% 最大电量)`）：
1. 查找最近的可用充电站
2. 在 action_plan 头部插入：`move(充电站) → charge`
3. 确保电量足以到达充电站（不足时强制补足到刚好够）

---
## 6. 事件生成器 (`EventGenerator`)

### 6.1 任务生成逻辑

在 `[1, time_horizon]` 范围内随机生成 `task_count` 个时间点：
- `ready_time = create_time`（生成即就绪）
- `due_time = create_time + random(500, 1200)`

**任务类型分布**：
- `single_task_ratio = 0.4`：40% 生成单点任务，60% 生成分拣派送任务
- 单点任务内部再 50/50 分配：
  - `depot_delivery`：仓库 → 服务节点
  - `sub_depot_return`：子仓库 → 仓库

### 6.2 三类任务的物理区别

| 任务类型 | pickup_node | delivery_node | 动作序列实际执行 |
|---------|------------|---------------|----------------|
| `paired`（分拣派送） | 随机服务节点 | 另一随机服务节点 | 取货 → 回仓库 → 送货 |
| `depot_delivery`（单点送货） | 仓库 | 随机服务节点 | 取货（在仓库，立即完成）→ 送货 |
| `sub_depot_return`（仓库取货） | 子仓库 | 仓库 | 取货 → 回仓库（即完成） |

虽然三种任务都复用 `pickup → move(depot) → deliver` 的动作序列模板，但由于 pickup/delivery 节点的特殊性，单点任务实际上只执行其中一部分：
- `depot_delivery`：车辆从仓库出发，pickup 动作在仓库立即完成，直接进入送货
- `sub_depot_return`：取货后回到仓库即完成，无需外部送货

---

## 7. 评价指标体系

### 7.1 核心指标

| 指标 | 计算方式 | 含义 |
|------|----------|------|
| 任务完成率 | completed / (completed + failed) | 成功率 |
| 平均完成用时 | avg(completed_time - ready_time) | 响应速度 |
| 单位任务距离 | total_distance / completed | 路线效率 |
| 总能耗 | sum(max_battery - current_battery) | 能源消耗 |
| 充电次数 | 充电站 start_charging 调用次数 | 充电频次 |
| 充电时间占比 | total_charging_time / sim_time | 停工充电比例 |
| 负载均衡标准差 | stdev(tasks_per_vehicle) | 任务分配均匀度 |
| 最终得分 | sum(任务得分) | 综合收益 |

### 7.2 对比实验设计

`/api/compare` 接口使用**控制变量法**：
- 相同的地图种子（seed）
- 相同的车辆配置
- 相同的任务序列
- 仅更换调度器类型

通过 `sim_speed = 1000` 和 `real_time_step = 0` 消除实时延迟，批量运行到仿真结束，保证对比的公平性。

---

## 8. 技术要点总结

### 8.1 关键设计决策

| 决策 | 方案 | 理由 |
|------|------|------|
| 离散事件 vs 连续仿真 | 离散 tick（每单位时间推进） | 实现简单，易于调试，足够展示调度策略差异 |
| 预计算最短路径 | Floyd-Warshall 全局距离矩阵 | 节点数少（~64），调度器频繁查询距离，预计算加速明显 |
| 动作队列设计 | `action_plan` + `current_path_nodes` 分离 | action_plan 是逻辑层（做什么），path 是物理层（怎么走），解耦便于插入优化 |
| 状态快照推送 | 每 tick 通过 SocketIO 推送完整状态 | 前端无需维护状态，实现简单；数据量小（几十辆车 + 百个任务） |

### 8.2 可扩展方向

1. **更多调度策略**：遗传算法、强化学习、蚁群算法等
2. **动态任务**：任务在仿真过程中实时生成（当前是预生成时间表）
3. **多仓库网络**：支持多个仓库之间的货物调拨
4. **时间窗硬约束**：当前只检查是否超时，可扩展为必须在时间窗内到达
5. **车辆异构**：不同车型（容量、电量、速度不同）
6. **真实地图数据**：接入 OpenStreetMap 等真实道路网络

### 8.3 文件结构速查

```
backend/
├── app.py                          # Flask + SocketIO 服务入口
├── models/
│   ├── task.py                     # 任务模型（三类任务 + 状态机）
│   ├── vehicle.py                  # 车辆模型（电量/负载/路径）
│   ├── transport_map.py            # 地图模型（NetworkX + 最短路径）
│   └── charging_station.py         # 充电站模型（排队 + 充放电）
├── scheduler/
│   ├── base_scheduler.py           # 调度器抽象基类
│   ├── nearest_first_scheduler.py  # 最近优先
│   ├── max_weight_scheduler.py     # 最大重量优先
│   └── insertion_scheduler.py      # 插入启发式（核心算法）
└── simulator/
    ├── simulator.py                # 主仿真引擎
    └── event_generator.py          # 任务事件生成器
```

---

*文档版本: 1.0 | 生成日期: 2026-05-28*
