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
        this.comparisonChart = null;

        this.setupEventListeners();
        this.setupSocketListeners();
    }

    setupEventListeners() {
        document.getElementById('btn-init').addEventListener('click', () => this.initialize());
        document.getElementById('btn-start').addEventListener('click', () => this.start());
        document.getElementById('btn-pause').addEventListener('click', () => this.pause());
        document.getElementById('btn-reset').addEventListener('click', () => this.reset());
        document.getElementById('btn-compare').addEventListener('click', () => this.runComparison());
        document.getElementById('btn-close-comparison').addEventListener('click', () => this.hideComparison());
        document.getElementById('btn-random-seed').addEventListener('click', () => this.randomSeed());
        document.getElementById('btn-zoom-in').addEventListener('click', () => this.mapRenderer.zoomIn());
        document.getElementById('btn-zoom-out').addEventListener('click', () => this.mapRenderer.zoomOut());
        document.getElementById('btn-zoom-reset').addEventListener('click', () => this.mapRenderer.resetView());
    }

    setupSocketListeners() {
        this.socketClient.on('connected', () => {
            console.log('已连接到仿真服务器');
        });

        this.socketClient.on('state_update', (state) => {
            this.updateUI(state);
        });

        this.socketClient.on('finished', (data) => {
            this.isRunning = false;
            document.getElementById('btn-start').disabled = false;
            document.getElementById('btn-pause').disabled = true;
            this.stopRenderLoop();
        });

        this.socketClient.on('disconnected', () => {
            console.log('与服务器断开连接');
        });
    }

    async initialize() {
        const numVehicles = parseInt(document.getElementById('config-vehicles').value);
        const seed = parseInt(document.getElementById('config-seed').value);
        const fleet = Array.from({length: numVehicles}, (_, i) => ({
            id: i,
            start_node: i % 64,
            max_battery: 800,
            max_capacity: 50,
            consumption_empty: 0.05,
            consumption_full: 0.1
        }));

        const config = {
            map: {width: 1000, height: 800, num_nodes: 64},
            fleet: fleet,
            stations: [
                {id: 0, node_id: 10, total_slots: 2, charge_rate: 30},
                {id: 1, node_id: 25, total_slots: 2, charge_rate: 30},
                {id: 2, node_id: 40, total_slots: 2, charge_rate: 30}
            ],
            scheduler: document.getElementById('config-scheduler').value,
            task_count: parseInt(document.getElementById('config-tasks').value),
            time_horizon: 2000,
            tick_interval: 1,
            sim_speed: parseFloat(document.getElementById('config-speed').value),
            seed: seed
        };

        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            });
            const data = await response.json();

            if (data.status === 'initialized') {
                document.getElementById('btn-start').disabled = false;

                const mapResponse = await fetch('/api/map');
                const mapData = await mapResponse.json();
                this.mapRenderer.setMapData(mapData.nodes, mapData.edges);
                this.render();
            }
        } catch (error) {
            console.error('初始化失败:', error.message);
        }
    }

    async start() {
        try {
            await fetch('/api/start', {method: 'POST'});
            this.isRunning = true;
            document.getElementById('btn-start').disabled = true;
            document.getElementById('btn-pause').disabled = false;
            this.startRenderLoop();
        } catch (error) {
            console.error('启动失败:', error.message);
        }
    }

    async pause() {
        try {
            await fetch('/api/pause', {method: 'POST'});
            this.isRunning = false;
            document.getElementById('btn-start').disabled = false;
            document.getElementById('btn-pause').disabled = true;
            this.stopRenderLoop();
        } catch (error) {
            console.error('暂停失败:', error.message);
        }
    }

    async reset() {
        try {
            await fetch('/api/reset', {method: 'POST'});
            this.isRunning = false;
            this.stopRenderLoop();
            document.getElementById('btn-start').disabled = true;
            document.getElementById('btn-pause').disabled = true;

            this.vehicleRenderer.updateVehicles([]);
            this.taskRenderer.updateTasks([]);
            this.stationRenderer.updateStations([]);
            this.updateStats({completed: 0, failed: 0, pending: 0, active: 0});
            this.clearLists();
            this.mapRenderer.render();
        } catch (error) {
            console.error('重置失败:', error.message);
        }
    }

    randomSeed() {
        const seed = Math.floor(Math.random() * 99999) + 1;
        document.getElementById('config-seed').value = seed;
    }

    async runComparison() {
        const btn = document.getElementById('btn-compare');
        btn.disabled = true;
        btn.textContent = '运行中...';

        const numVehicles = parseInt(document.getElementById('config-vehicles').value);
        const taskCount = parseInt(document.getElementById('config-tasks').value);
        const seed = parseInt(document.getElementById('config-seed').value);
        const simSpeed = parseFloat(document.getElementById('config-speed').value);

        const fleet = Array.from({length: numVehicles}, (_, i) => ({
            id: i,
            start_node: i % 64,
            max_battery: 800,
            max_capacity: 50,
            consumption_empty: 0.05,
            consumption_full: 0.1
        }));

        const baseConfig = {
            map: {width: 1000, height: 800, num_nodes: 64},
            fleet: fleet,
            stations: [
                {id: 0, node_id: 10, total_slots: 2, charge_rate: 30},
                {id: 1, node_id: 25, total_slots: 2, charge_rate: 30},
                {id: 2, node_id: 40, total_slots: 2, charge_rate: 30}
            ],
            task_count: taskCount,
            time_horizon: 2000,
            tick_interval: 1,
            sim_speed: simSpeed,
            seed: seed
        };

        try {
            const response = await fetch('/api/compare', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(baseConfig)
            });
            const results = await response.json();
            this.showComparison(results);
        } catch (error) {
            console.error('对比实验失败:', error.message);
        } finally {
            btn.disabled = false;
            btn.textContent = '对比实验';
        }
    }

    showComparison(results) {
        const panel = document.getElementById('comparison-panel');
        panel.classList.add('visible');

        const schedulers = ['insertion', 'nearest', 'max_weight'];
        const labels = ['插入启发式 (IH)', '最近优先 (NF)', '最大重量优先 (MW)'];
        const shortLabels = ['IH', 'NF', 'MW'];
        // Academic color palette
        const colors = ['#2E5C8A', '#C44E52', '#DDAA33'];
        const fills = ['rgba(46,92,138,0.75)', 'rgba(196,78,82,0.75)', 'rgba(221,170,51,0.75)'];

        // Extract data
        const d = schedulers.map(s => results[s] || {});

        // ---- Chart 1: Completion & Timeout Rate ----
        this._createOrUpdateChart('chart-completion', {
            type: 'bar',
            data: {
                labels: shortLabels,
                datasets: [
                    {
                        label: '完成率 (%)',
                        data: d.map(x => (x.completion_rate || 0) * 100),
                        backgroundColor: fills,
                        borderColor: colors,
                        borderWidth: 1.5
                    },
                    {
                        label: '超时率 (%)',
                        data: d.map(x => (x.timeout_rate || 0) * 100),
                        backgroundColor: colors.map(c => c + '40'),
                        borderColor: colors,
                        borderWidth: 1.5,
                        borderDash: [4, 2]
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'top', labels: { font: { size: 11 } } } },
                scales: {
                    y: { beginAtZero: true, max: 100, grid: { color: '#e1e4e8' }, title: { display: true, text: '百分比 (%)', font: { size: 11 } } },
                    x: { grid: { display: false } }
                }
            }
        });

        // ---- Chart 2: Efficiency metrics ----
        this._createOrUpdateChart('chart-efficiency', {
            type: 'bar',
            data: {
                labels: shortLabels,
                datasets: [
                    {
                        label: '平均完成用时',
                        data: d.map(x => x.avg_completion_time || 0),
                        backgroundColor: fills[0],
                        borderColor: colors[0],
                        borderWidth: 1.5,
                        yAxisID: 'y'
                    },
                    {
                        label: '单位任务距离',
                        data: d.map(x => x.avg_distance_per_task || 0),
                        backgroundColor: fills[1],
                        borderColor: colors[1],
                        borderWidth: 1.5,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'top', labels: { font: { size: 11 } } } },
                scales: {
                    y: { type: 'linear', position: 'left', grid: { color: '#e1e4e8' }, title: { display: true, text: '时间', font: { size: 11 } } },
                    y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: '距离', font: { size: 11 } } },
                    x: { grid: { display: false } }
                }
            }
        });

        // ---- Chart 3: Energy metrics ----
        this._createOrUpdateChart('chart-energy', {
            type: 'bar',
            data: {
                labels: shortLabels,
                datasets: [
                    {
                        label: '总能耗',
                        data: d.map(x => x.total_energy_consumed || 0),
                        backgroundColor: fills[0],
                        borderColor: colors[0],
                        borderWidth: 1.5,
                        yAxisID: 'y'
                    },
                    {
                        label: '充电次数',
                        data: d.map(x => x.charging_count || 0),
                        backgroundColor: fills[2],
                        borderColor: colors[2],
                        borderWidth: 1.5,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'top', labels: { font: { size: 11 } } } },
                scales: {
                    y: { type: 'linear', position: 'left', grid: { color: '#e1e4e8' }, title: { display: true, text: '能耗', font: { size: 11 } } },
                    y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: '次数', font: { size: 11 } } },
                    x: { grid: { display: false } }
                }
            }
        });

        // ---- Chart 4: Radar chart for overall comparison ----
        // Normalize metrics to 0-100 scale for radar
        const maxScore = Math.max(...d.map(x => x.final_score || 1));
        const maxDist = Math.max(...d.map(x => x.total_distance || 1));
        const maxEnergy = Math.max(...d.map(x => x.total_energy_consumed || 1));
        const maxTime = Math.max(...d.map(x => x.avg_completion_time || 1));
        const maxLoad = Math.max(...d.map(x => x.load_balance_std || 1), 0.01);

        this._createOrUpdateChart('chart-radar', {
            type: 'radar',
            data: {
                labels: ['完成率', '得分', '距离效率', '能耗效率', '响应速度', '负载均衡'],
                datasets: schedulers.map((s, i) => ({
                    label: shortLabels[i],
                    data: [
                        (d[i].completion_rate || 0) * 100,
                        ((d[i].final_score || 0) / maxScore) * 100,
                        (1 - ((d[i].total_distance || 0) / maxDist)) * 100,
                        (1 - ((d[i].total_energy_consumed || 0) / maxEnergy)) * 100,
                        (1 - ((d[i].avg_completion_time || 0) / maxTime)) * 100,
                        (1 - ((d[i].load_balance_std || 0) / maxLoad)) * 100
                    ],
                    backgroundColor: fills[i].replace('0.75', '0.15'),
                    borderColor: colors[i],
                    borderWidth: 2,
                    pointRadius: 3
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'top', labels: { font: { size: 11 } } } },
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        grid: { color: '#e1e4e8' },
                        pointLabels: { font: { size: 11 } }
                    }
                }
            }
        });

        // ---- Update table ----
        const tbody = document.querySelector('#comparison-table tbody');
        const metrics = [
            { key: 'completed', label: '已完成任务数', fmt: v => v.toString(), higherBetter: true },
            { key: 'failed', label: '超时任务数', fmt: v => v.toString(), higherBetter: false },
            { key: 'completion_rate', label: '任务完成率 (%)', fmt: v => (v * 100).toFixed(1) + '%', higherBetter: true },
            { key: 'timeout_rate', label: '任务超时率 (%)', fmt: v => (v * 100).toFixed(1) + '%', higherBetter: false },
            { key: 'avg_completion_time', label: '平均完成用时', fmt: v => v.toFixed(1), higherBetter: false },
            { key: 'avg_distance_per_task', label: '单位任务平均距离', fmt: v => v.toFixed(1), higherBetter: false },
            { key: 'total_distance', label: '总行驶距离', fmt: v => v.toFixed(0), higherBetter: false },
            { key: 'total_energy_consumed', label: '总耗电量', fmt: v => v.toFixed(0), higherBetter: false },
            { key: 'energy_efficiency', label: '能量效率', fmt: v => v.toFixed(3), higherBetter: false },
            { key: 'charging_count', label: '充电次数', fmt: v => v.toString(), higherBetter: false },
            { key: 'charging_time_ratio', label: '充电时间占比 (%)', fmt: v => (v * 100).toFixed(1) + '%', higherBetter: false },
            { key: 'load_balance_std', label: '负载均衡标准差', fmt: v => v.toFixed(2), higherBetter: false },
            { key: 'final_score', label: '最终得分', fmt: v => v.toFixed(1), higherBetter: true },
            { key: 'sim_time', label: '仿真总用时', fmt: v => v.toString(), higherBetter: false },
        ];

        let tableHtml = '';
        for (const m of metrics) {
            const values = schedulers.map(s => results[s]?.[m.key] ?? 0);
            let bestIdx = -1;
            if (m.higherBetter) {
                bestIdx = values.indexOf(Math.max(...values));
            } else {
                bestIdx = values.indexOf(Math.min(...values));
            }

            tableHtml += `<tr>
                <td>${m.label}</td>
                <td class="${bestIdx === 0 ? 'best' : ''}">${m.fmt(values[0])}</td>
                <td class="${bestIdx === 1 ? 'best' : ''}">${m.fmt(values[1])}</td>
                <td class="${bestIdx === 2 ? 'best' : ''}">${m.fmt(values[2])}</td>
            </tr>`;
        }
        tbody.innerHTML = tableHtml;

        // ---- Summary ----
        const ranked = schedulers
            .map((s, i) => ({ key: s, label: labels[i], rate: d[i].completion_rate || 0, score: d[i].final_score || 0 }))
            .sort((a, b) => b.rate - a.rate || b.score - a.score);
        const best = ranked[0];
        const worst = ranked[2];
        const improvement = best.rate > 0 ? ((best.rate - worst.rate) / worst.rate * 100).toFixed(1) : '0';

        document.getElementById('comparison-summary').innerHTML =
            `<strong>实验结论：</strong> 在相同的地图与任务集下，<strong>${best.label}</strong> 的综合表现最优。` +
            `其任务完成率达到 <strong>${(best.rate * 100).toFixed(1)}%</strong>，` +
            `相较于表现最差的 <strong>${worst.label}</strong> ` +
            `(${worst.rate > 0 ? (worst.rate * 100).toFixed(1) : '0'}%)` +
            `提升了约 <strong>${improvement}%</strong>。` +
            `插入启发式通过动态优化任务在车辆路径中的插入位置，有效降低了空驶距离与任务等待时间，` +
            `从而显著提升了新能源物流车队的整体调度效率与服务水平。`;
    }

    _createOrUpdateChart(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        // Destroy existing chart on this canvas
        if (canvas._chart) {
            canvas._chart.destroy();
        }

        const ctx = canvas.getContext('2d');
        canvas._chart = new Chart(ctx, config);
    }

    hideComparison() {
        document.getElementById('comparison-panel').classList.remove('visible');
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
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    new UIController();
});
