# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Real-Time Battlefield Threat Monitor & Leak Detector
Author: Emiliamio <mio2110767128@163.com>
"""

from enum import IntEnum
from typing import List, Tuple, Dict, Any, Optional, Set
import numpy as np
import cv2

from tactical.map_deconstructor import TacticalMap, TileType
from tactical.choke_point_analyzer import AStarPathfinder
from core.homography_mapper import HomographyMapper


class ThreatLevel(IntEnum):
    """Graduated threat levels on the combat field."""
    SAFE = 0             # No imminent leaks
    MONITORING = 1       # Enemies on field, properly blocked by front line
    ALERT = 2            # High enemy density on front line
    PANIC_LEAK = 3       # Enemy within <= 2 tiles of Blue Goal with NO friendly blocker!


class EnemyEntity:
    """Represents a localized enemy on the tactical grid."""

    def __init__(
        self,
        screen_pos: Tuple[int, int],
        grid_pos: Tuple[int, int],  # (col, row)
        distance_to_goal: int,
        contour_area: float
    ):
        self.screen_pos = screen_pos
        self.col = grid_pos[0]
        self.row = grid_pos[1]
        self.grid_pos = grid_pos
        self.distance_to_goal = distance_to_goal
        self.contour_area = contour_area

    def to_dict(self) -> Dict[str, Any]:
        return {
            "screen_pos": list(self.screen_pos),
            "grid_pos": [self.col, self.row],
            "distance_to_goal": self.distance_to_goal,
            "contour_area": round(self.contour_area, 1)
        }


class ThreatMonitor:
    """
    Performs high-frequency scanning of battlefield red markers and enemy trajectories.
    Features:
    - Spatial clustering & deduplication of multi-part contours (HP bars + entities).
    - True A* corridor path navigation for intercept tile deduction.
    - Symmetrical orientation facing resolution.
    """

    def __init__(self, tactical_map: TacticalMap):
        self.map = tactical_map
        self.pathfinder = AStarPathfinder(tactical_map)

    def detect_enemies(
        self,
        frame: np.ndarray,
        mapper: HomographyMapper
    ) -> List[EnemyEntity]:
        """
        Extracts enemy entities using dual-peak red HSV thresholding,
        spatial projection to logical grid, and grid-cell clustering.
        """
        h, w = frame.shape[:2]

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([168, 100, 100]), np.array([180, 255, 255]))
        red_mask = cv2.bitwise_or(mask1, mask2)

        # Exclude UI areas
        red_mask[:int(h * 0.10), :] = 0
        red_mask[int(h * 0.85):, :] = 0
        red_mask[:, :int(w * 0.08)] = 0
        red_mask[:, int(w * 0.92):] = 0

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        opened = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
        dilated = cv2.dilate(opened, kernel, iterations=1)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Cluster by grid cell to merge entity + HP bar duplicate contours
        grid_clusters: Dict[Tuple[int, int], Dict[str, Any]] = {}

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 15.0 <= area <= 600.0:
                M = cv2.moments(cnt)
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])

                    col_f, row_f = mapper.screen_to_grid(cx, cy)
                    c = int(np.floor(col_f))
                    r = int(np.floor(row_f))

                    if self.map.in_bounds(r, c) and self.map.is_walkable(r, c):
                        if (r, c) not in self.map.spawns:
                            key = (c, r)
                            if key not in grid_clusters:
                                grid_clusters[key] = {
                                    "screen_pts": [(cx, cy)],
                                    "total_area": area,
                                    "col": c,
                                    "row": r
                                }
                            else:
                                grid_clusters[key]["screen_pts"].append((cx, cy))
                                grid_clusters[key]["total_area"] += area

        enemies = []
        for (c, r), cluster in grid_clusters.items():
            pts = cluster["screen_pts"]
            avg_x = sum(p[0] for p in pts) // len(pts)
            avg_y = sum(p[1] for p in pts) // len(pts)

            min_dist = 999
            for gr, gc in self.map.goals:
                d = abs(r - gr) + abs(c - gc)
                if d < min_dist:
                    min_dist = d

            enemies.append(EnemyEntity(
                screen_pos=(avg_x, avg_y),
                grid_pos=(c, r),
                distance_to_goal=min_dist,
                contour_area=cluster["total_area"]
            ))

        return enemies

    def evaluate_threat(
        self,
        enemies: List[EnemyEntity],
        active_blockers: Set[Tuple[int, int]]  # Set of (col, row) friendly blockers
    ) -> Tuple[ThreatLevel, Optional[Dict[str, Any]]]:
        """
        Evaluates threat level across all detected enemies using actual A* corridor navigation.
        Triggers PANIC_LEAK if an enemy is <= 2 tiles from Blue Goal with no blocker along their path.
        """
        if not enemies:
            return ThreatLevel.SAFE, None

        worst_level = ThreatLevel.MONITORING

        # Sort enemies by urgency (closest to goal first)
        sorted_enemies = sorted(enemies, key=lambda e: e.distance_to_goal)

        for enemy in sorted_enemies:
            if enemy.distance_to_goal <= 2:
                target_goal = None
                for gr, gc in self.map.goals:
                    if abs(enemy.row - gr) + abs(enemy.col - gc) == enemy.distance_to_goal:
                        target_goal = (gc, gr)
                        break

                if target_goal:
                    goal_c, goal_r = target_goal
                    path = self.pathfinder.find_shortest_path((enemy.row, enemy.col), (goal_r, goal_c))
                    if path and len(path) >= 2:
                        next_r, next_c = path[1]
                        int_c, int_r = next_c, next_r
                    else:
                        int_c, int_r = enemy.col, enemy.row

                    is_blocked = (int_c, int_r) in active_blockers or (enemy.col, enemy.row) in active_blockers

                    if not is_blocked:
                        # Determine orientation facing incoming enemy
                        if enemy.col > int_c:
                            facing = "right"
                        elif enemy.col < int_c:
                            facing = "left"
                        elif enemy.row > int_r:
                            facing = "down"
                        elif enemy.row < int_r:
                            facing = "up"
                        else:
                            # If on same tile, face opposite of goal direction
                            facing = "left" if goal_c >= int_c else "right"

                        critical_leak = {
                            "enemy_pos": (enemy.col, enemy.row),
                            "distance_to_goal": enemy.distance_to_goal,
                            "target_goal": target_goal,
                            "intercept_tile": (int_c, int_r),
                            "facing": facing,
                            "urgency": round(1.0 - (enemy.distance_to_goal / 3.0), 2)
                        }
                        return ThreatLevel.PANIC_LEAK, critical_leak
                    else:
                        worst_level = ThreatLevel.ALERT

        return worst_level, None