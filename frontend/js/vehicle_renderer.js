/**
 * VehicleRenderer - Renders vehicles, paths and battery indicators
 */
class VehicleRenderer {
    constructor(ctx, mapRenderer) {
        this.ctx = ctx;
        this.mapRenderer = mapRenderer;
        this.vehicles = [];
        this.displayPositions = new Map();
    }

    updateVehicles(vehicleData) {
        this.vehicles = vehicleData;
        const activeIds = new Set(vehicleData.map(v => v.id));

        for (const vehicle of vehicleData) {
            if (!this.displayPositions.has(vehicle.id)) {
                this.displayPositions.set(vehicle.id, [...vehicle.position]);
            }
        }

        for (const id of this.displayPositions.keys()) {
            if (!activeIds.has(id)) {
                this.displayPositions.delete(id);
            }
        }
    }

    render() {
        this.updateDisplayPositions();

        for (const vehicle of this.vehicles) {
            this.drawPath(vehicle);
        }
        for (const vehicle of this.vehicles) {
            this.drawVehicle(vehicle);
        }
    }

    updateDisplayPositions() {
        for (const vehicle of this.vehicles) {
            const target = vehicle.position;
            const current = this.displayPositions.get(vehicle.id) || target;

            if (vehicle.status !== 'moving') {
                this.displayPositions.set(vehicle.id, [...target]);
                continue;
            }

            const dx = target[0] - current[0];
            const dy = target[1] - current[1];
            const distance = Math.hypot(dx, dy);

            if (distance < 0.5) {
                this.displayPositions.set(vehicle.id, [...target]);
            } else {
                this.displayPositions.set(vehicle.id, [
                    current[0] + dx * 0.35,
                    current[1] + dy * 0.35
                ]);
            }
        }
    }

    getDisplayPosition(vehicle) {
        return this.displayPositions.get(vehicle.id) || vehicle.position;
    }

    drawVehicle(vehicle) {
        const displayPosition = this.getDisplayPosition(vehicle);
        const pos = this.mapRenderer.worldToScreen(
            displayPosition[0],
            displayPosition[1]
        );
        const scale = Math.min(this.mapRenderer.scale, 2);
        const radius = Math.max(6, 10 * scale);

        this.ctx.save();

        // Battery indicator ring
        const batteryPct = vehicle.battery_pct;
        const batteryColor = batteryPct > 0.3 ? '#27ae60' :
                            batteryPct > 0.1 ? '#f39c12' : '#e74c3c';

        this.ctx.strokeStyle = batteryColor;
        this.ctx.lineWidth = Math.max(2, 2.5 * scale);
        this.ctx.beginPath();
        this.ctx.arc(pos.x, pos.y, radius + 3, -Math.PI / 2,
                     -Math.PI / 2 + Math.PI * 2 * batteryPct);
        this.ctx.stroke();

        // Vehicle body
        this.ctx.fillStyle = '#3498db';
        this.ctx.shadowBlur = 6;
        this.ctx.shadowColor = 'rgba(52, 152, 219, 0.4)';
        this.ctx.beginPath();
        this.ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
        this.ctx.fill();

        // Load indicator
        if (vehicle.load_pct > 0) {
            this.ctx.fillStyle = `rgba(231, 76, 60, ${vehicle.load_pct * 0.5})`;
            this.ctx.beginPath();
            this.ctx.arc(pos.x, pos.y, radius * 0.6, 0, Math.PI * 2);
            this.ctx.fill();
        }

        // Vehicle ID
        this.ctx.fillStyle = '#ffffff';
        this.ctx.font = `bold ${Math.max(8, 9 * scale)}px sans-serif`;
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        this.ctx.shadowBlur = 0;
        this.ctx.fillText(vehicle.id, pos.x, pos.y);

        this.ctx.restore();
    }

    drawPath(vehicle) {
        if (vehicle.status === 'charging' || vehicle.status === 'waiting_charge') {
            return;
        }

        this.ctx.save();
        this.ctx.lineWidth = Math.max(2, 2.5 * this.mapRenderer.scale);
        this.ctx.setLineDash([5, 5]);

        if (vehicle.path && vehicle.path.length >= 2) {
            // Remaining current path (vehicle is moving)
            this.ctx.strokeStyle = 'rgba(52, 152, 219, 0.45)';
            this.ctx.beginPath();
            const displayPosition = this.getDisplayPosition(vehicle);
            const start = this.mapRenderer.worldToScreen(
                displayPosition[0], displayPosition[1]
            );
            this.ctx.moveTo(start.x, start.y);

            const nextPathIndex = Math.max(1, (vehicle.path_index ?? 0) + 1);
            const targetIndex = this.getRouteTargetIndex(vehicle, nextPathIndex);
            for (let i = nextPathIndex; i <= targetIndex; i++) {
                const pos = this.mapRenderer.worldToScreen(
                    ...this.mapRenderer.getNodePosition(vehicle.path[i])
                );
                this.ctx.lineTo(pos.x, pos.y);
            }
            this.ctx.stroke();
        } else if (vehicle.next_target != null && vehicle.next_target !== vehicle.node) {
            // Preview line to next target when idle but has pending action
            this.ctx.strokeStyle = 'rgba(30, 120, 200, 0.75)';
            this.ctx.beginPath();
            const displayPosition = this.getDisplayPosition(vehicle);
            const start = this.mapRenderer.worldToScreen(
                displayPosition[0], displayPosition[1]
            );
            const end = this.mapRenderer.worldToScreen(
                ...this.mapRenderer.getNodePosition(vehicle.next_target)
            );
            this.ctx.moveTo(start.x, start.y);
            this.ctx.lineTo(end.x, end.y);
            this.ctx.stroke();
        }

        this.ctx.restore();
    }

    getRouteTargetIndex(vehicle, startIndex) {
        if (vehicle.route_target == null) {
            return vehicle.path.length - 1;
        }

        const targetIndex = vehicle.path.indexOf(vehicle.route_target, startIndex);
        return targetIndex === -1 ? vehicle.path.length - 1 : targetIndex;
    }
}
