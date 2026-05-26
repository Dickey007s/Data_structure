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
