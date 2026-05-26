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

        this.ctx.save();

        // Outer ring - capacity indicator
        const capacityPct = station.occupied / station.total;
        this.ctx.strokeStyle = capacityPct > 0.8 ? '#e94560' : '#00ff88';
        this.ctx.lineWidth = 4;
        this.ctx.beginPath();
        this.ctx.arc(nodePos.x, nodePos.y, 20, 0, Math.PI * 2);
        this.ctx.stroke();

        // Fill occupancy
        this.ctx.fillStyle = `rgba(0, 255, 136, ${capacityPct * 0.3})`;
        this.ctx.beginPath();
        this.ctx.arc(nodePos.x, nodePos.y, 20, 0, Math.PI * 2);
        this.ctx.fill();

        // Queue count
        if (station.queue > 0) {
            this.ctx.fillStyle = '#f9a826';
            this.ctx.font = 'bold 12px sans-serif';
            this.ctx.textAlign = 'center';
            this.ctx.fillText(
                `+${station.queue}`,
                nodePos.x,
                nodePos.y - 25
            );
        }

        // Slot count
        this.ctx.fillStyle = '#fff';
        this.ctx.font = '10px sans-serif';
        this.ctx.textAlign = 'center';
        this.ctx.fillText(
            `${station.occupied}/${station.total}`,
            nodePos.x,
            nodePos.y + 4
        );

        this.ctx.restore();
    }
}
