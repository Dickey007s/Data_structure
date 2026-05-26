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

        this.ctx.save();

        // Pickup - orange triangle
        if (task.status === 'pending' || task.status === 'assigned') {
            this.ctx.fillStyle = '#f9a826';
            this.ctx.shadowBlur = 8;
            this.ctx.shadowColor = '#f9a826';
            this.drawTriangle(pickupPos.x, pickupPos.y, 8);
        }

        // Delivery - red square
        if (task.status !== 'completed') {
            this.ctx.fillStyle = '#e94560';
            this.ctx.shadowBlur = 8;
            this.ctx.shadowColor = '#e94560';
            this.ctx.fillRect(deliveryPos.x - 6, deliveryPos.y - 6, 12, 12);
        }

        // Connection line for assigned tasks
        if (task.status !== 'pending' && task.status !== 'completed') {
            this.ctx.strokeStyle = 'rgba(249, 168, 38, 0.2)';
            this.ctx.lineWidth = 1;
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
