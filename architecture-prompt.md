# EV Fleet Simulation System Architecture Diagram - SVG Prompt

Generate a clean, professional SVG system architecture diagram for an "EV Fleet Coordinated Scheduling Simulation System". Use a flat, modern design style with subtle shadows, rounded rectangles, and clear arrows.

## Layout Structure (Top to Bottom)

### Layer 1: FRONT END (Browser)
Position at top. Light blue background container (#e3f2fd).

**Components (inside FRONT END, arranged horizontally):**

1. **UI Controller** (`js/ui_controller.js`)
   - Central coordinator, slightly larger or highlighted
   - Receives user input from buttons/sliders
   - Dispatches commands to Socket.IO Client
   - Drives Canvas Renderer on each state update

2. **Socket.IO Client** (`js/socket_client.js`)
   - Receives `state_update` events (real-time simulation state)
   - Receives `simulation_finished` event
   - Emits `request_state` when needed
   - Pushes data to UI Controller

3. **Canvas 2D Renderer** (`js/map_renderer.js`, `vehicle_renderer.js`, `task_renderer.js`, `station_renderer.js`)
   - Renders: grid map, depot (orange), charging stations (green circles with queue count), vehicles (blue circles with ID), pickup markers (orange triangles), delivery markers (red squares), vehicle trajectory preview lines (dashed)

4. **Chart.js Dashboard** (`index.html` comparison panel)
   - Only activated for `/api/compare` results
   - 4 charts: completion rate, efficiency, energy, radar
   - Comparison table (IH vs NF vs MW)

**Arrows within FRONT END:**
- UI Controller --(click events)--> Socket.IO Client
- Socket.IO Client --(state data)--> UI Controller
- UI Controller --(render trigger)--> Canvas 2D Renderer
- UI Controller --(comparison data)--> Chart.js Dashboard

---

### Layer 2: COMMUNICATION LAYER (Middle)
Two separate, clearly labeled channels:

**Channel A: HTTP REST (left side, blue)**
- Static file serving: `GET /` → `index.html`, CSS, JS
- API endpoints:
  - `POST /api/config` → initialize simulation
  - `POST /api/start` → start background thread
  - `POST /api/pause` → pause
  - `POST /api/reset` → reset
  - `POST /api/compare` → batch run all 3 schedulers, return JSON
  - `GET /api/stats` → current statistics

**Channel B: Socket.IO WebSocket (right side, green)**
- Events FROM server:
  - `state_update` → pushes full simulation state each tick
  - `simulation_finished` → final score
- Events TO server:
  - `request_state` → client requests current state

**Visual separation:** Draw HTTP and Socket.IO as two distinct vertical arrows, not merged into one. Label them clearly.

---

### Layer 3: BACK END (Python Flask)
Position at bottom. Light gray background container (#f5f5f5).

**Architecture pattern:** Container (Flask App) wrapping an engine (Simulator), which orchestrates multiple subsystems.

**Outer Container:**
- **Flask App** (`app.py`): HTTP server + static file host + Socket.IO server instance. Creates and holds global `simulator` instance.

**Core Engine (inside Flask App):**
- **Simulator** (`simulator.py`, Tick Loop)
  - Runs in background `threading.Thread`
  - Main loop: `tick()` → advance time, generate tasks, update vehicles, update stations, check timeouts, handle low battery, check return phase, emit state
  - Holds references to: map, fleet, stations, scheduler, event_generator
  - Callbacks: `_emit_state` (to Socket.IO), `_emit_finished` (to Socket.IO)

**Subsystems (arranged below or beside Simulator):**

1. **Scheduler Engine** (`scheduler/`)
   - Strategy pattern: 3 implementations
   - `NearestFirstScheduler` (NF)
   - `MaxWeightScheduler` (MW)
   - `InsertionScheduler` (IH) — default
   - Interface: `assign_task(task, fleet, map) → bool`
   - Uses: TransportMap (distances, paths), Vehicle (capacity, battery, position)

2. **EventGenerator** (`event_generator.py`)
   - Generates task stream with time horizon
   - Deterministic with seed
   - Produces `Task` objects with pickup_node, delivery_node, weight, ready_time, due_time

3. **TransportMap** (`models/transport_map.py`)
   - NetworkX graph
   - Grid layout with jitter, depot at center, station nodes with 10% edge margin
   - Shortest path (Dijkstra) for routing
   - Cached distance matrix

4. **Vehicle** (`models/vehicle.py`)
   - FSM: IDLE → MOVING → LOADING → UNLOADING → CHARGING → WAITING_CHARGE
   - Battery: linear consumption based on distance × rate
   - Action plan queue: [pickup, move, deliver, charge, depot_return]
   - Carrying tasks list

5. **ChargingStation** (`models/charging_station.py`)
   - Fixed slots + FIFO queue
   - Fixed charge rate
   - `tick(interval)` → advance charging, return completed vehicles

6. **Task** (`models/task.py`)
   - Lifecycle: pending → assigned → picking → delivering → completed/timeout
   - Score: +100 + time_bonus if completed, -50 if timeout

**Dependency Arrows (BACK END internal):**
- Flask App --(creates & configures)--> Simulator
- Simulator --(calls per tick)--> Scheduler Engine
- Simulator --(calls per tick)--> EventGenerator
- Simulator --(calls per tick)--> ChargingStation.tick()
- Simulator --(reads/writes)--> TransportMap, Vehicle, Task
- Scheduler --(queries)--> TransportMap, Vehicle
- Vehicle --(updates state)--> Task

**Critical Flow (draw prominently):**
```
Flask App → Simulator.initialize() → Simulator.run() [thread]
  → tick() loop:
    1. EventGenerator.generate() → new Tasks
    2. Scheduler.assign_task() → Vehicle.action_plan
    3. _update_vehicle() → Vehicle.move() → battery--
    4. station.tick() → charging progress
    5. _handle_low_battery() → reroute to station
    6. _check_return_phase() → depot_return
    7. _emit_state() → Socket.IO → Frontend
```

---

## Color Scheme
- FRONT END container: #e3f2fd (light blue)
- BACK END container: #f5f5f5 (light gray)
- HTTP channel: #1976d2 (blue)
- Socket.IO channel: #388e3c (green)
- Simulator (core): #ff7043 (orange highlight)
- Scheduler: #7e57c2 (purple)
- Models (Map/Vehicle/Station/Task): #26a69a (teal)
- EventGenerator: #5c6bc0 (indigo)
- Flask App container: #424242 (dark gray border)
- Arrows: #616161, with direction markers

## Style Requirements
- Use rounded rectangles (rx="6" ry="6")
- Container boxes have dashed borders
- Component boxes have solid borders
- Arrow labels in small text above or beside arrows
- Group related components visually (subsystems clustered)
- Leave adequate whitespace between layers
- Title at top: "EV Fleet Scheduling Simulation — System Architecture"
- Figure caption at bottom
