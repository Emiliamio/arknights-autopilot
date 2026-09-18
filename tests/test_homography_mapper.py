# -*- coding: utf-8 -*-
"""
Unit tests for HomographyMapper (2.5D perspective mapping)
Author: Emiliamio <mio2110767128@163.com>
"""

import pytest
import numpy as np
from core.homography_mapper import HomographyMapper


def test_synthetic_arknights_mapper():
    mapper = HomographyMapper.create_synthetic_arknights_mapper(
        cols=11, rows=6, screen_resolution=(1920, 1080)
    )
    assert mapper.is_calibrated()

    cx, cy = mapper.get_tile_center(5, 3)
    assert 0 <= cx < 1920
    assert 0 <= cy < 1080


def test_round_trip_invertibility():
    mapper = HomographyMapper.create_synthetic_arknights_mapper(
        cols=11, rows=6, screen_resolution=(1920, 1080)
    )

    test_points = [(0.5, 0.5), (5.5, 2.5), (10.5, 5.5), (2.0, 4.0), (8.0, 1.0)]
    for gc, gr in test_points:
        sx, sy = mapper.grid_to_screen(gc, gr)
        rc, rr = mapper.screen_to_grid(sx, sy)
        assert abs(gc - rc) < 0.05, f"Column mismatch: expected {gc}, got {rc}"
        assert abs(gr - rr) < 0.05, f"Row mismatch: expected {gr}, got {rr}"


def test_dynamic_resolution_scaling():
    mapper = HomographyMapper.create_synthetic_arknights_mapper(
        cols=11, rows=6, screen_resolution=(1920, 1080)
    )
    cx_1080, cy_1080 = mapper.get_tile_center(5, 3)

    # Scale to 1280x720
    mapper.scale_to_resolution(1280, 720)
    cx_720, cy_720 = mapper.get_tile_center(5, 3)

    expected_x = int(round(cx_1080 * (1280.0 / 1920.0)))
    expected_y = int(round(cy_1080 * (720.0 / 1080.0)))
    assert abs(cx_720 - expected_x) <= 2
    assert abs(cy_720 - expected_y) <= 2


def test_screen_to_tile_lookup():
    mapper = HomographyMapper.create_synthetic_arknights_mapper(
        cols=11, rows=6, screen_resolution=(1920, 1080)
    )
    cx, cy = mapper.get_tile_center(4, 2)
    tile = mapper.get_tile_at_screen(cx, cy)
    assert tile == (4, 2), f"Expected tile (4, 2), got {tile}"


def test_tile_polygon_four_corners():
    mapper = HomographyMapper.create_synthetic_arknights_mapper(
        cols=11, rows=6, screen_resolution=(1920, 1080)
    )
    poly = mapper.get_tile_polygon(4, 2)
    assert len(poly) == 4, "Tile polygon must have 4 vertices"
    for x, y in poly:
        assert 0 <= x < 1920
        assert 0 <= y < 1080


def test_degenerate_points_rejection():
    grid_pts = [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, 3.0)]
    screen_pts = [(100.0, 100.0), (200.0, 200.0), (300.0, 300.0), (400.0, 400.0)]

    mapper = HomographyMapper()
    with pytest.raises((ValueError, RuntimeError)):
        mapper.calibrate(grid_pts, screen_pts)