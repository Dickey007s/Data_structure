"""TransportMap model - road network graph using NetworkX."""

import math
import random
from typing import Dict, List, Tuple, Optional
import networkx as nx


class TransportMap:
    """Road network represented as a graph with grid layout."""

    def __init__(self, width: int, height: int, grid_type: str = "hex"):
        self.graph = nx.Graph()
        self.nodes: Dict[int, Tuple[float, float, str]] = {}
        self.dist_matrix: Dict[Tuple[int, int], float] = {}
        self.width = width
        self.height = height
        self.grid_type = grid_type
        self.depot_node = 0
        self.station_nodes: List[int] = []

    def generate_grid(
        self,
        num_nodes: int,
        num_stations: int = 3,
        seed: int = 42,
    ) -> None:
        """Generate a grid-like road network with randomized node positions.

        Features:
        - Grid layout with random jitter for visual variety
        - Guaranteed adjacency connections (up, down, left, right)
        - Optional diagonal connections
        - Depot placed near center of map
        """
        random.seed(seed)

        # Use larger node count for richer map
        if num_nodes < 40:
            num_nodes = 64

        # Calculate grid dimensions
        cols = int(math.sqrt(num_nodes))
        rows = (num_nodes + cols - 1) // cols

        # Ensure at least a reasonable grid
        cols = max(cols, 6)
        rows = max(rows, 6)
        num_nodes = min(num_nodes, cols * rows)

        # Generate nodes in a grid with jitter
        node_id = 0
        jitter_amount = 0.15  # 15% cell size jitter

        for row in range(rows):
            for col in range(cols):
                if node_id >= num_nodes:
                    break

                # Base grid position
                base_x = (col / max(cols - 1, 1)) * self.width
                base_y = (row / max(rows - 1, 1)) * self.height

                # Add random jitter
                cell_w = self.width / max(cols - 1, 1)
                cell_h = self.height / max(rows - 1, 1)
                jitter_x = random.uniform(-cell_w * jitter_amount, cell_w * jitter_amount)
                jitter_y = random.uniform(-cell_h * jitter_amount, cell_h * jitter_amount)

                x = max(0, min(self.width, base_x + jitter_x))
                y = max(0, min(self.height, base_y + jitter_y))

                self.add_node(node_id, x, y, "normal")
                node_id += 1

        # Place depot near center
        center_row = rows // 2
        center_col = cols // 2
        center_node_id = center_row * cols + center_col
        center_node_id = min(center_node_id, node_id - 1)

        self.depot_node = center_node_id
        cx, cy, _ = self.nodes[center_node_id]
        self.nodes[center_node_id] = (cx, cy, "depot")
        self.graph.nodes[center_node_id]["type"] = "depot"

        # Build guaranteed grid connections (adjacent neighbors)
        for row in range(rows):
            for col in range(cols):
                nid = row * cols + col
                if nid >= node_id:
                    continue

                # Right neighbor
                if col + 1 < cols:
                    right_id = row * cols + (col + 1)
                    if right_id < node_id:
                        self._add_edge_if_not_exists(nid, right_id)

                # Down neighbor
                if row + 1 < rows:
                    down_id = (row + 1) * cols + col
                    if down_id < node_id:
                        self._add_edge_if_not_exists(nid, down_id)

                # Diagonal connections (random, ~40% probability)
                if row + 1 < rows and col + 1 < cols:
                    diag_id = (row + 1) * cols + (col + 1)
                    if diag_id < node_id and random.random() < 0.4:
                        self._add_edge_if_not_exists(nid, diag_id)

                if row + 1 < rows and col - 1 >= 0:
                    diag_id = (row + 1) * cols + (col - 1)
                    if diag_id < node_id and random.random() < 0.4:
                        self._add_edge_if_not_exists(nid, diag_id)

        # Assign station nodes (random from non-depot, keep away from edges)
        non_depot = [n for n in self.nodes if n != self.depot_node]
        if len(non_depot) >= num_stations:
            # Exclude nodes too close to map edges (10% margin)
            margin_x = self.width * 0.1
            margin_y = self.height * 0.1
            candidates = [
                n for n in non_depot
                if margin_x <= self.nodes[n][0] <= self.width - margin_x
                and margin_y <= self.nodes[n][1] <= self.height - margin_y
            ]
            pool = candidates if len(candidates) >= num_stations else non_depot
            self.station_nodes = sorted(random.sample(pool, num_stations))
            for sid in self.station_nodes:
                x, y, _ = self.nodes[sid]
                self.nodes[sid] = (x, y, "station")
                self.graph.nodes[sid]["type"] = "station"

    def _add_edge_if_not_exists(self, u: int, v: int) -> None:
        """Add edge if it doesn't already exist."""
        if not self.graph.has_edge(u, v):
            ux, uy, _ = self.nodes[u]
            vx, vy, _ = self.nodes[v]
            dist = math.sqrt((ux - vx) ** 2 + (uy - vy) ** 2)
            self.graph.add_edge(u, v, weight=round(dist, 2))

    def add_node(self, node_id: int, x: float, y: float, node_type: str = "normal") -> None:
        """Add a node to the map."""
        self.nodes[node_id] = (x, y, node_type)
        self.graph.add_node(node_id, pos=(x, y), type=node_type)

    def add_road(self, u: int, v: int, distance: float = None) -> None:
        """Add a road (edge) between two nodes."""
        if distance is None:
            ux, uy, _ = self.nodes[u]
            vx, vy, _ = self.nodes[v]
            distance = math.sqrt((ux - vx) ** 2 + (uy - vy) ** 2)
        self.graph.add_edge(u, v, weight=round(distance, 2))

    def get_distance(self, u: int, v: int) -> float:
        """Get shortest path distance between two nodes."""
        if u == v:
            return 0.0
        if u not in self.graph or v not in self.graph:
            return float("inf")
        key = (min(u, v), max(u, v))
        if key not in self.dist_matrix:
            try:
                self.dist_matrix[key] = nx.shortest_path_length(
                    self.graph, u, v, weight="weight"
                )
            except nx.NetworkXNoPath:
                self.dist_matrix[key] = float("inf")
        return self.dist_matrix[key]

    def get_path(self, u: int, v: int) -> List[int]:
        """Get shortest path as list of node IDs."""
        try:
            return nx.shortest_path(self.graph, u, v, weight="weight")
        except nx.NetworkXNoPath:
            return []

    def find_nearest_station(self, node_id: int) -> Optional[int]:
        """Find nearest charging station to given node."""
        if not self.station_nodes or node_id not in self.graph:
            return None

        min_dist = float("inf")
        nearest = None
        for station_node in self.station_nodes:
            dist = self.get_distance(node_id, station_node)
            if dist < min_dist:
                min_dist = dist
                nearest = station_node
        return nearest

    def get_node_position(self, node_id: int) -> Tuple[float, float]:
        """Get world coordinates of a node."""
        return self.nodes[node_id][:2]

    def to_dict(self) -> dict:
        """Serialize to dictionary for frontend."""
        return {
            "nodes": [
                {"id": nid, "x": round(x, 2), "y": round(y, 2), "type": ntype}
                for nid, (x, y, ntype) in self.nodes.items()
            ],
            "edges": [
                {"u": u, "v": v, "weight": round(d["weight"], 2)}
                for u, v, d in self.graph.edges(data=True)
            ],
        }
