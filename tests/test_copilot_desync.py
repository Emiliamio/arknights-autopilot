# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Unit tests for CopilotBrain Desync Deadlock Breaker & Soft Conditions
Author: Emiliamio <mio2110767128@163.com>
"""

import pytest
import time
import numpy as np

from tactical.map_deconstructor import TacticalMap
from tactical.copilot_adapter import CopilotAdapter, CopilotAction, CopilotActionType
from tactical.copilot_brain import CopilotBrain
from tactical.threat_monitor import ThreatLevel
from core.homography_mapper import HomographyMapper
from core.vision_engine import VisionEngine
from core.touch_humanizer import TouchHumanizer


@pytest.fixture
def base_copilot():
    t_map = TacticalMap.create_1_7()
    plan = CopilotAdapter.load_file("data/copilots/1-7_universal_farm.json")
    brain = CopilotBrain(t_map, plan)
    mapper = HomographyMapper.create_synthetic_arknights_mapper()
    humanizer = TouchHumanizer()
    vision = VisionEngine()
    return brain, plan, mapper, humanizer, vision


def test_evaluate_action_readiness_normal(base_copilot):
    brain, plan, _, _, _ = base_copilot
    action = CopilotAction(
        step_index=1,
        action_type=CopilotActionType.DEPLOY,
        name="芬",
        min_costs=10,
        min_kills=5
    )

    # 1. Normal satisfied
    is_ready, reason = brain.evaluate_action_readiness(
        action=action, current_dp=15, kills=6, threat_lvl=ThreatLevel.SAFE, elapsed_sec=2.0
    )
    assert is_ready is True
    assert reason == "NORMAL"


def test_evaluate_action_readiness_waiting_dp(base_copilot):
    brain, plan, _, _, _ = base_copilot
    action = CopilotAction(
        step_index=1,
        action_type=CopilotActionType.DEPLOY,
        name="芬",
        min_costs=10,
        min_kills=5
    )

    # Not enough DP even if kills satisfied
    is_ready, reason = brain.evaluate_action_readiness(
        action=action, current_dp=8, kills=10, threat_lvl=ThreatLevel.SAFE, elapsed_sec=3.0
    )
    assert is_ready is False
    assert reason == "WAITING_DP"


def test_evaluate_action_readiness_soft_dp_surplus(base_copilot):
    brain, plan, _, _, _ = base_copilot
    action = CopilotAction(
        step_index=1,
        action_type=CopilotActionType.DEPLOY,
        name="斑点",
        min_costs=16,
        min_kills=12
    )

    # Kills not reached (only 10 kills), but DP is high (30 >= 16 + 12) and elapsed >= 8.0s
    is_ready, reason = brain.evaluate_action_readiness(
        action=action, current_dp=30, kills=10, threat_lvl=ThreatLevel.SAFE, elapsed_sec=8.5
    )
    assert is_ready is True
    assert reason == "SOFT_DP_SURPLUS"

    # If elapsed < 8.0s, should wait
    is_ready_early, reason_early = brain.evaluate_action_readiness(
        action=action, current_dp=30, kills=10, threat_lvl=ThreatLevel.SAFE, elapsed_sec=4.0
    )
    assert is_ready_early is False
    assert reason_early == "WAITING_KILLS"


def test_evaluate_action_readiness_threat_urgency(base_copilot):
    brain, plan, _, _, _ = base_copilot
    action = CopilotAction(
        step_index=1,
        action_type=CopilotActionType.DEPLOY,
        name="克洛丝",
        min_costs=12,
        min_kills=8
    )

    # Kills not reached (kills=3), but map threat is ALERT
    is_ready, reason = brain.evaluate_action_readiness(
        action=action, current_dp=12, kills=3, threat_lvl=ThreatLevel.ALERT, elapsed_sec=1.5
    )
    assert is_ready is True
    assert reason == "THREAT_URGENCY"

    # Same for PANIC_LEAK
    is_ready_crit, reason_crit = brain.evaluate_action_readiness(
        action=action, current_dp=12, kills=3, threat_lvl=ThreatLevel.PANIC_LEAK, elapsed_sec=1.5
    )
    assert is_ready_crit is True
    assert reason_crit == "THREAT_URGENCY"


def test_copilot_watchdog_timeout_bypass(base_copilot):
    brain, plan, mapper, humanizer, vision = base_copilot
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)

    # Fast forward past SpeedUp
    brain.current_action_idx = 1
    # Action 1 is Deploy 芬 (min_costs=10). We artificially freeze DP at 0 and time by 26s
    brain.last_dp = 0
    brain.action_start_time = time.time() - 26.0

    res = brain.tick(frame, vision, mapper, humanizer, adb_client=None)
    assert res["action_taken"] == "WATCHDOG_BYPASS"
    assert brain.current_action_idx == 2  # Bypassed to next action


def test_copilot_roster_substitution_in_brain():
    t_map = TacticalMap.create_1_7()
    plan = CopilotAdapter.load_file("data/copilots/1-7_universal_farm.json")

    # User roster lacks 芬, has 讯使
    owned = ["讯使", "克洛丝", "斑点", "炎熔", "砾"]
    brain = CopilotBrain(t_map, plan, owned_roster=owned)

    assert "芬" in brain.substitutions
    assert brain.substitutions["芬"] == "讯使"

    # Check adapted plan actions
    deploy_action = brain.plan.actions[1]
    assert deploy_action.name == "讯使"
