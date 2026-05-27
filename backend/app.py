"""Flask + SocketIO web service for EV Fleet Simulation."""

import os
import sys
import threading
from typing import Optional

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS

from backend.simulator.simulator import Simulator

app = Flask(__name__, static_folder="../frontend")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Global simulator instance and thread
simulator: Optional[Simulator] = None
sim_thread: Optional[threading.Thread] = None


@app.route("/")
def index():
    """Serve frontend main page."""
    return send_from_directory("../frontend", "index.html")


@app.route("/<path:path>")
def serve_static(path):
    """Serve frontend static resources."""
    return send_from_directory("../frontend", path)


@app.route("/api/map", methods=["GET"])
def get_map():
    """Get map configuration data."""
    if simulator and simulator.map:
        return jsonify(simulator.map.to_dict())
    return jsonify({"error": "Simulator not initialized"}), 400


@app.route("/api/config", methods=["POST"])
def initialize_simulation():
    """Initialize simulation environment."""
    global simulator

    config = request.json
    simulator = Simulator(config)
    simulator.initialize(
        map_config=config["map"],
        fleet_config=config["fleet"],
        station_config=config["stations"],
        scheduler_type=config.get("scheduler", "insertion"),
    )

    simulator._emit_state = lambda state: socketio.emit("state_update", state)
    simulator._emit_finished = lambda data: socketio.emit("simulation_finished", data)

    return jsonify({
        "status": "initialized",
        "task_count": len(simulator.event_generator.schedule),
        "map_nodes": len(simulator.map.nodes),
        "fleet_size": len(simulator.fleet),
    })


@app.route("/api/start", methods=["POST"])
def start_simulation():
    """Start simulation in background thread."""
    global sim_thread

    if not simulator:
        return jsonify({"error": "Simulator not initialized"}), 400

    if simulator.running:
        return jsonify({"error": "Simulation already running"}), 400

    def run_sim():
        simulator.run()

    sim_thread = threading.Thread(target=run_sim, daemon=True)
    sim_thread.start()

    return jsonify({"status": "started", "time": simulator.current_time})


@app.route("/api/pause", methods=["POST"])
def pause_simulation():
    """Pause simulation."""
    if simulator:
        simulator.pause()
    return jsonify({"status": "paused"})


@app.route("/api/reset", methods=["POST"])
def reset_simulation():
    """Reset simulation."""
    global simulator, sim_thread

    if simulator:
        simulator.reset()

    if sim_thread and sim_thread.is_alive():
        sim_thread.join(timeout=2.0)

    simulator = None
    sim_thread = None

    return jsonify({"status": "reset"})


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get current statistics."""
    if not simulator:
        return jsonify({"error": "Simulator not initialized"}), 400

    return jsonify({
        "time": simulator.current_time,
        "score": simulator._calculate_score(),
        "completed": len(simulator.completed_tasks),
        "failed": len(simulator.failed_tasks),
        "active": len(simulator.active_tasks),
    })


@socketio.on("connect")
def handle_connect():
    """Client connected."""
    print(f"Client connected: {request.sid}")
    emit("connected", {
        "message": "Connected to EV Fleet Simulation Server",
        "version": "1.1",
    })


@socketio.on("disconnect")
def handle_disconnect():
    """Client disconnected."""
    print(f"Client disconnected: {request.sid}")


@socketio.on("request_state")
def handle_request_state():
    """Client requests current state."""
    if simulator:
        state = simulator._get_state_snapshot(simulator._calculate_score())
        emit("state_update", state)


if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
