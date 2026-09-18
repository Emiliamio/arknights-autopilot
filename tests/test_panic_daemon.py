# -*- coding: utf-8 -*-
"""
Unit tests for PanicDaemon & Emergency Interception
Author: Emiliamio <mio2110767128@163.com>
"""

import pytest
from tactical.map_deconstructor import TacticalMap
from tactical.panic_daemon import PanicDaemon
from core.homography_mapper import HomographyMapper
from core.touch_humanizer import TouchHumanizer


@pytest.fixture
def daemon():
    t_map = TacticalMap.create_1_7()
    return PanicDaemon(t_map)


def test_blocker_registry(daemon):
    assert len(daemon.active_blockers) == 0
    daemon.register_blocker(9, 2)
    assert (9, 2) in daemon.active_blockers

    daemon.unregister_blocker(9, 2)
    assert (9, 2) not in daemon.active_blockers


def test_select_emergency_operator(daemon):
    cards = [
        {"slot_index": 0, "is_ready": False, "center": (400, 980)},
        {"slot_index": 1, "is_ready": True, "center": (550, 980)},
        {"slot_index": 2, "is_ready": True, "center": (700, 980)}
    ]
    picked = daemon.select_emergency_operator(cards)
    assert picked is not None
    assert picked["slot_index"] == 1, "Must pick the first available ready card"


def test_execute_emergency_intercept(daemon):
    mapper = HomographyMapper.create_synthetic_arknights_mapper()
    humanizer = TouchHumanizer()

    leak_info = {
        "enemy_pos": (8, 2),
        "distance_to_goal": 2,
        "intercept_tile": (9, 2),
        "facing": "left"
    }
    cards = [
        {"slot_index": 0, "is_ready": True, "center": (450, 980)}
    ]

    # First intercept: must succeed
    res = daemon.execute_emergency_intercept(
        leak_info=leak_info,
        cards=cards,
        mapper=mapper,
        humanizer=humanizer,
        adb_client=None
    )
    assert res["status"] == "INTERCEPTED"
    assert res["intercept_tile"] == (9, 2)
    assert (9, 2) in daemon.active_blockers

    # Second immediate intercept to same tile within cooldown: must be suppressed
    res2 = daemon.execute_emergency_intercept(
        leak_info=leak_info,
        cards=cards,
        mapper=mapper,
        humanizer=humanizer,
        adb_client=None
    )
    assert res2["status"] == "COOLDOWN_SUPPRESSED"