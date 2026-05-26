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
        connection_prob: float = 0.4,
        seed: int = 42,
    ) -> None:
        """Generate a grid-like road network."""
        random.seed(seed)

        # Calculate grid dimensions
        cols = int(math.sqrt(num_nodes))
        rows = (num_nodes + cols - 1) // cols

        # Generate nodes in a grid
        node_id = 0
        for row in range(rows):
            for col in range(cols):
                if node_id >= num_nodes:
                    break

                x = (col / max(cols - 1, 1)) * self.width
                y = (row / max(rows - 1, 1)) * self.height

                # First node is depot
                node_type = "depot" if node_id == 0 else "normal"
                self.add_node(node_id, x, y, node_type)
                node_id += 1

        # Add some random connections for irregularity
        extra_nodes = num_nodes - node_id
        for i in range(extra_nodes):
            x = random.uniform(0, self.width)
            y = random.uniform(0, self.height)
            self.add_node(node_id, x, y, "normal")
            node_id += 1

        # Connect neighboring nodes
        for node_id in self.nodes:
            x, y, _ = self.nodes[node_id]
            # Find nearest nodes
            neighbors = []
            for other_id in self.nodes:
                if other_id == node_id:
                    continue
                ox, oy, _ = self.nodes[other_id]
                dist = math.sqrt((x - ox) ** 2 + (y - oy) ** 2)
                neighbors.append((dist, other_id))

            neighbors.sort()
            # Connect to 2-4 nearest neighbors
            num_connections = random.randint(2, 4)
            for dist, other_id in neighbors[:num_connections]:
                if not self.graph.has_edge(node_id, other_id):
                    self.add_road(node_id, other_id, dist)

        # Assign station nodes (pick from non-depot nodes)
        non_depot = [n for n in self.nodes if n != self.depot_node]
        if len(non_depot) >= num_stations:
            self.station_nodes = sorted(random.sample(non_depot, num_stations))
            for sid in self.station_nodes:
                x, y, _ = self.nodes[sid]
                self.nodes[sid] = (x, y, "station")
                self.graph.nodes[sid]["type"] = "station"

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
        if not self.station_nodes:
            return None

        min_dist = float("inf")
        nearest = self.station_nodes[0]
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
