"""OR-Tools global static VRP solver with pickup and delivery constraints."""

from typing import List, Optional

from backend.models.task import Task
from backend.models.vehicle import Vehicle, VehicleStatus
from backend.scheduler.base_scheduler import BaseScheduler


class GlobalORScheduler(BaseScheduler):
    """Static global optimizer using OR-Tools RoutingModel.

    Solves a Pickup-and-Delivery VRP with capacity constraints.
    Each vehicle starts from its actual start_node.
    Time windows and battery are handled by the simulation engine at runtime.
    """

    def __init__(self, time_limit_seconds: int = 10):
        self.time_limit_seconds = time_limit_seconds

    def preassign_all_tasks(
        self,
        tasks: List[Task],
        fleet: List[Vehicle],
        map_obj,
    ) -> None:
        """Solve global VRP and pre-assign tasks to fleet."""
        if not tasks:
            return

        try:
            from ortools.constraint_solver import routing_enums_pb2
            from ortools.constraint_solver import pywrapcp
        except ImportError:
            print("[GlobalORScheduler] OR-Tools not installed, falling back to nearest-first")
            self._fallback_assign(tasks, fleet, map_obj)
            return

        # Step 1: Greedy assignment of tasks to vehicles (capacity-aware)
        vehicle_tasks = self._assign_tasks_greedy(tasks, fleet, map_obj)

        # Step 2: For each vehicle, solve TSP/PDP to determine optimal visit order
        for vehicle_id, vtasks in enumerate(vehicle_tasks):
            if not vtasks:
                continue
            vehicle = fleet[vehicle_id]
            action_plan = self._solve_vehicle_route(
                vehicle, vtasks, map_obj,
                routing_enums_pb2, pywrapcp,
            )
            vehicle.action_plan = action_plan

            # Build path and mark assignments
            if action_plan:
                vehicle.current_path_nodes = [vehicle.current_node]
                current = vehicle.current_node

                for action in action_plan:
                    if action["type"] == "pickup":
                        target = action["task"].pickup_node
                    elif action["type"] == "deliver":
                        target = action["task"].delivery_node
                    else:
                        continue

                    if target != current:
                        path = map_obj.get_path(current, target)
                        if path and len(path) > 1:
                            vehicle.current_path_nodes.extend(path[1:])
                        else:
                            vehicle.current_path_nodes.append(target)
                        current = target

                for action in action_plan:
                    if action["type"] == "pickup":
                        task = action["task"]
                        vehicle.add_task(task)
                        task.status = Task.STATUS_ASSIGNED
                        task.assigned_vehicle = vehicle.id

                vehicle.current_path_index = 0
                if len(vehicle.current_path_nodes) > 1:
                    vehicle.status = VehicleStatus.MOVING

    def _assign_tasks_greedy(
        self,
        tasks: List[Task],
        fleet: List[Vehicle],
        map_obj,
    ) -> List[List[Task]]:
        """Assign tasks to vehicles using greedy capacity-aware heuristic."""
        vehicle_tasks = [[] for _ in fleet]
        vehicle_loads = [0.0 for _ in fleet]

        # Sort tasks by weight descending (heavier first for better packing)
        sorted_tasks = sorted(tasks, key=lambda t: t.weight, reverse=True)

        for task in sorted_tasks:
            best_vehicle = -1
            best_cost = float("inf")
            for v_id, vehicle in enumerate(fleet):
                if vehicle_loads[v_id] + task.weight > vehicle.max_capacity:
                    continue
                cost = (
                    map_obj.get_distance(vehicle.start_node, task.pickup_node)
                    + map_obj.get_distance(task.pickup_node, task.delivery_node)
                )
                if cost < best_cost:
                    best_cost = cost
                    best_vehicle = v_id

            if best_vehicle >= 0:
                vehicle_tasks[best_vehicle].append(task)
                vehicle_loads[best_vehicle] += task.weight
            else:
                # No vehicle can fit this task - assign to least loaded
                min_load = min(vehicle_loads)
                best_vehicle = vehicle_loads.index(min_load)
                vehicle_tasks[best_vehicle].append(task)
                vehicle_loads[best_vehicle] += task.weight

        return vehicle_tasks

    def _solve_vehicle_route(
        self,
        vehicle: Vehicle,
        tasks: List[Task],
        map_obj,
        routing_enums_pb2,
        pywrapcp,
    ) -> List[dict]:
        """Solve optimal visit order for a single vehicle's tasks."""
        num_tasks = len(tasks)

        # Node layout for single vehicle:
        #   0          : depot (vehicle start_node)
        #   1..N       : pickup nodes
        #   N+1..2N    : delivery nodes
        depot_index = 0
        pickup_offset = 1
        delivery_offset = 1 + num_tasks
        total_nodes = 1 + 2 * num_tasks

        def _node_to_map_node(node: int) -> int:
            if node == depot_index:
                return vehicle.start_node
            elif pickup_offset <= node < delivery_offset:
                return tasks[node - pickup_offset].pickup_node
            elif delivery_offset <= node < total_nodes:
                return tasks[node - delivery_offset].delivery_node
            return vehicle.start_node

        # Build distance matrix
        distance_matrix = [[0] * total_nodes for _ in range(total_nodes)]
        for i in range(total_nodes):
            for j in range(total_nodes):
                if i == j:
                    continue
                u = _node_to_map_node(i)
                v = _node_to_map_node(j)
                dist = map_obj.get_distance(u, v)
                distance_matrix[i][j] = int(dist * 100)

        manager = pywrapcp.RoutingIndexManager(total_nodes, 1, depot_index)
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return distance_matrix[from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Pickup and delivery constraints
        for task_idx in range(num_tasks):
            pickup_index = manager.NodeToIndex(pickup_offset + task_idx)
            delivery_index = manager.NodeToIndex(delivery_offset + task_idx)
            routing.AddPickupAndDelivery(pickup_index, delivery_index)
            routing.solver().Add(
                routing.VehicleVar(pickup_index) == routing.VehicleVar(delivery_index)
            )

        # Capacity constraint
        def demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            if pickup_offset <= from_node < delivery_offset:
                task_idx = from_node - pickup_offset
                return int(tasks[task_idx].weight * 100)
            elif delivery_offset <= from_node < total_nodes:
                task_idx = from_node - delivery_offset
                return -int(tasks[task_idx].weight * 100)
            return 0

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,
            [int(vehicle.max_capacity * 100)],
            True,
            "Capacity",
        )

        # Search parameters
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.FromSeconds(self.time_limit_seconds)
        search_parameters.log_search = False

        solution = routing.SolveWithParameters(search_parameters)

        if not solution:
            # Fallback: simple nearest-neighbor ordering
            return self._nearest_neighbor_route(vehicle, tasks, map_obj)

        # Extract route
        index = routing.Start(0)
        node_sequence = []
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            node_sequence.append(node)
            index = solution.Value(routing.NextVar(index))

        action_plan = []
        for node in node_sequence:
            if node == depot_index:
                continue
            if pickup_offset <= node < delivery_offset:
                task_idx = node - pickup_offset
                action_plan.append({"type": "pickup", "task": tasks[task_idx]})
            elif delivery_offset <= node < total_nodes:
                task_idx = node - delivery_offset
                action_plan.append({"type": "deliver", "task": tasks[task_idx]})

        return action_plan

    def _nearest_neighbor_route(
        self,
        vehicle: Vehicle,
        tasks: List[Task],
        map_obj,
    ) -> List[dict]:
        """Fallback: construct route using nearest-neighbor heuristic."""
        if not tasks:
            return []

        # Build a simple route: for each task, visit pickup then delivery
        # Order tasks by distance from current position
        current = vehicle.current_node
        remaining = list(tasks)
        ordered_tasks = []

        while remaining:
            best_task = None
            best_cost = float("inf")
            for task in remaining:
                cost = (
                    map_obj.get_distance(current, task.pickup_node)
                    + map_obj.get_distance(task.pickup_node, task.delivery_node)
                )
                if cost < best_cost:
                    best_cost = cost
                    best_task = task

            ordered_tasks.append(best_task)
            remaining.remove(best_task)
            current = best_task.delivery_node

        action_plan = []
        for task in ordered_tasks:
            action_plan.append({"type": "pickup", "task": task})
            action_plan.append({"type": "deliver", "task": task})

        return action_plan

    def _fallback_assign(
        self,
        tasks: List[Task],
        fleet: List[Vehicle],
        map_obj,
    ) -> None:
        """Fallback: assign tasks round-robin to nearest vehicle."""
        from backend.scheduler.nearest_first_scheduler import NearestFirstScheduler
        fallback = NearestFirstScheduler()
        for task in tasks:
            fallback.assign_task(task, fleet, map_obj)

    def assign_task(self, task, fleet, map_obj) -> Optional[Vehicle]:
        """Global scheduler does not use real-time assignment."""
        return None

    def replan(self, fleet, active_tasks, map_obj) -> None:
        """Global scheduler does not replan dynamically."""
        pass
