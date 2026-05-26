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

        this.ctx.save();

        // Battery indicator ring
        const batteryPct = vehicle.battery_pct;
        const batteryColor = batteryPct > 0.3 ? '#00d9ff' :
                            batteryPct > 0.1 ? '#f9a826' : '#e94560';

        this.ctx.strokeStyle = batteryColor;
        this.ctx.lineWidth = 3;
        this.ctx.beginPath();
        this.ctx.arc(pos.x, pos.y, 16, -Math.PI / 2,
                     -Math.PI / 2 + Math.PI * 2 * batteryPct);
        this.ctx.stroke();

        // Vehicle body
        this.ctx.fillStyle = '#00d9ff';
        this.ctx.shadowBlur = 15;
        this.ctx.shadowColor = '#00d9ff';
        this.ctx.beginPath();
        this.ctx.arc(pos.x, pos.y, 12, 0, Math.PI * 2);
        this.ctx.fill();

        // Load indicator
        if (vehicle.load_pct > 0) {
            this.ctx.fillStyle = `rgba(233, 69, 96, ${vehicle.load_pct * 0.6})`;
            this.ctx.beginPath();
            this.ctx.arc(pos.x, pos.y, 8, 0, Math.PI * 2);
            this.ctx.fill();
        }

        // Vehicle ID
        this.ctx.fillStyle = '#1a1a2e';
        this.ctx.font = 'bold 10px sans-serif';
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        this.ctx.shadowBlur = 0;
        this.ctx.fillText(vehicle.id, pos.x, pos.y);

        this.ctx.restore();
    }

    drawPath(vehicle) {
        if (!vehicle.path || vehicle.path.length < 2) return;

        this.ctx.save();
        this.ctx.strokeStyle = 'rgba(0, 217, 255, 0.12)';
        this.ctx.lineWidth = 2;
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
