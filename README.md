# 新能源物流车队协同调度仿真平台

> 课程大作业：基于离散事件仿真的新能源物流车队动态调度系统，支持多种调度策略对比与可视化展示。

## 功能特性

- **动态任务生成**：任务按时间逐步释放，包含取货点、送货点、货物重量、时间窗约束
- **三种调度策略**：
  - **最近优先 (Nearest First)**：将任务分配给距离最近的车辆
  - **最大重量优先 (Max Weight)**：优先分配重量大的任务
  - **插入启发式 (Insertion)**：基于路径插入成本选择最优车辆和位置
- **新能源建模**：
  - 车辆空载/满载差异化电耗
  - 实时电量监测与低电量自动充电
  - 充电站排队与多桩位管理
- **可视化仿真**：
  - 前端 Canvas 实时渲染车辆移动、任务状态、充电站负荷
  - 运行日志与实时统计面板
  - Socket.IO 实时推送仿真状态
- **评分系统**：任务完成越早、路径越短得分越高，超时未完成则扣分

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.13 + Flask + Flask-SocketIO |
| 前端 | 原生 HTML5 + Canvas API + Socket.IO Client |
| 算法 | NetworkX（最短路径）+ 自定义离散事件仿真引擎 |
| 样式 | 纯 CSS（Dark Theme） |

## 项目结构

```
.
├── backend/
│   ├── app.py                      # Flask + SocketIO 主服务
│   ├── requirements.txt            # Python 依赖
│   ├── models/
│   │   ├── vehicle.py              # 车辆模型（电量、载重、状态机）
│   │   ├── task.py                 # 任务模型（时间窗、重量、状态）
│   │   ├── charging_station.py     # 充电站模型（排队、多桩位）
│   │   └── transport_map.py        # 地图模型（图结构、最短路径）
│   ├── scheduler/
│   │   ├── base_scheduler.py       # 调度器抽象基类
│   │   ├── nearest_first_scheduler.py
│   │   ├── max_weight_scheduler.py
│   │   └── insertion_scheduler.py  # 路径插入启发式
│   └── simulator/
│       ├── simulator.py            # 离散事件仿真引擎主循环
│       └── event_generator.py      # 动态任务生成器
├── frontend/
│   ├── index.html                  # 主页面
│   ├── css/styles.css              # 暗色主题样式
│   └── js/
│       ├── socket_client.js        # Socket.IO 通信
│       ├── map_renderer.js         # 地图/道路 Canvas 渲染
│       ├── vehicle_renderer.js     # 车辆动画渲染
│       ├── task_renderer.js        # 任务点渲染
│       ├── station_renderer.js     # 充电站渲染
│       └── ui_controller.js        # UI 交互与渲染循环
└── docs/
    ├── 2026-大作业要求.txt
    ├── proposal.md
    └── images/                      # 设计稿/截图
```

## 快速开始

### 环境要求

- Python >= 3.10
- pip

### 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

依赖列表：
- flask >= 3.0.0
- flask-socketio >= 5.3.0
- flask-cors >= 4.0.0
- networkx >= 3.2.1
- numpy >= 2.0.0
- python-socketio >= 5.9.0

### 启动服务

```bash
cd backend
python app.py
```

服务启动后，打开浏览器访问 `http://localhost:5000`

### 使用说明

1. 在左侧面板设置**车辆数量**、**任务数量**、**仿真速度**和**调度策略**
2. 点击**初始化**生成地图和任务
3. 点击**开始**运行仿真
4. 观察 Canvas 中车辆移动、任务完成情况和充电站状态
5. 点击**重置**清空当前仿真，可切换策略重新实验

## 调度策略说明

### 1. 最近优先 (Nearest First)

为每个新任务计算所有车辆当前位置到取货点的距离，选择最近车辆进行分配。车辆按 FIFO 顺序依次执行任务。

**特点**：响应快，适合任务分布均匀的场景。

### 2. 最大重量优先 (Max Weight)

优先将重量大的任务分配给当前可用的车辆。与最近优先相同，按 FIFO 执行。

**特点**：优先完成高收益任务，但可能牺牲小任务的完成率。

### 3. 插入启发式 (Insertion)

对每辆车的现有路径，尝试在任意位置插入新任务的取货点和送货点，计算插入后的额外行驶距离，选择使增量成本最小的车辆和插入位置。

**特点**：路径优化能力最强，能有效减少空驶和重复路径。

## 评分规则

- 任务在 `due_time` 之前完成：获得正分（与时间、重量相关）
- 任务超过 `due_time` 未完成：标记为超时，扣除相应分数
- 总得分实时显示在页面顶部状态栏

## 仿真参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 车辆数 | 10 | 1–20 |
| 任务数 | 100 | 10–500 |
| 仿真速度 | 1x | 0.5x–10x |
| 地图节点数 | 30 | 道路网络节点 |
| 车辆电量 | 800 | 单位容量 |
| 车辆载重 | 50 | 单位容量 |
| 空载电耗 | 0.05 | 每单位距离 |
| 满载电耗 | 0.10 | 每单位距离 |

## 核心设计

### 车辆状态机

```
IDLE -> MOVING -> IDLE
  |        |
  v        v
CHARGING  LOADING -> DELIVERING
```

### 低电量处理

当车辆电量低于以下阈值时，自动规划前往最近充电站：
- 到达最近充电站所需电量的 2 倍
- 或低于最大电量的 25%

### 充电站排队

充电站支持多车辆同时充电（默认 2 桩位），满员时车辆进入等待队列。

## 作者

课程大作业小组

## License

MIT
