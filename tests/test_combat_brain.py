# -*- coding: utf-8 -*-
"""
Unit tests for CombatBrain HFSM & Deployment Priority Queue
Author: Emiliamio <mio2110767128@163.com>
"""

import pytest
import numpy as np
import cv2
from tactical.map_deconstructor import TacticalMap
from tactical.choke_point_analyzer import ChokePointAnalyzer, HighGroundScorer
from tactical.combat_brain import CombatBrain, BrainState
from core.homography_mapper import HomographyMapper
from core.vision_engine import VisionEngine, BattleState
from core.touch_humanizer import TouchHumanizer


@pytest.fixture
def prepared_brain():
    t_map = TacticalMap.create_1_7()
    analyzer = ChokePointAnalyzer(t_map)
    choke_res = analyzer.analyze_choke_points()

    scorer = HighGroundScorer(t_map)
    hg_ranks = scorer.score_high_grounds(choke_res)
    med_ranks = scorer.score_medic_positions(choke_res)

    brain = CombatBrain(
        tactical_map=t_map,
        choke_analysis=choke_res,
        high_ground_ranks=hg_ranks,
        medic_ranks=med_ranks
    )
    return brain


def test_deployment_plan_generation(prepared_brain):
    plan = prepared_brain.plan
    assert len(plan) >= 3, "Plan must contain at least Vanguard, Sniper, Medic"

    assert plan[0].role == "VANGUARD"
    assert plan[0].min_dp == 10
    assert hasattr(plan[0], "col") and hasattr(plan[0], "row")

    assert plan[1].role == "SNIPER"
    assert plan[1].min_dp == 12

    assert plan[2].role == "MEDIC"
    assert plan[2].min_dp == 16


def test_combat_brain_tick_dp_gate(prepared_brain):
    mapper = HomographyMapper.create_synthetic_arknights_mapper()
    humanizer = TouchHumanizer()
    vision = VisionEngine()

    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    h, w = 1080, 1920
    nx1, ny1, nx2, ny2 = vision.ROI_NORMS["cost"]
    cx1, cy1 = int(nx1 * w), int(ny1 * h)
    cv2.putText(frame, "5", (cx1 + 10, cy1 + 55), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)
    frame[20:70, 1820:1880] = 100

    # Ensure 2x speed icon is active so test focuses on DP gate
    sx1, sy1 = int(vision.ROI_NORMS["speed_toggle"][0] * w), int(vision.ROI_NORMS["speed_toggle"][1] * h)
    frame[sy1:sy1 + 40, sx1:sx1 + 40] = 150

    hx1, hy1 = int(vision.ROI_NORMS["hand_cards"][0] * w), int(vision.ROI_NORMS["hand_cards"][1] * h)
    frame[hy1:hy1 + 80, hx1:hx1 + 100] = (60, 180, 240)

    # Tick 1: DP is 5, cannot deploy Vanguard
    res = prepared_brain.tick(frame, vision, mapper, humanizer, adb_client=None)
    assert res["action_taken"] == "NONE"
    assert prepared_brain.current_step_idx == 0

    # Tick 2: Update frame with DP=10
    frame[hy1:hy1 + 80, :] = 0
    frame[hy1:hy1 + 80, hx1:hx1 + 100] = (60, 180, 240)
    frame[cy1:cy1 + 80, cx1:cx1 + 100] = 0
    cv2.putText(frame, "10", (cx1 + 10, cy1 + 55), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)

    res2 = prepared_brain.tick(frame, vision, mapper, humanizer, adb_client=None)
    assert res2["action_taken"] == "DEPLOY_VANGUARD"
    assert prepared_brain.current_step_idx == 1
    assert prepared_brain.plan[0].status == "DEPLOYED"


def test_combat_brain_2x_speed_auto_toggle(prepared_brain):
    mapper = HomographyMapper.create_synthetic_arknights_mapper()
    humanizer = TouchHumanizer()
    vision = VisionEngine()

    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    h, w = 1080, 1920
    nx1, ny1, nx2, ny2 = vision.ROI_NORMS["cost"]
    cx1, cy1 = int(nx1 * w), int(ny1 * h)
    cv2.putText(frame, "10", (cx1 + 10, cy1 + 55), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)
    frame[20:70, 1820:1880] = 100

    # Speed button is dark (1x speed)
    assert not prepared_brain.speed_2x_ensured
    res = prepared_brain.tick(frame, vision, mapper, humanizer, adb_client=None)
    assert res["action_taken"] == "TOGGLE_2X_SPEED"
    assert prepared_brain.speed_2x_ensured is True


def test_combat_brain_victory_settlement(prepared_brain):
    mapper = HomographyMapper.create_synthetic_arknights_mapper()
    humanizer = TouchHumanizer()
    vision = VisionEngine()

    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    cv2.putText(frame, "MISSION ACCOMPLISHED", (600, 540), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (255, 255, 255), 3)

    res = prepared_brain.tick(frame, vision, mapper, humanizer, adb_client=None)
    assert res["action_taken"] == "SETTLE_VICTORY"
    assert prepared_brain.state == BrainState.COMPLETED