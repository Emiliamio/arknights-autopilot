# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Touch Humanizer & Anti-Detection Trajectory Generator
Author: Emiliamio <mio2110767128@163.com>
"""

import random
import math
from typing import List, Tuple, Dict, Any, Optional
import numpy as np


class TouchHumanizer:
    """
    Generates humanized touch and swipe trajectories using Cubic Bezier curves,
    Gaussian coordinate dispersion, boundary clamping, and human-muscle non-linear velocity profiles.
    """

    def __init__(
        self,
        jitter_sigma: float = 2.5,
        max_jitter_radius: float = 8.0,
        touch_down_duration_ms: Tuple[int, int] = (65, 110),
        swipe_duration_ms: Tuple[int, int] = (250, 400),
        default_steps: int = 20,
        screen_bounds: Tuple[int, int] = (1920, 1080)
    ):
        self.jitter_sigma = jitter_sigma
        self.max_jitter_radius = max_jitter_radius
        self.touch_down_duration_ms = touch_down_duration_ms
        self.swipe_duration_ms = swipe_duration_ms
        self.default_steps = default_steps
        self.screen_bounds = screen_bounds  # (max_width, max_height)

    def set_screen_bounds(self, width: int, height: int) -> None:
        """Dynamically updates screen boundaries for clamping."""
        self.screen_bounds = (max(1, width), max(1, height))

    def clamp_coordinates(self, x: float, y: float) -> Tuple[int, int]:
        """Clamps (x, y) strictly within [0, max_w - 1] and [0, max_h - 1]."""
        max_w, max_h = self.screen_bounds
        cx = max(0, min(int(round(x)), max_w - 1))
        cy = max(0, min(int(round(y)), max_h - 1))
        return cx, cy

    def jitter_point(self, x: float, y: float) -> Tuple[int, int]:
        """
        Applies a 2D Gaussian jitter to the target point.
        Strictly guarantees:
        1. Discrete Euclidean distance <= max_jitter_radius.
        2. Coordinates clamped within screen boundaries.
        """
        dx = random.gauss(0, self.jitter_sigma)
        dy = random.gauss(0, self.jitter_sigma)
        r = math.hypot(dx, dy)
        if r > self.max_jitter_radius and r > 0:
            scale = self.max_jitter_radius / r
            dx *= scale
            dy *= scale

        ix = int(round(dx))
        iy = int(round(dy))

        # Enforce strict discrete Euclidean bound after integer rounding
        while math.hypot(ix, iy) > self.max_jitter_radius:
            if abs(ix) >= abs(iy) and ix != 0:
                ix -= 1 if ix > 0 else -1
            elif iy != 0:
                iy -= 1 if iy > 0 else -1
            else:
                break

        return self.clamp_coordinates(x + ix, y + iy)

    def generate_tap(self, x: float, y: float) -> Dict[str, Any]:
        """
        Generates tap parameters with randomized coordinates, boundary checks, and hold duration.
        """
        jx, jy = self.jitter_point(x, y)
        duration_ms = random.randint(self.touch_down_duration_ms[0], self.touch_down_duration_ms[1])
        return {
            "x": jx,
            "y": jy,
            "duration_ms": duration_ms,
            "duration_sec": duration_ms / 1000.0
        }

    def generate_bezier_trajectory(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        steps: Optional[int] = None,
        duration_ms: Optional[int] = None,
        add_tremor: bool = True
    ) -> List[Tuple[int, int, float]]:
        """
        Generates a cubic Bezier trajectory with humanized control points and ease-in-out timing.
        Returns a list of tuples: (x, y, sleep_after_step_sec)
        All coordinates are guaranteed bounded within screen limits.
        """
        if steps is None:
            steps = self.default_steps
        steps = max(2, steps)

        if duration_ms is None:
            duration_ms = random.randint(self.swipe_duration_ms[0], self.swipe_duration_ms[1])

        # Clamp start and end
        sx, sy = self.clamp_coordinates(start_x, start_y)
        ex, ey = self.clamp_coordinates(end_x, end_y)

        p0 = np.array([sx, sy], dtype=np.float64)
        p3 = np.array([ex, ey], dtype=np.float64)

        delta = p3 - p0
        dist = np.linalg.norm(delta)
        if dist < 1.0:
            return [(sx, sy, duration_ms / 1000.0)]

        # Normal vector perpendicular to movement vector
        unit_u = delta / dist
        unit_n = np.array([-unit_u[1], unit_u[0]], dtype=np.float64)

        # Random control point offsets (alpha along line, beta normal to line)
        alpha1 = random.uniform(0.20, 0.40)
        alpha2 = random.uniform(0.60, 0.80)
        curve_intensity = random.uniform(-0.10, 0.10)
        beta1 = curve_intensity * dist * random.uniform(0.8, 1.2)
        beta2 = curve_intensity * dist * random.uniform(0.8, 1.2)

        p1 = p0 + alpha1 * delta + beta1 * unit_n
        p2 = p0 + alpha2 * delta + beta2 * unit_n

        trajectory = []
        total_duration_sec = duration_ms / 1000.0

        for i in range(steps + 1):
            s = i / float(steps)
            # Smooth non-linear ease-in-out: starts gently, accelerates, then decelerates
            t = 0.5 * (1.0 - math.cos(math.pi * s))

            # Cubic Bezier: B(t) = (1-t)^3 P0 + 3(1-t)^2 t P1 + 3(1-t) t^2 P2 + t^3 P3
            bx = (1 - t)**3 * p0[0] + 3 * (1 - t)**2 * t * p1[0] + 3 * (1 - t) * t**2 * p2[0] + t**3 * p3[0]
            by = (1 - t)**3 * p0[1] + 3 * (1 - t)**2 * t * p1[1] + 3 * (1 - t) * t**2 * p2[1] + t**3 * p3[1]

            # Physiological micro-tremor for intermediate path nodes
            if add_tremor and 0 < i < steps:
                bx += random.gauss(0, 0.6)
                by += random.gauss(0, 0.6)

            # Strictly clamp inside display limits
            cx, cy = self.clamp_coordinates(bx, by)

            # Realistic step delta time
            step_dt = (total_duration_sec / steps) * (1.2 - 0.4 * math.sin(math.pi * s))
            trajectory.append((cx, cy, max(0.001, step_dt)))

        return trajectory

    def generate_deploy_gesture(
        self,
        card_x: float,
        card_y: float,
        target_grid_x: float,
        target_grid_y: float,
        orientation: str = "right"
    ) -> Dict[str, Any]:
        """
        Generates full operator deployment sequence:
        1. Card pickup (tap down with hold);
        2. Drag from hand to target grid (smooth Bezier);
        3. Pause to confirm grid placement (80~150ms);
        4. Orientation direction flick (gesture flick according to orientation);
        5. Touch release.
        """
        pickup = self.generate_tap(card_x, card_y)
        drag_trajectory = self.generate_bezier_trajectory(
            pickup["x"], pickup["y"],
            target_grid_x, target_grid_y,
            steps=18,
            duration_ms=random.randint(220, 300)
        )

        flick_offsets = {
            "up": (0, -160),
            "down": (0, 160),
            "left": (-160, 0),
            "right": (160, 0)
        }
        dx, dy = flick_offsets.get(orientation.lower(), (160, 0))
        flick_end_x, flick_end_y = self.jitter_point(target_grid_x + dx, target_grid_y + dy)
        flick_trajectory = self.generate_bezier_trajectory(
            target_grid_x, target_grid_y,
            flick_end_x, flick_end_y,
            steps=8,
            duration_ms=random.randint(100, 150)
        )

        return {
            "pickup": pickup,
            "drag_trajectory": drag_trajectory,
            "pause_before_flick_ms": random.randint(80, 140),
            "flick_trajectory": flick_trajectory
        }