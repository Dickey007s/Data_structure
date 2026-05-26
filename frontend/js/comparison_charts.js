/**
 * ComparisonCharts - Render benchmark results with Chart.js
 */

const STRATEGY_LABELS = {
    nearest: '最近优先',
    max_weight: '最大重量优先',
    insertion: '插入启发式',
    global_or: 'OR-Tools 全局最优'
};

const STRATEGY_COLORS = {
    nearest: { bg: 'rgba(233, 69, 96, 0.7)', border: '#e94560' },
    max_weight: { bg: 'rgba(249, 168, 38, 0.7)', border: '#f9a826' },
    insertion: { bg: 'rgba(0, 217, 255, 0.7)', border: '#00d9ff' },
    global_or: { bg: 'rgba(0, 255, 136, 0.7)', border: '#00ff88' }
};

let charts = {};

function showComparisonModal() {
    document.getElementById('compare-modal').style.display = 'flex';
    document.getElementById('compare-loading').style.display = 'block';
    document.getElementById('compare-results').style.display = 'none';
}

function hideComparisonModal() {
    document.getElementById('compare-modal').style.display = 'none';
}

function setComparisonStatus(text) {
    document.getElementById('compare-status').textContent = text;
}

function showComparisonResults() {
    document.getElementById('compare-loading').style.display = 'none';
    document.getElementById('compare-results').style.display = 'block';
}

function destroyCharts() {
    Object.values(charts).forEach(c => c.destroy());
    charts = {};
}

function renderAllCharts(results) {
    destroyCharts();
    renderMetricsTable(results);
    renderCompletionChart(results);
    renderDistanceChart(results);
    renderChargingChart(results);
    renderRadarChart(results);
}

function renderMetricsTable(results) {
    const strategies = ['nearest', 'max_weight', 'insertion', 'global_or'];
    const rows = [
        { key: 'strategy_name', label: '策略名称', fmt: v => v },
        { key: 'completion_rate', label: '完成率', fmt: v => (v * 100).toFixed(1) + '%' },
        { key: 'failure_rate', label: '失败率', fmt: v => (v * 100).toFixed(1) + '%' },
        { key: 'total_distance', label: '总行驶距离', fmt: v => v.toFixed(0) },
        { key: 'avg_completion_time', label: '平均完成时间', fmt: v => v.toFixed(1) },
        { key: 'avg_wait_time', label: '平均等待时间', fmt: v => v.toFixed(1) },
        { key: 'total_charging_time', label: '总充电时间', fmt: v => v.toFixed(1) },
        { key: 'charging_count', label: '充电次数', fmt: v => v },
        { key: 'avg_utilization', label: '车辆利用率', fmt: v => (v * 100).toFixed(1) + '%' },
        { key: 'score', label: '总得分', fmt: v => v.toFixed(0) },
    ];

    // Find best values (lower is better for distance, time, failure; higher for completion, utilization, score)
    const higherIsBetter = ['completion_rate', 'avg_utilization', 'score', 'strategy_name'];
    const bestValues = {};
    rows.forEach(row => {
        const values = strategies.map(s => results[s][row.key]).filter(v => typeof v === 'number');
        if (values.length === 0) return;
        if (higherIsBetter.includes(row.key)) {
            bestValues[row.key] = Math.max(...values);
        } else {
            bestValues[row.key] = Math.min(...values);
        }
    });

    let html = '<thead><tr><th>指标</th>';
    strategies.forEach(s => {
        html += `<th>${STRATEGY_LABELS[s]}</th>`;
    });
    html += '</tr></thead><tbody>';

    rows.forEach(row => {
        html += `<tr><td>${row.label}</td>`;
        strategies.forEach(s => {
            const val = results[s][row.key];
            let cellClass = '';
            if (typeof val === 'number' && bestValues[row.key] !== undefined) {
                const isBest = Math.abs(val - bestValues[row.key]) < 0.001;
                cellClass = isBest ? 'metric-best' : '';
                // Highlight insertion if it's close to or better than global_or
                if (s === 'insertion' && !isBest) {
                    const globalVal = results['global_or'][row.key];
                    if (globalVal !== undefined) {
                        const diff = higherIsBetter.includes(row.key) ? val - globalVal : globalVal - val;
                        if (diff >= -0.001) cellClass = 'metric-good';
                    }
                }
            }
            html += `<td class="${cellClass}">${row.fmt(val)}</td>`;
        });
        html += '</tr>';
    });

    html += '</tbody>';
    document.getElementById('metrics-table').innerHTML = html;
}

