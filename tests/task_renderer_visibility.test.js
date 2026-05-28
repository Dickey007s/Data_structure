const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync('frontend/js/task_renderer.js', 'utf8');
const sandbox = { console };
vm.runInNewContext(`${source}\nthis.TaskRenderer = TaskRenderer;`, sandbox);

function makeRenderer() {
    const calls = [];
    const ctx = {
        save() { calls.push(['save']); },
        restore() { calls.push(['restore']); },
        beginPath() {},
        moveTo() {},
        lineTo() {},
        closePath() {},
        fill() { calls.push(['fill']); },
        fillRect() { calls.push(['fillRect']); },
        stroke() { calls.push(['stroke']); },
        setLineDash() {},
        set fillStyle(value) {},
        set shadowBlur(value) {},
        set shadowColor(value) {},
        set strokeStyle(value) {},
        set lineWidth(value) {},
    };
    const mapRenderer = {
        scale: 1,
        getNodePosition(nodeId) {
            return [nodeId * 10, 0];
        },
        worldToScreen(x, y) {
            return { x, y };
        },
    };
    return { renderer: new sandbox.TaskRenderer(ctx, mapRenderer), calls };
}

function drawStatus(status) {
    const { renderer, calls } = makeRenderer();
    renderer.updateTasks([{ id: 1, pickup: 1, delivery: 2, status }]);
    renderer.render();
    return calls.map(([name]) => name);
}

assert(drawStatus('assigned').includes('fill'), 'assigned task should draw pickup marker');
assert(!drawStatus('assigned').includes('fillRect'), 'assigned task should not draw delivery marker');
assert(!drawStatus('picking').includes('fillRect'), 'picking task should not draw delivery marker before depot return');
assert(drawStatus('delivering').includes('fillRect'), 'delivering task should draw delivery marker');
assert(!drawStatus('completed').includes('fillRect'), 'completed task should not draw delivery marker');

function drawTask(task) {
    const { renderer, calls } = makeRenderer();
    renderer.updateTasks([task]);
    renderer.render();
    return calls.map(([name]) => name);
}

assert(
    drawTask({
        id: 2,
        pickup: 0,
        delivery: 5,
        status: 'assigned',
        task_type: 'depot_delivery',
    }).includes('fillRect'),
    'depot delivery task should show its delivery point while assigned'
);
assert(
    !drawTask({
        id: 2,
        pickup: 0,
        delivery: 5,
        status: 'assigned',
        task_type: 'depot_delivery',
    }).includes('fill'),
    'depot delivery task should not show a pickup marker at the main depot'
);
assert(
    drawTask({
        id: 3,
        pickup: 2,
        delivery: 0,
        status: 'assigned',
        task_type: 'sub_depot_return',
    }).includes('fill'),
    'sub-depot return task should show the sub-depot pickup point while assigned'
);
assert(
    !drawTask({
        id: 3,
        pickup: 2,
        delivery: 0,
        status: 'picking',
        task_type: 'sub_depot_return',
    }).includes('fillRect'),
    'sub-depot return task should not show a delivery marker at the main depot'
);
