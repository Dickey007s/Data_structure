"""Flask + SocketIO web service for EV Fleet Simulation."""

import os
import sys
import threading
import copy
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
        seed=config.get("seed", 42),
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


@app.route("/api/compare", methods=["POST"])
def compare_schedulers():
    """Run all three schedulers on the same map/tasks and return comparison."""
    base_config = request.json
    schedulers = ["insertion", "nearest", "max_weight"]
    results = {}

    # Use deterministic seed for reproducible comparison
    seed = base_config.get("seed", 42)

    for scheduler_type in schedulers:
        config = copy.deepcopy(base_config)
        config["scheduler"] = scheduler_type

        sim = Simulator(config)
        sim.initialize(
            map_config=config["map"],
            fleet_config=config["fleet"],
            station_config=config["stations"],
            scheduler_type=scheduler_type,
            seed=seed,
        )

        # Run simulation to completion (no real-time delay)
        sim.sim_speed = 1000.0  # Fast forward
        sim.real_time_step = 0.0

        while not sim._check_finished():
            sim.tick()

        # Calculate comprehensive metrics
        completed = len(sim.completed_tasks)
        failed = len(sim.failed_tasks)
        total = completed + failed
        completion_rate = completed / total if total > 0 else 0.0
        timeout_rate = failed / total if total > 0 else 0.0

        avg_time = 0.0
        if sim.completed_tasks:
            avg_time = sum(
                t.completed_time - t.ready_time
                for t in sim.completed_tasks
                if t.completed_time is not None
            ) / len(sim.completed_tasks)

        total_distance = sum(sim.total_distance_traveled)
        avg_distance_per_task = total_distance / completed if completed > 0 else 0.0

        # Energy consumption: initial battery - current battery for each vehicle
        total_energy_consumed = sum(
            v.max_battery - v.current_battery for v in sim.fleet
        )
        energy_efficiency = (
            total_energy_consumed / total_distance if total_distance > 0 else 0.0
        )

        # Load balance: standard deviation of tasks completed per vehicle
        tasks_per_vehicle = [0] * len(sim.fleet)
        for t in sim.completed_tasks:
            if t.assigned_vehicle is not None and 0 <= t.assigned_vehicle < len(tasks_per_vehicle):
                tasks_per_vehicle[t.assigned_vehicle] += 1
        load_balance_std = (
            __import__("statistics").stdev(tasks_per_vehicle)
            if len(tasks_per_vehicle) > 1
            else 0.0
        )

        # Charging time ratio
        charging_time_ratio = (
            sim.total_charging_time / sim.current_time
            if sim.current_time > 0
            else 0.0
        )

        results[scheduler_type] = {
            "completed": completed,
            "failed": failed,
            "completion_rate": round(completion_rate, 4),
            "timeout_rate": round(timeout_rate, 4),
            "avg_completion_time": round(avg_time, 2),
            "total_distance": round(total_distance, 2),
            "avg_distance_per_task": round(avg_distance_per_task, 2),
            "total_energy_consumed": round(total_energy_consumed, 2),
            "energy_efficiency": round(energy_efficiency, 4),
            "charging_count": sim.charging_count,
            "charging_time_ratio": round(charging_time_ratio, 4),
            "load_balance_std": round(load_balance_std, 2),
            "final_score": round(sim._calculate_score(), 2),
            "sim_time": sim.current_time,
        }

    return jsonify(results)


@socketio.on("connect")
def handle_connect():
    """Client connected."""
    print(f"Client connected: {request.sid}")
    emit("connected", {
        "message": "Connected to EV Fleet Simulation Server",
        "version": "1.2",
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
