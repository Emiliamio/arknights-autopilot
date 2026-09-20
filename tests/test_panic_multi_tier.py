# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Unit tests for PanicDaemon Multi-Tier Emergency Defense Protocols
Author: Emiliamio <mio2110767128@163.com>
"""

import pytest
import time
from unittest.mock import MagicMock

from tactical.map_deconstructor import TacticalMap
from tactical.panic_daemon import PanicDaemon, EmergencyTier
from core.homography_mapper import HomographyMapper
from core.touch_humanizer import TouchHumanizer
from core.adb_client import ADBClient


@pytest.fixture
def panic_setup():
    t_map = TacticalMap.create_1_7()
    daemon = PanicDaemon(t_map)
    mapper = HomographyMapper.create_synthetic_arknights_mapper()
    humanizer = TouchHumanizer()
    adb = MagicMock(spec=ADBClient)
    return daemon, mapper, humanizer, adb


def test_emergency_tier_enum_values():
    assert EmergencyTier.TIER_1_DROP.value == "TIER_1_DROP"
    assert EmergencyTier.TIER_2_BURST.value == "TIER_2_BURST"
    assert EmergencyTier.TIER_3_RELAY.value == "TIER_3_RELAY"


def test_tier_1_fast_redeploy_drop_success(panic_setup):
    daemon, mapper, humanizer, adb = panic_setup
    leak_info = {
        "enemy_pos": (9.0, 1.2),
        "intercept_tile": (9, 2),
        "facing": "right"
    }
    cards = [
        {"slot_index": 0, "center": (100, 950), "is_ready": True},
        {"slot_index": 1, "center": (250, 950), "is_ready": True}
    ]
    deployed_operators = {"克洛丝": (6, 0)}

    res = daemon.execute_multi_tier_emergency(
        leak_info=leak_info,
        cards=cards,
        deployed_operators=deployed_operators,
        mapper=mapper,
        humanizer=humanizer,
        adb_client=adb
    )

    assert res["status"] == "INTERCEPTED"
    assert res["tier"] == EmergencyTier.TIER_1_DROP.value
    assert (9, 2) in daemon.active_blockers
    assert adb.deploy_operator_gesture.called


def test_tier_2_burst_mode_escalation_when_no_cards(panic_setup):
    daemon, mapper, humanizer, adb = panic_setup
    leak_info = {
        "enemy_pos": (9.0, 1.2),
        "intercept_tile": (9, 2),
        "facing": "right"
    }
    # No ready cards in hand!
    cards = [
        {"slot_index": 0, "center": (100, 950), "is_ready": False}
    ]
    deployed_operators = {
        "克洛丝": (6, 0),
        "芬": (9, 2)
    }

    res = daemon.execute_multi_tier_emergency(
        leak_info=leak_info,
        cards=cards,
        deployed_operators=deployed_operators,
        mapper=mapper,
        humanizer=humanizer,
        adb_client=adb
    )

    assert res["status"] == "BURST_TRIGGERED"
    assert res["tier"] == EmergencyTier.TIER_2_BURST.value
    assert res["skills_triggered"] == 2
    assert res["fallback_reason"] == "NO_EMERGENCY_RESERVES"
    # ADB tap should have been called twice per operator (tap op + tap skill)
    assert adb.tap.call_count == 4


def test_tier_2_burst_mode_escalation_on_cooldown(panic_setup):
    daemon, mapper, humanizer, adb = panic_setup
    leak_info = {
        "enemy_pos": (9.0, 1.2),
        "intercept_tile": (9, 2),
        "facing": "right"
    }
    # Tile (9, 2) is already on cooldown
    daemon.intercept_cooldowns[(9, 2)] = time.time()

    cards = [
        {"slot_index": 0, "center": (100, 950), "is_ready": True}
    ]
    deployed_operators = {"棘刺": (4, 2)}

    res = daemon.execute_multi_tier_emergency(
        leak_info=leak_info,
        cards=cards,
        deployed_operators=deployed_operators,
        mapper=mapper,
        humanizer=humanizer,
        adb_client=adb
    )

    assert res["status"] == "BURST_TRIGGERED"
    assert res["tier"] == EmergencyTier.TIER_2_BURST.value
    assert res["skills_triggered"] == 1
    assert res["fallback_reason"] == "COOLDOWN_SUPPRESSED"
