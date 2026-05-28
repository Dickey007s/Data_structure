/**
 * MapRenderer - Renders road network, nodes and grid background
 * Supports zoom with mouse wheel and pan with drag
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
        this.minScale = 0.3;
        this.maxScale = 5;

        // Pan state
        this.isDragging = false;
        this.dragStartX = 0;
        this.dragStartY = 0;
        this.dragOffsetX = 0;
        this.dragOffsetY = 0;

        this.setupCanvas();
        this.setupInteractions();
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

    setupInteractions() {
        // Mouse wheel zoom
        this.canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
            this.zoomAt(e.offsetX, e.offsetY, zoomFactor);
        }, { passive: false });

        // Mouse drag pan
        this.canvas.addEventListener('mousedown', (e) => {
            this.isDragging = true;
            this.dragStartX = e.clientX;
            this.dragStartY = e.clientY;
            this.dragOffsetX = this.offsetX;
            this.dragOffsetY = this.offsetY;
            this.canvas.style.cursor = 'grabbing';
        });

        window.addEventListener('mousemove', (e) => {
            if (!this.isDragging) return;
            const dx = e.clientX - this.dragStartX;
            const dy = e.clientY - this.dragStartY;
            this.offsetX = this.dragOffsetX + dx;
            this.offsetY = this.dragOffsetY + dy;
        });

        window.addEventListener('mouseup', () => {
            this.isDragging = false;
            this.canvas.style.cursor = 'grab';
        });
    }

    zoomAt(screenX, screenY, factor) {
        const newScale = Math.max(this.minScale, Math.min(this.maxScale, this.scale * factor));
        if (newScale === this.scale) return;

        // Zoom towards mouse position
        const worldX = (screenX - this.offsetX) / this.scale;
        const worldY = (screenY - this.offsetY) / this.scale;

        this.scale = newScale;
        this.offsetX = screenX - worldX * this.scale;
        this.offsetY = screenY - worldY * this.scale;
    }

    zoomIn() {
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;
        this.zoomAt(centerX, centerY, 1.3);
    }

    zoomOut() {
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;
        this.zoomAt(centerX, centerY, 0.77);
    }

    resetView() {
        this.fitToView();
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
        this.ctx.strokeStyle = 'rgba(180, 190, 200, 0.25)';
        this.ctx.lineWidth = 1;
        const gridSize = 30 * this.scale;

        const startX = this.offsetX % gridSize;
        const startY = this.offsetY % gridSize;

        for (let x = startX; x < this.canvas.width; x += gridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.canvas.height);
            this.ctx.stroke();
        }
        for (let y = startY; y < this.canvas.height; y += gridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.canvas.width, y);
            this.ctx.stroke();
        }
    }

    drawRoads() {
        this.ctx.strokeStyle = 'rgba(100, 120, 140, 0.35)';
        this.ctx.lineWidth = Math.max(1, 1.5 * this.scale);

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
            const baseRadius = node.type === 'depot' ? 10 : 5;
            const radius = Math.max(2, baseRadius * Math.min(this.scale, 2));

            this.ctx.save();

            switch (node.type) {
                case 'depot':
                    this.ctx.fillStyle = '#8e44ad';
                    this.ctx.shadowColor = 'rgba(142, 68, 173, 0.55)';
                    this.ctx.shadowBlur = 12;
                    break;
                case 'station':
                    this.ctx.fillStyle = '#27ae60';
                    this.ctx.shadowColor = 'rgba(39, 174, 96, 0.4)';
                    this.ctx.shadowBlur = 8;
                    break;
                default:
                    this.ctx.fillStyle = '#5d6d7e';
                    this.ctx.shadowBlur = 0;
            }

            if (node.type === 'depot') {
                this.drawPentagon(pos.x, pos.y, radius * 1.55);
            } else {
                this.ctx.beginPath();
                this.ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
                this.ctx.fill();
            }

            // Depot label
            if (node.type === 'depot' && this.scale > 0.6) {
                this.ctx.fillStyle = '#2c3e50';
                this.ctx.font = `bold ${Math.max(9, 11 * this.scale)}px sans-serif`;
                this.ctx.textAlign = 'center';
                this.ctx.textBaseline = 'bottom';
                this.ctx.shadowBlur = 0;
                this.ctx.fillText('仓库', pos.x, pos.y - radius - 3);
            }

            this.ctx.restore();
        }
    }

    drawPentagon(x, y, radius) {
        this.ctx.beginPath();
        for (let i = 0; i < 5; i++) {
            const angle = -Math.PI / 2 + i * (Math.PI * 2 / 5);
            const px = x + Math.cos(angle) * radius;
            const py = y + Math.sin(angle) * radius;
            if (i === 0) {
                this.ctx.moveTo(px, py);
            } else {
                this.ctx.lineTo(px, py);
            }
        }
        this.ctx.closePath();
        this.ctx.fill();
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
