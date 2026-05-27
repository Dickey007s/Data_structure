/**
 * VehicleRenderer - Renders vehicles, paths and battery indicators
 */
class VehicleRenderer {
    constructor(ctx, mapRenderer) {
        this.ctx = ctx;
        this.mapRenderer = mapRenderer;
        this.vehicles = [];
    }

    updateVehicles(vehicleData) {
        this.vehicles = vehicleData;
    }

    render() {
        for (const vehicle of this.vehicles) {
            this.drawPath(vehicle);
        }
        for (const vehicle of this.vehicles) {
            this.drawVehicle(vehicle);
        }
    }

    drawVehicle(vehicle) {
        const pos = this.mapRenderer.worldToScreen(
            vehicle.position[0],
            vehicle.position[1]
        );
        const scale = Math.min(this.mapRenderer.scale, 2);
        const radius = Math.max(6, 10 * scale);

        this.ctx.save();

        // Battery indicator ring
        const batteryPct = vehicle.battery_pct;
        const batteryColor = batteryPct > 0.3 ? '#3498db' :
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
        if (!vehicle.path || vehicle.path.length < 2) return;

        this.ctx.save();
        this.ctx.strokeStyle = 'rgba(52, 152, 219, 0.18)';
        this.ctx.lineWidth = Math.max(1, 1.5 * this.mapRenderer.scale);
        this.ctx.setLineDash([5, 5]);

        this.ctx.beginPath();
        const start = this.mapRenderer.worldToScreen(
            ...this.mapRenderer.getNodePosition(vehicle.path[0])
        );
        this.ctx.moveTo(start.x, start.y);

        for (let i = 1; i < vehicle.path.length; i++) {
            const pos = this.mapRenderer.worldToScreen(
                ...this.mapRenderer.getNodePosition(vehicle.path[i])
            );
            this.ctx.lineTo(pos.x, pos.y);
        }

        this.ctx.stroke();
        this.ctx.restore();
    }
}
