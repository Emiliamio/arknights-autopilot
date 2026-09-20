# -*- coding: utf-8 -*-
"""
Unit tests for UniversalCombatPilot end-to-end combat loop
Author: Emiliamio <mio2110767128@163.com>
"""

import pytest
import time
import numpy as np
from unittest.mock import MagicMock, patch

from core.abort_controller import AbortController
from core.vision_engine import BattleState
from tactical.threat_monitor import ThreatLevel
from tactical.universal_combat_pilot import UniversalCombatPilot


@pytest.fixture
def mock_pilot():
    client = MagicMock()
    vision = MagicMock()
    humanizer = MagicMock()
    mapper = MagicMock()
    threat_monitor = MagicMock()

    # Default dummy frame
    dummy_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    client.screencap.return_value = dummy_frame
    mapper.get_tile_center.return_value = (640, 360)
    humanizer.generate_deploy_gesture.return_value = {
        "drag_trajectory": [(300, 600), (640, 360)],
        "flick_trajectory": [(640, 360), (700, 360)],
        "pause_before_flick_ms": 100
    }

    pilot = UniversalCombatPilot(
        adb_client=client,
        vision_engine=vision,
        humanizer=humanizer,
        mapper=mapper,
        threat_monitor=threat_monitor
    )
    return pilot


def test_pilot_initialization(mock_pilot):
    assert mock_pilot.client is not None
    assert mock_pilot.vision is not None
    assert mock_pilot.humanizer is not None
    assert mock_pilot.mapper is not None
    assert len(mock_pilot.deployed_operators) == 0
    assert mock_pilot.skills_triggered_count == 0


def test_ensure_speed_2x(mock_pilot):
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    # 1. When 2x speed is NOT active, should tap speed toggle
    mock_pilot.vision.is_2x_speed_active.return_value = False
    res = mock_pilot.ensure_speed_2x(frame)
    assert res is True
    mock_pilot.client.tap.assert_called_with(1645, 69)

    # 2. When 2x speed is already active, should not tap
    mock_pilot.client.tap.reset_mock()
    mock_pilot.vision.is_2x_speed_active.return_value = True
    res2 = mock_pilot.ensure_speed_2x(frame)
    assert res2 is False
    mock_pilot.client.tap.assert_not_called()


def test_deploy_step_with_target_and_tile(mock_pilot):
    ready_card = {"slot_index": 0, "center": (300, 650), "is_ready": True}

    # Test 1: Raw target deployment
    step1 = {"target": (800, 450), "orientation": "right", "min_dp": 10, "name": "Vanguard"}
    res1 = mock_pilot.deploy_step(step1, ready_card, current_dp=12)
    assert res1 is True
    assert len(mock_pilot.deployed_operators) == 1
    assert mock_pilot.deployed_operators[0]["name"] == "Vanguard"
    assert mock_pilot.deployed_operators[0]["pos"] == (800, 450)
    mock_pilot.client.deploy_operator_gesture.assert_called_once()

    # Test 2: Tile-based deployment
    mock_pilot.mapper.get_tile_center.return_value = (500, 300)
    step2 = {"tile": (4, 2), "orientation": "down", "min_dp": 14, "name": "Sniper"}
    res2 = mock_pilot.deploy_step(step2, ready_card, current_dp=15)
    assert res2 is True
    assert len(mock_pilot.deployed_operators) == 2
    assert mock_pilot.deployed_operators[1]["name"] == "Sniper"
    assert mock_pilot.deployed_operators[1]["pos"] == (500, 300)
    assert (4, 2) in mock_pilot.panic_daemon.active_blockers


def test_cycle_skills_and_burst(mock_pilot):
    # Register 2 deployed operators
    t0 = 1000.0
    mock_pilot.deployed_operators = [
        {"name": "Op1", "pos": (400, 300), "last_skill_attempt": t0 - 10.0, "auto_skill": True, "skill_cooldown": 6.0},
        {"name": "Op2", "pos": (600, 300), "last_skill_attempt": t0 - 2.0, "auto_skill": True, "skill_cooldown": 6.0},
        {"name": "Op3", "pos": (800, 300), "last_skill_attempt": t0 - 10.0, "auto_skill": False, "skill_cooldown": 6.0}
    ]

    # Cycle at t0: Op1 cooldown is met (10.0 >= 6.0), Op2 cooldown not met (2.0 < 6.0), Op3 auto_skill is False
    with patch("time.sleep"):
        triggered = mock_pilot.cycle_skills(current_time=t0)
    assert triggered == 1
    assert mock_pilot.skills_triggered_count == 1
    # Verify Op1 tapped at (400, 300) and skill icon at (400, 240)
    mock_pilot.client.tap.assert_any_call(400, 300)
    mock_pilot.client.tap.assert_any_call(400, 240)

    # Test Burst Mode: trigger_all_skills
    mock_pilot.client.tap.reset_mock()
    with patch("time.sleep"):
        burst_count = mock_pilot.trigger_all_skills()
    assert burst_count == 3
    assert mock_pilot.skills_triggered_count == 4


