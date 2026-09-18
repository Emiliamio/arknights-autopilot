# -*- coding: utf-8 -*-
"""
Unit tests for TouchHumanizer
Author: Emiliamio <mio2110767128@163.com>
"""

import math
import pytest
from core.touch_humanizer import TouchHumanizer


def test_jitter_within_radius():
    th = TouchHumanizer(max_jitter_radius=8.0, jitter_sigma=3.0)
    for _ in range(100):
        jx, jy = th.jitter_point(960, 540)
        dist = math.hypot(jx - 960, jy - 540)
        assert dist <= 8.0001, f"Jitter distance {dist} exceeded maximum radius 8.0"


def test_screen_bounds_clamping():
    th = TouchHumanizer(screen_bounds=(1920, 1080))
    # Test near top-left origin
    for _ in range(50):
        jx, jy = th.jitter_point(0, 0)
        assert 0 <= jx < 1920
        assert 0 <= jy < 1080

    # Test near bottom-right edge
    for _ in range(50):
        jx, jy = th.jitter_point(1920, 1080)
        assert 0 <= jx < 1920
        assert 0 <= jy < 1080


def test_bezier_trajectory_endpoints():
    th = TouchHumanizer(screen_bounds=(1920, 1080))
    start_x, start_y = 200, 300
    end_x, end_y = 1000, 700

    traj = th.generate_bezier_trajectory(start_x, start_y, end_x, end_y, steps=15)
    assert len(traj) == 16, "15 steps must generate 16 points"

    p0 = traj[0]
    pn = traj[-1]
    assert p0[0] == start_x and p0[1] == start_y
    assert pn[0] == end_x and pn[1] == end_y

    for x, y, dt in traj:
        assert 0 <= x < 1920
        assert 0 <= y < 1080
        assert dt > 0.0


def test_bezier_curvature_non_colinear():
    th = TouchHumanizer(screen_bounds=(1920, 1080))
    # Test across multiple generated curves that at least some intermediate points curve away from line
    has_curvature = False
    for _ in range(10):
        traj = th.generate_bezier_trajectory(100, 100, 900, 900, steps=20)
        # Check area of triangle formed by P0, Pi, Pn
        p0 = traj[0]
        pn = traj[-1]
        for p in traj[1:-1]:
            # Cross product area
            area = abs((pn[0] - p0[0]) * (p0[1] - p[1]) - (p0[0] - p[0]) * (pn[1] - p0[1]))
            if area > 10.0:
                has_curvature = True
                break
        if has_curvature:
            break
    assert has_curvature, "Bezier curve must exhibit natural non-linear curvature"


def test_deploy_gesture_structure():
    th = TouchHumanizer()
    deploy = th.generate_deploy_gesture(300, 950, 800, 500, orientation="up")
    assert "pickup" in deploy
    assert "drag_trajectory" in deploy
    assert "flick_trajectory" in deploy
    assert len(deploy["drag_trajectory"]) >= 10
    assert len(deploy["flick_trajectory"]) >= 5
    assert deploy["pause_before_flick_ms"] > 0