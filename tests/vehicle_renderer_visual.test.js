const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync('frontend/js/vehicle_renderer.js', 'utf8');
const sandbox = { console };
vm.runInNewContext(`${source}\nthis.VehicleRenderer = VehicleRenderer;`, sandbox);

function makeRenderer() {
    const calls = [];
    const ctx = {
        save() {},
        restore() {},
        beginPath() {},
        moveTo(x, y) { calls.push(['moveTo', x, y]); },
        lineTo(x, y) { calls.push(['lineTo', x, y]); },
        arc(x, y) { calls.push(['arc', x, y]); },
        stroke() {},
        fill() {},
        fillText() {},
        setLineDash(value) { calls.push(['dash', value]); },
        set strokeStyle(value) { calls.push(['strokeStyle', value]); },
        set lineWidth(value) {},
        set fillStyle(value) {},
        set shadowBlur(value) {},
        set shadowColor(value) {},
        set font(value) {},
        set textAlign(value) {},
        set textBaseline(value) {},
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
    return { renderer: new sandbox.VehicleRenderer(ctx, mapRenderer), calls };
}

{
    const { renderer, calls } = makeRenderer();
    renderer.drawPath({
        id: 1,
        node: 1,
        position: [15, 5],
        path: [0, 1, 2, 3],
        path_index: 1,
        next_target: 3,
    });

    assert.deepStrictEqual(
        calls.find(([name]) => name === 'moveTo'),
        ['moveTo', 15, 5],
        'moving path should start at the vehicle position'
    );
    assert.deepStrictEqual(
        calls.filter(([name]) => name === 'lineTo'),
        [['lineTo', 20, 0], ['lineTo', 30, 0]],
        'moving path should only draw the untraveled path suffix'
    );
}

{
    const { renderer, calls } = makeRenderer();
    renderer.drawPath({
        id: 1,
        node: 1,
        position: [15, 5],
        path: [0, 1, 2, 3, 4],
        path_index: 1,
        route_target: 2,
        next_target: 4,
    });

    assert.deepStrictEqual(
        calls.filter(([name]) => name === 'lineTo'),
        [['lineTo', 20, 0]],
        'moving path should stop at the current route target instead of showing future delivery legs'
    );
}

{
    const { renderer, calls } = makeRenderer();
    renderer.updateVehicles([{
        id: 1,
        node: 0,
        position: [0, 0],
        battery_pct: 1,
        load_pct: 0,
        path: [],
    }]);
    renderer.render();
    renderer.updateVehicles([{
        id: 1,
        node: 3,
        position: [300, 0],
        battery_pct: 1,
        load_pct: 0,
        path: [3],
        status: 'moving',
    }]);
    renderer.render();

    const secondVehicleArc = calls.filter(([name]) => name === 'arc')[2];
    assert(secondVehicleArc[1] > 0, 'vehicle display position should move toward a new target');
    assert(secondVehicleArc[1] < 300, 'vehicle display position should smooth a large visual jump');
}

{
    const { renderer, calls } = makeRenderer();
    renderer.drawVehicle({
        id: 1,
        position: [0, 0],
        battery_pct: 1,
        load_pct: 0,
    });

    assert(
        calls.some(([name, value]) => name === 'strokeStyle' && value === '#27ae60'),
        'high battery indicator should use green instead of blue'
    );
}

{
    const { renderer, calls } = makeRenderer();
    renderer.drawPath({
        id: 1,
        node: 1,
        position: [10, 0],
        status: 'charging',
        path: [],
        next_target: 3,
    });

    assert.deepStrictEqual(
        calls.filter(([name]) => name === 'lineTo'),
        [],
        'charging vehicles should not draw a direct preview line to the next target'
    );
}
