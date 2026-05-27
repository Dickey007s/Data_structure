/**
 * TaskRenderer - Renders task markers (pickup/delivery points)
 */
class TaskRenderer {
    constructor(ctx, mapRenderer) {
        this.ctx = ctx;
        this.mapRenderer = mapRenderer;
        this.tasks = [];
    }

    updateTasks(taskData) {
        this.tasks = taskData;
    }

    render() {
        for (const task of this.tasks) {
            if (task.status === 'completed') continue;
            this.drawTaskMarker(task);
        }
    }

    drawTaskMarker(task) {
        const pickupPos = this.mapRenderer.worldToScreen(
            ...this.mapRenderer.getNodePosition(task.pickup)
        );
        const deliveryPos = this.mapRenderer.worldToScreen(
            ...this.mapRenderer.getNodePosition(task.delivery)
        );
        const scale = Math.min(this.mapRenderer.scale, 2);

        this.ctx.save();

        // Pickup - orange triangle
        if (task.status === 'pending' || task.status === 'assigned') {
            this.ctx.fillStyle = '#f39c12';
            this.ctx.shadowBlur = 4;
            this.ctx.shadowColor = 'rgba(243, 156, 18, 0.4)';
            this.drawTriangle(pickupPos.x, pickupPos.y, Math.max(5, 7 * scale));
        }

        // Delivery - red square
        if (task.status !== 'completed') {
            const sz = Math.max(4, 6 * scale);
            this.ctx.fillStyle = '#e74c3c';
            this.ctx.shadowBlur = 4;
            this.ctx.shadowColor = 'rgba(231, 76, 60, 0.4)';
            this.ctx.fillRect(deliveryPos.x - sz, deliveryPos.y - sz, sz * 2, sz * 2);
        }

        // Connection line for assigned tasks
        if (task.status !== 'pending' && task.status !== 'completed') {
            this.ctx.strokeStyle = 'rgba(243, 156, 18, 0.25)';
            this.ctx.lineWidth = Math.max(1, scale);
            this.ctx.setLineDash([3, 3]);
            this.ctx.beginPath();
            this.ctx.moveTo(pickupPos.x, pickupPos.y);
            this.ctx.lineTo(deliveryPos.x, deliveryPos.y);
            this.ctx.stroke();
        }

        this.ctx.restore();
    }

    drawTriangle(x, y, size) {
        this.ctx.beginPath();
        this.ctx.moveTo(x, y - size);
        this.ctx.lineTo(x - size, y + size);
        this.ctx.lineTo(x + size, y + size);
        this.ctx.closePath();
        this.ctx.fill();
    }
}
