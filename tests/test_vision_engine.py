# -*- coding: utf-8 -*-
"""
Unit tests for VisionEngine
Author: Emiliamio <mio2110767128@163.com>
"""

import pytest
import numpy as np
import cv2
from core.vision_engine import VisionEngine, BattleState


@pytest.fixture
def vision():
    return VisionEngine()


def test_roi_cropping(vision):
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    cost_crop = vision.get_roi_crop(frame, "cost")
    assert cost_crop.shape[0] > 0 and cost_crop.shape[1] > 0

    kill_crop = vision.get_roi_crop(frame, "kill_count")
    assert kill_crop.shape[0] > 0 and kill_crop.shape[1] > 0


def test_read_cost_ocr(vision):
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    h, w = 1080, 1920
    nx1, ny1, nx2, ny2 = vision.ROI_NORMS["cost"]
    cx1, cy1 = int(nx1 * w), int(ny1 * h)
    cv2.putText(frame, "18", (cx1 + 10, cy1 + 55), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)

    cost = vision.read_cost(frame)
    assert cost == 18, f"Expected cost 18, got {cost}"


def test_read_cost_ocr_kerning_split(vision):
    # Simulate wide kerning space between digits: "2 5"
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    h, w = 1080, 1920
    nx1, ny1, nx2, ny2 = vision.ROI_NORMS["cost"]
    cx1, cy1 = int(nx1 * w), int(ny1 * h)
    cv2.putText(frame, "2  5", (cx1 + 10, cy1 + 55), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)

    cost = vision.read_cost(frame)
    assert cost == 25, f"Expected cost 25 despite kerning split, got {cost}"


def test_read_kill_count_ocr(vision):
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    h, w = 1080, 1920
    nx1, ny1, nx2, ny2 = vision.ROI_NORMS["kill_count"]
    kx1, ky1 = int(nx1 * w), int(ny1 * h)
    cv2.putText(frame, "15/35", (kx1 + 5, ky1 + 40), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2)

    kills, total = vision.read_kill_count(frame)
    assert kills == 15 and total == 35, f"Expected (15, 35), got ({kills}, {total})"


def test_is_2x_speed_active(vision):
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    # Default dark frame
    assert not vision.is_2x_speed_active(frame)

    # Light up 2x speed button ROI
    h, w = 1080, 1920
    nx1, ny1, nx2, ny2 = vision.ROI_NORMS["speed_toggle"]
    x1, y1 = int(nx1 * w), int(ny1 * h)
    x2, y2 = int(nx2 * w), int(ny2 * h)
    frame[y1:y2, x1:x2] = (180, 180, 180)  # Bright icon
    assert vision.is_2x_speed_active(frame)


def test_detect_battle_state_pre_battle(vision):
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    frame[950:1060, 1600:1900] = (20, 20, 220)

    state = vision.detect_battle_state(frame)
    assert state == BattleState.PRE_BATTLE


def test_detect_battle_state_victory(vision):
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    cv2.putText(frame, "MISSION ACCOMPLISHED", (600, 540), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (255, 255, 255), 3)

    state = vision.detect_battle_state(frame)
    assert state == BattleState.VICTORY


def test_detect_deployable_cards(vision):
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    h, w = 1080, 1920
    nx1, ny1, nx2, ny2 = vision.ROI_NORMS["hand_cards"]
    x1, y1 = int(nx1 * w), int(ny1 * h)
    x2, y2 = int(nx2 * w), int(ny2 * h)

    slot_w = (x2 - x1) // 8
    frame[y1:y2, x1:x1 + slot_w] = (50, 180, 240)
    frame[y1:y2, x1 + slot_w:x1 + 2 * slot_w] = (30, 30, 30)

    cards = vision.detect_deployable_cards(frame, num_slots=8)
    assert len(cards) == 8
    assert cards[0]["is_ready"] is True
    assert cards[1]["is_ready"] is False