# -*- coding: utf-8 -*-
"""
Unit tests for CopilotBrain Dual-Track Execution & Panic Preemption
Author: Emiliamio <mio2110767128@163.com>
"""

import pytest
import numpy as np
import cv2

from tactical.map_deconstructor import TacticalMap
from tactical.copilot_adapter import CopilotAdapter
from tactical.copilot_brain import CopilotBrain
from core.homography_mapper import HomographyMapper
from core.vision_engine import VisionEngine, BattleState
from core.touch_humanizer import TouchHumanizer


@pytest.fixture
def copilot_env():
    t_map = TacticalMap.create_1_7()
    plan = CopilotAdapter.load_file("data/copilots/1-7_xiaoran_duo.json")
    brain = CopilotBrain(t_map, plan)
    mapper = HomographyMapper.create_synthetic_arknights_mapper()
    humanizer = TouchHumanizer()
    vision = VisionEngine()
    return t_map, plan, brain, mapper, humanizer, vision


def test_copilot_sequential_actions(copilot_env):
    t_map, plan, brain, mapper, humanizer, vision = copilot_env

    # Frame with 2x speed active, DP=10, 0 kills, ready cards in hand
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    h, w = 1080, 1920
    # Speed icon bright
    sx1, sy1 = int(vision.ROI_NORMS["speed_toggle"][0] * w), int(vision.ROI_NORMS["speed_toggle"][1] * h)
    frame[sy1:sy1 + 40, sx1:sx1 + 40] = 150
    # Cost 10
    cx1, cy1 = int(vision.ROI_NORMS["cost"][0] * w), int(vision.ROI_NORMS["cost"][1] * h)
    cv2.putText(frame, "10", (cx1 + 10, cy1 + 55), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)
    frame[20:70, 1820:1880] = 100
    # Hand card ready
    hx1, hy1 = int(vision.ROI_NORMS["hand_cards"][0] * w), int(vision.ROI_NORMS["hand_cards"][1] * h)
    frame[hy1:hy1 + 80, hx1:hx1 + 100] = (60, 180, 240)

    # Tick 1: Action 1 is SPEED_UP
    t1 = brain.tick(frame, vision, mapper, humanizer, adb_client=None)
    assert t1["action_taken"] == "SPEED_UP_CONFIRMED"
    assert brain.current_action_idx == 1

    # Tick 2: Action 2 is DEPLOY 芬 at [9, 2] (DP=10 satisfied)
    t2 = brain.tick(frame, vision, mapper, humanizer, adb_client=None)
    assert t2["action_taken"] == "COPILOT_DEPLOY_芬"
    assert brain.current_action_idx == 2
    assert (9, 2) in brain.panic_daemon.active_blockers


def test_copilot_panic_preemption_and_recovery(copilot_env):
    t_map, plan, brain, mapper, humanizer, vision = copilot_env

    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    h, w = 1080, 1920
    sx1, sy1 = int(vision.ROI_NORMS["speed_toggle"][0] * w), int(vision.ROI_NORMS["speed_toggle"][1] * h)
    frame[sy1:sy1 + 40, sx1:sx1 + 40] = 150
    cx1, cy1 = int(vision.ROI_NORMS["cost"][0] * w), int(vision.ROI_NORMS["cost"][1] * h)
    cv2.putText(frame, "10", (cx1 + 10, cy1 + 55), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)
    frame[20:70, 1820:1880] = 100
    hx1, hy1 = int(vision.ROI_NORMS["hand_cards"][0] * w), int(vision.ROI_NORMS["hand_cards"][1] * h)
    frame[hy1:hy1 + 80, hx1:hx1 + 100] = (60, 180, 240)

    # Tick 1: Advance past SpeedUp
    brain.tick(frame, vision, mapper, humanizer, adb_client=None)
    assert brain.current_action_idx == 1  # Next is Deploy 芬

    # SIMULATE SUDDEN LEAK: An unexpected enemy appears at (col=9, row=1) without blocker!
    ex, ey = mapper.get_tile_center(9, 1)
    cv2.circle(frame, (ex, ey), 12, (20, 20, 220), -1)

    # Tick 2: PANIC SENTRY PREEMPTS COPILOT!
    t2 = brain.tick(frame, vision, mapper, humanizer, adb_client=None)
    assert t2["action_taken"] == "PANIC_INTERCEPT_PREEMPTION", "Panic Sentry must overrule copilot on breach!"
    assert brain.emergency_interventions_count == 1
    assert t2["status"] == "EMERGENCY_INTERVENING"
    # Interceptor placed at (9, 2)
    assert (9, 2) in brain.panic_daemon.active_blockers

    # Tick 3: Breach is now intercepted! Remove red leak blob, copilot resumes!
    frame[ey - 20:ey + 20, ex - 20:ex + 20] = 0  # clear enemy
    t3 = brain.tick(frame, vision, mapper, humanizer, adb_client=None)
    assert t3["action_taken"] == "COPILOT_DEPLOY_芬"
    assert brain.current_action_idx == 2
def test_copilot_omitted_location_auto_resolved(copilot_env):
    t_map, plan, brain, mapper, humanizer, vision = copilot_env
    brain.deployed_operators["克洛丝"] = (6, 0)

    # Action has location [0, 0]
    skill_action = plan.actions[3]  # Skill 克洛丝
    assert skill_action.col == 0 and skill_action.row == 0

    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    h, w = 1080, 1920
    sx1, sy1 = int(vision.ROI_NORMS["speed_toggle"][0] * w), int(vision.ROI_NORMS["speed_toggle"][1] * h)
    frame[sy1:sy1 + 40, sx1:sx1 + 40] = 150
    cx1, cy1 = int(vision.ROI_NORMS["cost"][0] * w), int(vision.ROI_NORMS["cost"][1] * h)
    cv2.putText(frame, "20", (cx1 + 10, cy1 + 55), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)
    frame[20:70, 1820:1880] = 100

    # Advance current action to Action 3 (Skill)
    brain.current_action_idx = 3
    brain.kill_count = (10, 35)

    res = brain.tick(frame, vision, mapper, humanizer, adb_client=None)
    assert res["action_taken"] == "COPILOT_SKILL_克洛丝"
    assert skill_action.status == "EXECUTED"
