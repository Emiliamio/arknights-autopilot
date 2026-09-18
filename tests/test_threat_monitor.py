# -*- coding: utf-8 -*-
"""
Unit tests for ThreatMonitor & Leak Detector
Author: Emiliamio <mio2110767128@163.com>
"""

import pytest
import numpy as np
import cv2

from tactical.map_deconstructor import TacticalMap
from tactical.threat_monitor import ThreatMonitor, ThreatLevel, EnemyEntity
from core.homography_mapper import HomographyMapper


@pytest.fixture
def monitor():
    t_map = TacticalMap.create_1_7()
    return ThreatMonitor(t_map)


def test_detect_enemies_red_blob(monitor):
    mapper = HomographyMapper.create_synthetic_arknights_mapper()
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)

    # Draw bright red enemy on walkable tile (col=3, row=1)
    cx, cy = mapper.get_tile_center(3, 1)
    cv2.circle(frame, (cx, cy), 12, (20, 20, 220), -1)  # Pure bright red

    enemies = monitor.detect_enemies(frame, mapper)
    assert len(enemies) == 1, f"Expected 1 enemy detected, found {len(enemies)}"
    assert enemies[0].col == 3
    assert enemies[0].row == 1


def test_evaluate_threat_safe_when_no_enemies(monitor):
    level, leak = monitor.evaluate_threat([], active_blockers=set())
    assert level == ThreatLevel.SAFE
    assert leak is None


def test_evaluate_threat_monitoring_when_distant(monitor):
    # Enemy at (3, 1), goal at (10, 2), distance is |3-10| + |1-2| = 7 + 1 = 8 > 2
    enemy = EnemyEntity(screen_pos=(500, 300), grid_pos=(3, 1), distance_to_goal=8, contour_area=50.0)
    level, leak = monitor.evaluate_threat([enemy], active_blockers=set())
    assert level == ThreatLevel.MONITORING
    assert leak is None


def test_evaluate_threat_panic_leak_when_unblocked(monitor):
    # Enemy reached (9, 2), 1 step from Goal at (10, 2) with NO blocker!
    enemy = EnemyEntity(screen_pos=(1600, 540), grid_pos=(9, 2), distance_to_goal=1, contour_area=50.0)
    level, leak = monitor.evaluate_threat([enemy], active_blockers=set())

    assert level == ThreatLevel.PANIC_LEAK, "Must trigger PANIC_LEAK when unblocked enemy <= 2 tiles from goal"
    assert leak is not None
    assert leak["enemy_pos"] == (9, 2)
    assert leak["intercept_tile"] in [(9, 2), (10, 2)]


def test_evaluate_threat_alert_when_properly_blocked(monitor):
    # Enemy at (9, 2), but friendly blocker is active at (9, 2)
    enemy = EnemyEntity(screen_pos=(1600, 540), grid_pos=(9, 2), distance_to_goal=1, contour_area=50.0)
    active_blockers = {(9, 2)}

    level, leak = monitor.evaluate_threat([enemy], active_blockers=active_blockers)
    assert level == ThreatLevel.ALERT, "Must return ALERT (not PANIC_LEAK) when front line blocker is active"
    assert leak is None