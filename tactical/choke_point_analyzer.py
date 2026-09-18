# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
A* Pathfinding, Shortest-Path DAG Flow Analysis & Tactical Scorer
Author: Emiliamio <mio2110767128@163.com>
"""

import heapq
from collections import deque
from typing import List, Tuple, Dict, Any, Optional, Set
from tactical.map_deconstructor import TacticalMap, TileType


class AStarPathfinder:
    """
    Standard A* grid pathfinder tailored for Arknights enemy trajectory deduction.
    Uses Manhattan heuristic and handles multi-source multi-goal path convergence.
    """

    def __init__(self, tactical_map: TacticalMap):
        self.map = tactical_map

    def heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """Manhattan distance heuristic: |r1 - r2| + |c1 - c2|."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def find_shortest_path(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int]
    ) -> Optional[List[Tuple[int, int]]]:
        """
        Finds the primary shortest walkable path from start (r, c) to goal (r, c).
        """
        if not self.map.is_walkable(start[0], start[1]) or not self.map.is_walkable(goal[0], goal[1]):
            return None

        tie_breaker = 0
        frontier = [(self.heuristic(start, goal), 0, start)]
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        cost_so_far: Dict[Tuple[int, int], float] = {start: 0.0}

        while frontier:
            _, _, current = heapq.heappop(frontier)

            if current == goal:
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                return path

            for neighbor in self.map.get_walkable_neighbors(current[0], current[1]):
                new_cost = cost_so_far[current] + 1.0
                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    priority = new_cost + self.heuristic(neighbor, goal)
                    tie_breaker += 1
                    heapq.heappush(frontier, (priority, tie_breaker, neighbor))
                    came_from[neighbor] = current

        return None

    def compute_shortest_path_dag_flow(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int]
    ) -> Dict[Tuple[int, int], float]:
        """
        Computes exact traffic flow probabilities across ALL possible shortest paths
        using layered DAG dynamic programming (Brandes' betweenness flow).
        Eliminates branch blind spots on maps with symmetrical forks or alternative corridors.
        Returns: { (r, c): probability_in_[0.0, 1.0] }
        """
        if not self.map.is_walkable(start[0], start[1]) or not self.map.is_walkable(goal[0], goal[1]):
            return {}

        dist = {start: 0}
        q = deque([start])
        order = []
        children: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}

        while q:
            u = q.popleft()
            order.append(u)
            children[u] = []
            for v in self.map.get_walkable_neighbors(u[0], u[1]):
                if v not in dist:
                    dist[v] = dist[u] + 1
                    q.append(v)

        if goal not in dist:
            return {}

        # Build DAG edges (only steps strictly advancing shortest distance)
        for u in order:
            for v in self.map.get_walkable_neighbors(u[0], u[1]):
                if dist.get(v) == dist.get(u, -1) + 1:
                    children[u].append(v)

        # Forward DP: Number of shortest paths from start to u
        num_from_start = {start: 1}
        for u in order:
            cnt = num_from_start.get(u, 0)
            for v in children.get(u, []):
                num_from_start[v] = num_from_start.get(v, 0) + cnt

        total_paths = num_from_start.get(goal, 0)
        if total_paths == 0:
            return {}

        # Backward DP: Number of shortest paths from u to goal
        num_to_goal = {goal: 1}
        for u in reversed(order):
            if u == goal:
                continue
            cnt = 0
            for v in children.get(u, []):
                cnt += num_to_goal.get(v, 0)
            num_to_goal[u] = cnt

        flow = {}
        for u in order:
            if u in num_from_start and u in num_to_goal:
                paths_thru_u = num_from_start[u] * num_to_goal[u]
                flow[u] = round(paths_thru_u / total_paths, 4)

        return flow

    def find_all_spawn_goal_paths(self) -> List[Dict[str, Any]]:
        """Computes shortest paths and flow distributions for all (Spawn, Goal) pairs."""
        results = []
        for s in self.map.spawns:
            for g in self.map.goals:
                path = self.find_shortest_path(s, g)
                flow = self.compute_shortest_path_dag_flow(s, g)
                if path:
                    results.append({
                        "spawn": s,
                        "goal": g,
                        "length": len(path),
                        "path": path,
                        "flow": flow
                    })
        return results


