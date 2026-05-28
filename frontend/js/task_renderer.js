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
        const taskType = task.task_type || 'paired';

        this.ctx.save();

        // 单点送货：大仓库 → 送货点，只显示粉色送货方块
        if (taskType === 'depot_delivery') {
            if (task.status !== 'completed' && task.status !== 'timeout') {
                this.drawPinkSquare(deliveryPos.x, deliveryPos.y, scale);
            }
            this.ctx.restore();
            return;
        }

        // 仓库取货：子仓库 → 大仓库，不显示额外标记（子仓库本身有菱形标记）
        if (taskType === 'sub_depot_return') {
            this.ctx.restore();
            return;
        }

        // 分拣派送（paired）：保持原有逻辑
        if (task.status === 'pending' || task.status === 'assigned') {
            this.drawPickupTriangle(pickupPos.x, pickupPos.y, scale);
        }

        if (task.status === 'delivering') {
            this.drawDeliverySquare(deliveryPos.x, deliveryPos.y, scale);
        }

        this.ctx.restore();
    }

    drawPickupTriangle(x, y, scale) {
        this.ctx.fillStyle = '#f39c12';
        this.ctx.shadowBlur = 4;
        this.ctx.shadowColor = 'rgba(243, 156, 18, 0.4)';
        this.drawTriangle(x, y, Math.max(5, 7 * scale));
    }

    drawDeliverySquare(x, y, scale) {
        const sz = Math.max(4, 6 * scale);
        this.ctx.fillStyle = '#e74c3c';
        this.ctx.shadowBlur = 4;
        this.ctx.shadowColor = 'rgba(231, 76, 60, 0.4)';
        this.ctx.fillRect(x - sz, y - sz, sz * 2, sz * 2);
    }

    drawPinkSquare(x, y, scale) {
        const sz = Math.max(4, 6 * scale);
        this.ctx.fillStyle = '#ff69b4';
        this.ctx.shadowBlur = 4;
        this.ctx.shadowColor = 'rgba(255, 105, 180, 0.4)';
        this.ctx.fillRect(x - sz, y - sz, sz * 2, sz * 2);
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
