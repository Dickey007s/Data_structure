/**
 * MapRenderer - Renders road network, nodes and grid background
 */
class MapRenderer {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.nodes = [];
        this.edges = [];
        this.scale = 1;
        this.offsetX = 0;
        this.offsetY = 0;
        this.padding = 40;
        this.setupCanvas();
    }

    setupCanvas() {
        const resize = () => {
            const rect = this.canvas.parentElement.getBoundingClientRect();
            this.canvas.width = rect.width;
            this.canvas.height = rect.height;
            if (this.nodes.length > 0) {
                this.fitToView();
            }
        };
        window.addEventListener('resize', resize);
        resize();
    }

    setMapData(nodes, edges) {
        this.nodes = nodes;
        this.edges = edges;
        this.fitToView();
    }

    fitToView() {
        if (this.nodes.length === 0) return;

        const xs = this.nodes.map(n => n.x);
        const ys = this.nodes.map(n => n.y);
        const minX = Math.min(...xs);
        const maxX = Math.max(...xs);
        const minY = Math.min(...ys);
        const maxY = Math.max(...ys);

        const mapWidth = maxX - minX || 1;
        const mapHeight = maxY - minY || 1;

        const scaleX = (this.canvas.width - this.padding * 2) / mapWidth;
        const scaleY = (this.canvas.height - this.padding * 2) / mapHeight;
        this.scale = Math.min(scaleX, scaleY);

        this.offsetX = this.padding - minX * this.scale;
        this.offsetY = this.padding - minY * this.scale;
    }

    render() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.drawGrid();
        this.drawRoads();
        this.drawNodes();
    }

    drawGrid() {
        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
        this.ctx.lineWidth = 1;
        const gridSize = 30;

        for (let x = 0; x < this.canvas.width; x += gridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.canvas.height);
            this.ctx.stroke();
        }
        for (let y = 0; y < this.canvas.height; y += gridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.canvas.width, y);
            this.ctx.stroke();
        }
    }

    drawRoads() {
        this.ctx.strokeStyle = 'rgba(100, 150, 200, 0.3)';
        this.ctx.lineWidth = 2;

        for (const edge of this.edges) {
            const u = this.nodes.find(n => n.id === edge.u);
            const v = this.nodes.find(n => n.id === edge.v);
            if (u && v) {
                const posU = this.worldToScreen(u.x, u.y);
                const posV = this.worldToScreen(v.x, v.y);

                this.ctx.beginPath();
                this.ctx.moveTo(posU.x, posU.y);
                this.ctx.lineTo(posV.x, posV.y);
                this.ctx.stroke();
            }
        }
    }

    drawNodes() {
        for (const node of this.nodes) {
            const pos = this.worldToScreen(node.x, node.y);
            const radius = node.type === 'depot' ? 10 : 6;

            this.ctx.save();

            switch (node.type) {
                case 'depot':
                    this.ctx.fillStyle = '#ffd700';
                    this.ctx.shadowColor = '#ffd700';
                    this.ctx.shadowBlur = 15;
                    break;
                case 'station':
                    this.ctx.fillStyle = '#00ff88';
                    this.ctx.shadowColor = '#00ff88';
                    this.ctx.shadowBlur = 10;
                    break;
                default:
                    this.ctx.fillStyle = '#4a5568';
                    this.ctx.shadowBlur = 0;
            }

            this.ctx.beginPath();
            this.ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
            this.ctx.fill();

            this.ctx.restore();
        }
    }

    worldToScreen(x, y) {
        return {
            x: x * this.scale + this.offsetX,
            y: y * this.scale + this.offsetY
        };
    }

    screenToWorld(screenX, screenY) {
        return {
            x: (screenX - this.offsetX) / this.scale,
            y: (screenY - this.offsetY) / this.scale
        };
    }

    getNodePosition(nodeId) {
        const node = this.nodes.find(n => n.id === nodeId);
        return node ? [node.x, node.y] : [0, 0];
    }
}
