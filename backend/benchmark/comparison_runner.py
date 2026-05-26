"""Run comparison experiments across all scheduling strategies."""

from typing import Dict, Callable, Optional

from backend.simulator.simulator import Simulator
from backend.benchmark.metrics_collector import collect_metrics


class ComparisonRunner:
    """Serially run all strategies with identical configuration and collect metrics."""

    STRATEGIES = ["nearest", "max_weight", "insertion", "global_or"]
    STRATEGY_NAMES = {
        "nearest": "最近优先",
        "max_weight": "最大重量优先",
        "insertion": "插入启发式",
        "global_or": "OR-Tools 全局最优",
    }

    def run(
        self,
        config: dict,
        emit_progress: Optional[Callable] = None,
        emit_result: Optional[Callable] = None,
    ) -> Dict:
        """Run all strategies and return comparison results.

        Args:
            config: Simulation configuration dict.
            emit_progress: Callback(strategy_name, status) for progress updates.
            emit_result: Callback(results_dict) when all done.

        Returns:
            Dict mapping strategy key to metrics dict.
        """
        results = {}

        for strategy in self.STRATEGIES:
            if emit_progress:
                emit_progress({"strategy": strategy, "status": "running"})

            sim = Simulator(config)
            sim.initialize(
                map_config=config["map"],
                fleet_config=config["fleet"],
                station_config=config["stations"],
                scheduler_type=strategy,
            )

            # Fast synchronous run (no real-time sleep)
            while not sim._check_finished():
                sim.tick()

            metrics = collect_metrics(sim)
            metrics["strategy_name"] = self.STRATEGY_NAMES.get(strategy, strategy)
            results[strategy] = metrics

            if emit_progress:
                emit_progress({"strategy": strategy, "status": "done"})

        if emit_result:
            emit_result(results)

        return results