def test_settlement_dynamic_dismissal(mock_pilot):
    # Mock sequence of battle states during dismissal:
    # Attempt 1: Still VICTORY
    # Attempt 2: Still VICTORY
    # Attempt 3: Returned to UNKNOWN / Stage Lobby
    mock_pilot.vision.detect_battle_state.side_effect = [
        BattleState.VICTORY,
        BattleState.VICTORY,
        BattleState.UNKNOWN
    ]

    with patch("time.sleep"):
        res = mock_pilot.dismiss_settlement(max_taps=5, tap_interval=0.1)

    assert res is True
    # Verify tap was performed during dismissal attempts
    assert mock_pilot.client.tap.call_count >= 2


def test_enter_and_wait_battlefield(mock_pilot):
    # State transitions: PRE_BATTLE -> IN_BATTLE
    mock_pilot.vision.detect_battle_state.side_effect = [
        BattleState.PRE_BATTLE,
        BattleState.IN_BATTLE
    ]

    with patch("time.sleep"):
        entered = mock_pilot.enter_and_wait_battlefield(max_wait_sec=5)

    assert entered is True
    assert mock_pilot.client.tap.called


def test_run_combat_full_flow(mock_pilot):
    # Simulate a full flow:
    # Frame 0: IN_BATTLE
    # Frame 1: DP=15, deploy 1st operator
    # Frame 2: VICTORY
    mock_pilot.vision.detect_battle_state.side_effect = [
        BattleState.IN_BATTLE,
        BattleState.IN_BATTLE,
        BattleState.VICTORY,
        BattleState.UNKNOWN  # during dismissal
    ]
    mock_pilot.vision.is_2x_speed_active.return_value = True
    mock_pilot.vision.read_cost.return_value = 15
    mock_pilot.vision.detect_deployable_cards.return_value = [
        {"slot_index": 0, "center": (300, 650), "is_ready": True}
    ]
    mock_pilot.threat_monitor.detect_enemies.return_value = []
    mock_pilot.threat_monitor.evaluate_threat.return_value = (ThreatLevel.SAFE, None)

    with patch("time.sleep"):
        res = mock_pilot.run_combat(max_duration_sec=10, auto_handle_pre_battle=False)

    assert res["result"] == "VICTORY"
    assert res["deployed_count"] >= 1
    assert "elapsed_sec" in res


def test_run_combat_panic_leak(mock_pilot):
    # Simulate a panic leak triggering emergency intercept
    mock_pilot.vision.detect_battle_state.side_effect = [
        BattleState.IN_BATTLE,
        BattleState.VICTORY,
        BattleState.UNKNOWN
    ]
    mock_pilot.vision.is_2x_speed_active.return_value = True
    leak_info = {"enemy_pos": (8, 2), "distance_to_goal": 2, "intercept_tile": (9, 2), "facing": "left"}
    mock_pilot.threat_monitor.detect_enemies.return_value = [MagicMock()]
    mock_pilot.threat_monitor.evaluate_threat.return_value = (ThreatLevel.PANIC_LEAK, leak_info)
    mock_pilot.panic_daemon.execute_emergency_intercept = MagicMock(return_value={"status": "intercepted"})

    with patch("time.sleep"):
        res = mock_pilot.run_combat(max_duration_sec=10, auto_handle_pre_battle=False)

    assert res["result"] == "VICTORY"
    mock_pilot.panic_daemon.execute_emergency_intercept.assert_called_once()


def test_run_combat_abort_handling(mock_pilot):
    AbortController.reset()
    AbortController.trigger_abort("Test emergency abort")

    try:
        res = mock_pilot.run_combat(max_duration_sec=10, auto_handle_pre_battle=False)
        assert res["result"] == "ABORTED"
    finally:
        AbortController.reset()