class ChokePointAnalyzer:
    """
    Analyzes spatial convergence of enemy trajectories to extract
    Primary and Secondary Choke Points, traffic density, and cut-vertices.
    """

    def __init__(self, tactical_map: TacticalMap):
        self.map = tactical_map
        self.pathfinder = AStarPathfinder(tactical_map)

    def analyze_choke_points(self) -> Dict[str, Any]:
        """Performs full choke point and flow extraction."""
        routes = self.pathfinder.find_all_spawn_goal_paths()
        if not routes:
            return {
                "routes_count": 0,
                "primary_choke": None,
                "secondary_chokes": [],
                "heat_matrix": {},
                "flow_matrix": {},
                "deployable_ranked": []
            }

        heat: Dict[Tuple[int, int], int] = {}
        cumulative_flow: Dict[Tuple[int, int], float] = {}

        for r in routes:
            for node in r["path"]:
                heat[node] = heat.get(node, 0) + 1
            for node, prob in r.get("flow", {}).items():
                cumulative_flow[node] = cumulative_flow.get(node, 0.0) + prob

        total_routes = len(routes)

        deployable_ranked = []
        for r in range(self.map.rows):
            for c in range(self.map.cols):
                if self.map.is_deployable_ground(r, c):
                    cnt = heat.get((r, c), 0)
                    flow_val = cumulative_flow.get((r, c), 0.0)
                    if cnt > 0 or flow_val > 0.0:
                        criticality = cnt / float(total_routes)
                        deployable_ranked.append({
                            "coord": (r, c),
                            "heat": cnt,
                            "flow": round(flow_val, 3),
                            "criticality": round(criticality, 3)
                        })

        # Rank by cumulative flow and heat
        deployable_ranked.sort(key=lambda x: (x["flow"], x["heat"]), reverse=True)

        primary_choke = deployable_ranked[0] if deployable_ranked else None

        secondary_chokes = []
        if primary_choke:
            pr, pc = primary_choke["coord"]
            for cand in deployable_ranked[1:]:
                cr, cc = cand["coord"]
                manhattan_dist = abs(pr - cr) + abs(pc - cc)
                if manhattan_dist >= 2 and cand["flow"] > 0:
                    secondary_chokes.append(cand)
                    if len(secondary_chokes) >= 2:
                        break

        return {
            "routes_count": total_routes,
            "routes": routes,
            "heat_matrix": {f"{r},{c}": v for (r, c), v in heat.items()},
            "flow_matrix": {f"{r},{c}": v for (r, c), v in cumulative_flow.items()},
            "primary_choke": primary_choke,
            "secondary_chokes": secondary_chokes,
            "deployable_ranked": deployable_ranked
        }


