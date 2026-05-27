/**
 * StationRenderer - Renders charging stations with occupancy info
 */
class StationRenderer {
    constructor(ctx, mapRenderer) {
        this.ctx = ctx;
        this.mapRenderer = mapRenderer;
        this.stations = [];
    }

    updateStations(stationData) {
        this.stations = stationData;
    }

    render() {
        for (const station of this.stations) {
            this.drawStation(station);
        }
    }

    drawStation(station) {
        const nodePos = this.mapRenderer.worldToScreen(
            ...this.mapRenderer.getNodePosition(station.node)
        );
        const scale = Math.min(this.mapRenderer.scale, 2);
        const radius = Math.max(10, 16 * scale);

        this.ctx.save();

        // Outer ring - capacity indicator
        const capacityPct = station.occupied / station.total;
        this.ctx.strokeStyle = capacityPct > 0.8 ? '#e74c3c' : '#27ae60';
        this.ctx.lineWidth = Math.max(2, 3 * scale);
        this.ctx.beginPath();
        this.ctx.arc(nodePos.x, nodePos.y, radius, 0, Math.PI * 2);
        this.ctx.stroke();

        // Fill occupancy
        this.ctx.fillStyle = `rgba(39, 174, 96, ${capacityPct * 0.25})`;
        this.ctx.beginPath();
        this.ctx.arc(nodePos.x, nodePos.y, radius, 0, Math.PI * 2);
        this.ctx.fill();

        // Queue count
        if (station.queue > 0) {
            this.ctx.fillStyle = '#f39c12';
            this.ctx.font = `bold ${Math.max(10, 12 * scale)}px sans-serif`;
            this.ctx.textAlign = 'center';
            this.ctx.fillText(
                `+${station.queue}`,
                nodePos.x,
                nodePos.y - radius - 4
            );
        }

        // Slot count
        this.ctx.fillStyle = '#2c3e50';
        this.ctx.font = `${Math.max(8, 10 * scale)}px sans-serif`;
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        this.ctx.fillText(
            `${station.occupied}/${station.total}`,
            nodePos.x,
            nodePos.y + 1
        );

        this.ctx.restore();
    }
}
