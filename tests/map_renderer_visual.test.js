const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync('frontend/js/map_renderer.js', 'utf8');
const sandbox = { console };
vm.runInNewContext(`${source}\nthis.MapRenderer = MapRenderer;`, sandbox);

const calls = [];
const ctx = {
    save() {},
    restore() {},
    beginPath() { calls.push(['beginPath']); },
    moveTo(x, y) { calls.push(['moveTo', x, y]); },
    lineTo(x, y) { calls.push(['lineTo', x, y]); },
    closePath() { calls.push(['closePath']); },
    arc(x, y) { calls.push(['arc', x, y]); },
    fill() { calls.push(['fill']); },
    stroke() {},
    fillText() {},
    set fillStyle(value) { calls.push(['fillStyle', value]); },
    set shadowColor(value) { calls.push(['shadowColor', value]); },
    set shadowBlur(value) {},
    set font(value) {},
    set textAlign(value) {},
    set textBaseline(value) {},
};

const renderer = Object.create(sandbox.MapRenderer.prototype);
renderer.ctx = ctx;
renderer.nodes = [{ id: 0, x: 10, y: 20, type: 'depot' }];
renderer.scale = 1;
renderer.offsetX = 0;
renderer.offsetY = 0;
renderer.worldToScreen = (x, y) => ({ x, y });

renderer.drawNodes();

assert(
    calls.some(([name, value]) => name === 'fillStyle' && value === '#8e44ad'),
    'depot should be rendered with a prominent purple fill'
);
assert.strictEqual(
    calls.filter(([name]) => name === 'arc').length,
    0,
    'depot should not be rendered as a circle'
);
assert.strictEqual(
    calls.filter(([name]) => name === 'lineTo').length,
    4,
    'depot should be rendered as a five-sided polygon'
);
assert(
    calls.some(([name, x, y]) => (
        name === 'moveTo'
        && Math.abs(x - 10) < 0.001
        && y <= 5
    )),
    'depot pentagon should be larger than the default node footprint'
);
assert(
    calls.some(([name]) => name === 'closePath'),
    'depot polygon path should be closed before fill'
);

const subDepotCalls = [];
const subDepotCtx = {
    save() {},
    restore() {},
    beginPath() { subDepotCalls.push(['beginPath']); },
    moveTo(x, y) { subDepotCalls.push(['moveTo', x, y]); },
    lineTo(x, y) { subDepotCalls.push(['lineTo', x, y]); },
    closePath() { subDepotCalls.push(['closePath']); },
    arc(x, y) { subDepotCalls.push(['arc', x, y]); },
    fill() { subDepotCalls.push(['fill']); },
    stroke() {},
    fillText() {},
    set fillStyle(value) { subDepotCalls.push(['fillStyle', value]); },
    set shadowColor(value) { subDepotCalls.push(['shadowColor', value]); },
    set shadowBlur(value) {},
    set font(value) {},
    set textAlign(value) {},
    set textBaseline(value) {},
};

const subDepotRenderer = Object.create(sandbox.MapRenderer.prototype);
subDepotRenderer.ctx = subDepotCtx;
subDepotRenderer.nodes = [{ id: 1, x: 20, y: 30, type: 'sub_depot' }];
subDepotRenderer.scale = 1;
subDepotRenderer.offsetX = 0;
subDepotRenderer.offsetY = 0;
subDepotRenderer.worldToScreen = (x, y) => ({ x, y });

subDepotRenderer.drawNodes();

assert(
    subDepotCalls.some(([name, value]) => name === 'fillStyle' && value === '#9b59b6'),
    'sub-depot should be rendered as a distinct warehouse marker'
);