function renderCompletionChart(results) {
    const ctx = document.getElementById('chart-completion').getContext('2d');
    const strategies = ['nearest', 'max_weight', 'insertion', 'global_or'];

    charts.completion = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: strategies.map(s => STRATEGY_LABELS[s]),
            datasets: [
                {
                    label: '完成率 (%)',
                    data: strategies.map(s => (results[s].completion_rate * 100).toFixed(1)),
                    backgroundColor: strategies.map(s => STRATEGY_COLORS[s].bg),
                    borderColor: strategies.map(s => STRATEGY_COLORS[s].border),
                    borderWidth: 1
                },
                {
                    label: '失败率 (%)',
                    data: strategies.map(s => (results[s].failure_rate * 100).toFixed(1)),
                    backgroundColor: strategies.map(() => 'rgba(233, 69, 96, 0.3)'),
                    borderColor: strategies.map(() => '#e94560'),
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { color: '#eaeaea' } } },
            scales: {
                y: { beginAtZero: true, max: 100, ticks: { color: '#a0a0a0' }, grid: { color: '#2d3561' } },
                x: { ticks: { color: '#a0a0a0' }, grid: { display: false } }
            }
        }
    });
}

function renderDistanceChart(results) {
    const ctx = document.getElementById('chart-distance').getContext('2d');
    const strategies = ['nearest', 'max_weight', 'insertion', 'global_or'];

    charts.distance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: strategies.map(s => STRATEGY_LABELS[s]),
            datasets: [{
                label: '总行驶距离',
                data: strategies.map(s => results[s].total_distance),
                backgroundColor: strategies.map(s => STRATEGY_COLORS[s].bg),
                borderColor: strategies.map(s => STRATEGY_COLORS[s].border),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { color: '#eaeaea' } } },
            scales: {
                y: { beginAtZero: true, ticks: { color: '#a0a0a0' }, grid: { color: '#2d3561' } },
                x: { ticks: { color: '#a0a0a0' }, grid: { display: false } }
            }
        }
    });
}

function renderChargingChart(results) {
    const ctx = document.getElementById('chart-charging').getContext('2d');
    const strategies = ['nearest', 'max_weight', 'insertion', 'global_or'];

    charts.charging = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: strategies.map(s => STRATEGY_LABELS[s]),
            datasets: [
                {
                    label: '总充电时间',
                    data: strategies.map(s => results[s].total_charging_time),
                    backgroundColor: strategies.map(() => 'rgba(249, 168, 38, 0.6)'),
                    borderColor: strategies.map(() => '#f9a826'),
                    borderWidth: 1
                },
                {
                    label: '充电次数',
                    data: strategies.map(s => results[s].charging_count),
                    backgroundColor: strategies.map(() => 'rgba(0, 217, 255, 0.6)'),
                    borderColor: strategies.map(() => '#00d9ff'),
                    borderWidth: 1,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { color: '#eaeaea' } } },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: '#a0a0a0' },
                    grid: { color: '#2d3561' },
                    position: 'left'
                },
                y1: {
                    beginAtZero: true,
                    ticks: { color: '#a0a0a0' },
                    grid: { display: false },
                    position: 'right'
                },
                x: { ticks: { color: '#a0a0a0' }, grid: { display: false } }
            }
        }
    });
}

function renderRadarChart(results) {
    const ctx = document.getElementById('chart-radar').getContext('2d');
    const strategies = ['nearest', 'max_weight', 'insertion', 'global_or'];

    // Normalize metrics to 0-100 scale for radar
    function normalize(value, min, max) {
        if (max === min) return 50;
        return Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100));
    }

    const dims = [
        { key: 'completion_rate', label: '完成率', higherBetter: true },
        { key: 'avg_utilization', label: '利用率', higherBetter: true },
        { key: 'score', label: '总得分', higherBetter: true },
    ];
    // Invert distance, wait_time, failure_rate for radar (lower is better)
    const invertKeys = ['total_distance', 'avg_wait_time', 'failure_rate'];

    const datasets = strategies.map(s => {
        const data = dims.map(dim => {
            const values = strategies.map(ss => results[ss][dim.key]);
            const min = Math.min(...values);
            const max = Math.max(...values);
            return normalize(results[s][dim.key], min, max);
        });
        return {
            label: STRATEGY_LABELS[s],
            data,
            backgroundColor: STRATEGY_COLORS[s].bg,
            borderColor: STRATEGY_COLORS[s].border,
            borderWidth: 2,
            pointBackgroundColor: STRATEGY_COLORS[s].border
        };
    });

    charts.radar = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: dims.map(d => d.label),
            datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { color: '#eaeaea' } } },
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { color: '#a0a0a0', backdropColor: 'transparent' },
                    grid: { color: '#2d3561' },
                    pointLabels: { color: '#a0a0a0' }
                }
            }
        }
    });
}
