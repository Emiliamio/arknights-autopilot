# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
2.5D Isometric Homography Projection & Coordinate Mapper
Author: Emiliamio <mio2110767128@163.com>
"""

from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import cv2


class HomographyMapper:
    """
    Solves and manages the 3x3 projective transformation (Homography Matrix H)
    between logical grid coordinates (col, row) and screen physical pixel coordinates (x, y).

    Features:
    - Forward and inverse sub-pixel coordinate transforms.
    - Dynamic resolution scaling (e.g. 1080P -> 720P / 2K).
    - Vanishing horizon protection (w' > 0 verification).
    - Screen-to-tile discrete lookup with bounds checking.
    """

    def __init__(
        self,
        grid_points: Optional[List[Tuple[float, float]]] = None,
        screen_points: Optional[List[Tuple[float, float]]] = None,
        screen_resolution: Tuple[int, int] = (1920, 1080),
        grid_dims: Optional[Tuple[int, int]] = None
    ):
        self.screen_resolution = screen_resolution  # (width, height)
        self.grid_dims = grid_dims  # (cols, rows)
        self.H: Optional[np.ndarray] = None
        self.H_inv: Optional[np.ndarray] = None

        if grid_points is not None and screen_points is not None:
            self.calibrate(grid_points, screen_points)

    def calibrate(
        self,
        grid_points: List[Tuple[float, float]],
        screen_points: List[Tuple[float, float]]
    ) -> np.ndarray:
        """
        Calibrates the 3x3 Homography matrix using 4 or more corresponding points.
        """
        if len(grid_points) < 4 or len(screen_points) < 4:
            raise ValueError(f"At least 4 reference points required for homography, got {len(grid_points)}")

        if len(grid_points) != len(screen_points):
            raise ValueError(f"Mismatched points count: {len(grid_points)} grid vs {len(screen_points)} screen")

        src = np.array(grid_points, dtype=np.float32).reshape(-1, 1, 2)
        dst = np.array(screen_points, dtype=np.float32).reshape(-1, 1, 2)

        H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
        if H is None:
            H, _ = cv2.findHomography(src, dst, 0)

        if H is None:
            raise RuntimeError("Failed to compute valid Homography matrix. Points may be collinear or degenerate.")

        det = np.linalg.det(H)
        if abs(det) < 1e-9:
            raise ValueError(f"Computed Homography matrix is singular (det={det:.2e}). Check reference points.")

        self.H = H
        self.H_inv = np.linalg.inv(H)
        return self.H

    def is_calibrated(self) -> bool:
        """Checks if the mapper has a valid projection matrix."""
        return self.H is not None and self.H_inv is not None

    def scale_to_resolution(self, new_width: int, new_height: int) -> None:
        """
        Dynamically adapts the homography matrix to a new screen resolution.
        Scale matrix: S = diag(w_new / w_old, h_new / h_old, 1.0)
        H_new = S * H_old
        """
        if not self.is_calibrated():
            raise RuntimeError("Cannot scale uncalibrated HomographyMapper.")

        old_w, old_h = self.screen_resolution
        if old_w <= 0 or old_h <= 0 or new_width <= 0 or new_height <= 0:
            raise ValueError(f"Invalid dimensions for scaling: old=({old_w}, {old_h}), new=({new_width}, {new_height})")

        sx = float(new_width) / float(old_w)
        sy = float(new_height) / float(old_h)

        S = np.array([
            [sx, 0.0, 0.0],
            [0.0, sy, 0.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

        self.H = np.dot(S, self.H)
        self.H_inv = np.linalg.inv(self.H)
        self.screen_resolution = (new_width, new_height)

    def grid_to_screen(self, col: float, row: float) -> Tuple[int, int]:
        """
        Transforms a continuous grid coordinate (col, row) to screen physical pixel (x, y).
        Safely verifies vanishing plane w' > 0.
        """
        if self.H is None:
            raise RuntimeError("HomographyMapper is not calibrated. Call calibrate() first.")

        # Project homogeneous vector [c, r, 1]^T
        v = np.array([col, row, 1.0], dtype=np.float64)
        proj = np.dot(self.H, v)
        w_prime = proj[2]
        if w_prime <= 1e-6:
            raise ValueError(f"Projective coordinate at ({col}, {row}) lies on or behind vanishing horizon (w'={w_prime})")

        x = proj[0] / w_prime
        y = proj[1] / w_prime

        max_w, max_h = self.screen_resolution
        cx = max(0, min(int(round(x)), max_w - 1))
        cy = max(0, min(int(round(y)), max_h - 1))
        return cx, cy

    def screen_to_grid(self, x: float, y: float) -> Tuple[float, float]:
        """
        Transforms a physical screen pixel coordinate (x, y) back to continuous grid coordinate (col, row).
        """
        if self.H_inv is None:
            raise RuntimeError("HomographyMapper is not calibrated. Call calibrate() first.")

        v = np.array([x, y, 1.0], dtype=np.float64)
        proj = np.dot(self.H_inv, v)
        w_prime = proj[2]
        if abs(w_prime) <= 1e-9:
            raise ValueError(f"Singular point at screen coordinate ({x}, {y})")

        col = proj[0] / w_prime
        row = proj[1] / w_prime
        return float(col), float(row)

    def get_tile_at_screen(self, x: float, y: float) -> Optional[Tuple[int, int]]:
        """
        Maps screen pixel (x, y) to the discrete integer tile (col, row).
        Returns None if coordinates fall outside calibrated grid dimensions.
        """
        col_f, row_f = self.screen_to_grid(x, y)
        c = int(np.floor(col_f))
        r = int(np.floor(row_f))

        if self.grid_dims:
            max_c, max_r = self.grid_dims
            if not (0 <= c < max_c and 0 <= r < max_r):
                return None
        return c, r

    def get_tile_center(self, col: int, row: int) -> Tuple[int, int]:
        """Returns the screen pixel coordinate of tile center (col + 0.5, row + 0.5)."""
        return self.grid_to_screen(col + 0.5, row + 0.5)

    def get_tile_polygon(self, col: int, row: int) -> List[Tuple[int, int]]:
        """Returns 4 screen pixel vertices of tile (col, row): [TL, TR, BR, BL]."""
        corners = [
            (col, row),
            (col + 1.0, row),
            (col + 1.0, row + 1.0),
            (col, row + 1.0)
        ]
        return [self.grid_to_screen(c, r) for c, r in corners]

    @classmethod
    def create_synthetic_arknights_mapper(
        cls,
        cols: int = 11,
        rows: int = 6,
        screen_resolution: Tuple[int, int] = (1920, 1080),
        margin_x: float = 240.0,
        margin_top: float = 160.0,
        margin_bottom: float = 200.0,
        trapezoid_keystone: float = 0.08
    ) -> "HomographyMapper":
        """
        Factory method: Generates an accurate 2.5D perspective HomographyMapper
        synthesized for Arknights battlefields at given screen resolution.
        """
        sw, sh = screen_resolution

        grid_pts = [
            (0.0, 0.0),
            (float(cols), 0.0),
            (float(cols), float(rows)),
            (0.0, float(rows))
        ]

        keystone_offset = sw * trapezoid_keystone
        top_y = margin_top
        bottom_y = sh - margin_bottom

        screen_pts = [
            (margin_x + keystone_offset, top_y),
            (sw - margin_x - keystone_offset, top_y),
            (sw - margin_x, bottom_y),
            (margin_x, bottom_y)
        ]

        mapper = cls(screen_resolution=screen_resolution, grid_dims=(cols, rows))
        mapper.calibrate(grid_pts, screen_pts)
        return mapper