class HighGroundScorer:
    """
    Evaluates tactical value and optimal operator orientation for all High Ground tiles.
    Covers Sniper (Physical DPS), Caster (Arts DPS), and Medic (Healer coverage) roles.
    """

    ORIENTATION_VECTORS = {
        "up": (-1, 0),
        "down": (1, 0),
        "left": (0, -1),
        "right": (0, 1)
    }

    def __init__(self, tactical_map: TacticalMap):
        self.map = tactical_map

    def get_sniper_fov(self, r: int, c: int, orientation: str) -> Set[Tuple[int, int]]:
        """Sniper range: 3 tiles forward, 3 tiles wide."""
        fov = set()
        dr, dc = self.ORIENTATION_VECTORS.get(orientation.lower(), (0, 1))

        if dr == 0:
            step_c = dc
            for d in range(1, 4):
                tc = c + step_c * d
                for tr in (r - 1, r, r + 1):
                    if self.map.in_bounds(tr, tc):
                        fov.add((tr, tc))
        else:
            step_r = dr
            for d in range(1, 4):
                tr = r + step_r * d
                for tc in (c - 1, c, c + 1):
                    if self.map.in_bounds(tr, tc):
                        fov.add((tr, tc))

        return fov

    def get_medic_fov(self, r: int, c: int, orientation: str) -> Set[Tuple[int, int]]:
        """Medic range: 3x3 surrounding grid plus 1 forward extension."""
        fov = set()
        dr, dc = self.ORIENTATION_VECTORS.get(orientation.lower(), (0, 1))

        # 3x3 surrounding box
        for tr in (r - 1, r, r + 1):
            for tc in (c - 1, c, c + 1):
                if self.map.in_bounds(tr, tc):
                    fov.add((tr, tc))

        # 1-tile forward extension
        fwd_r, fwd_c = r + dr * 2, c + dc * 2
        if self.map.in_bounds(fwd_r, fwd_c):
            fov.add((fwd_r, fwd_c))

        return fov

    def score_high_grounds(
        self,
        choke_analysis: Dict[str, Any],
        choke_weight: float = 4.0,
        path_weight: float = 1.0
    ) -> List[Dict[str, Any]]:
        """Scores high ground tiles for DPS snipers."""
        choke_points = set()
        if choke_analysis.get("primary_choke"):
            choke_points.add(tuple(choke_analysis["primary_choke"]["coord"]))
        for sc in choke_analysis.get("secondary_chokes", []):
            choke_points.add(tuple(sc["coord"]))

        path_tiles = set()
        for route in choke_analysis.get("routes", []):
            for node in route["path"]:
                path_tiles.add(tuple(node))

        scores = []
        for r in range(self.map.rows):
            for c in range(self.map.cols):
                if self.map.is_deployable_high(r, c):
                    best_orient = "right"
                    best_score = -1.0
                    best_chokes = []
                    best_paths = []

                    for orient in ["up", "down", "left", "right"]:
                        fov = self.get_sniper_fov(r, c, orient)
                        covered_chokes = [pt for pt in fov if pt in choke_points]
                        covered_paths = [pt for pt in fov if pt in path_tiles and pt not in choke_points]

                        score = len(covered_chokes) * choke_weight + len(covered_paths) * path_weight
                        if score > best_score:
                            best_score = score
                            best_orient = orient
                            best_chokes = covered_chokes
                            best_paths = covered_paths

                    if best_score > 0:
                        scores.append({
                            "coord": (r, c),
                            "optimal_orientation": best_orient,
                            "tactical_score": round(best_score, 1),
                            "covered_chokes_count": len(best_chokes),
                            "covered_paths_count": len(best_paths),
                            "role": "SNIPER_DPS"
                        })

        scores.sort(key=lambda x: x["tactical_score"], reverse=True)
        return scores

    def score_medic_positions(
        self,
        choke_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Scores high ground tiles for Medic healers.
        Prioritizes positions that heal ground blockers at Choke Points.
        """
        choke_points = set()
        if choke_analysis.get("primary_choke"):
            choke_points.add(tuple(choke_analysis["primary_choke"]["coord"]))
        for sc in choke_analysis.get("secondary_chokes", []):
            choke_points.add(tuple(sc["coord"]))

        medic_scores = []
        for r in range(self.map.rows):
            for c in range(self.map.cols):
                if self.map.is_deployable_high(r, c):
                    best_orient = "down"
                    best_score = -1.0
                    best_healed_chokes = []

                    for orient in ["up", "down", "left", "right"]:
                        fov = self.get_medic_fov(r, c, orient)
                        healed_chokes = [pt for pt in fov if pt in choke_points]
                        # Score: 10 points per covered choke point blocker
                        score = len(healed_chokes) * 10.0
                        if score > best_score:
                            best_score = score
                            best_orient = orient
                            best_healed_chokes = healed_chokes

                    if best_score > 0:
                        medic_scores.append({
                            "coord": (r, c),
                            "optimal_orientation": best_orient,
                            "medic_score": round(best_score, 1),
                            "healed_chokes_count": len(best_healed_chokes),
                            "role": "MEDIC_HEALER"
                        })

        medic_scores.sort(key=lambda x: x["medic_score"], reverse=True)
        return medic_scores