# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Unit Tests for Global Navigator & Campaign Cruiser Node Matcher
Author: Emiliamio <mio2110767128@163.com>
"""

import numpy as np
import pytest
from tactical.global_navigator import GlobalNavigator, SceneType
from tactical.campaign_cruiser import CampaignCruiser


class MockVisionEngine:
    def __init__(self, mock_text=""):
        self.mock_text = mock_text

    def ocr(self, frame):
        if not self.mock_text:
            return [], None
        words = self.mock_text.split()
        res = []
        for i, word in enumerate(words):
            box = [[100 + i*60, 100], [150 + i*60, 100], [150 + i*60, 140], [100 + i*60, 140]]
            res.append([box, (word, 0.99)])
        return res, None

    def detect_battle_state(self, frame):
        from core.vision_engine import BattleState
        return BattleState.PRE_BATTLE


def test_detect_scene_home():
    mock_vision = MockVisionEngine(mock_text="终端 作战 基建 干员")
    navigator = GlobalNavigator(adb_client=None, vision_engine=mock_vision)

    dummy_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    scene = navigator.detect_scene(dummy_frame)
    assert scene == SceneType.HOME


def test_detect_scene_terminal():
    mock_vision = MockVisionEngine(mock_text="主题曲 资源收集 别传")
    navigator = GlobalNavigator(adb_client=None, vision_engine=mock_vision)

    dummy_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    scene = navigator.detect_scene(dummy_frame)
    assert scene == SceneType.TERMINAL


def test_detect_scene_settlement():
    mock_vision = MockVisionEngine(mock_text="MISSION ACCOMPLISHED 行动结束 CLEAR")
    navigator = GlobalNavigator(adb_client=None, vision_engine=mock_vision)

    dummy_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    scene = navigator.detect_scene(dummy_frame)
    assert scene == SceneType.SETTLEMENT


def test_campaign_cruiser_stage_node_matching():
    mock_vision = MockVisionEngine(mock_text="0-1 0-2 0-3 0-4")
    cruiser = CampaignCruiser(adb_client=None, vision_engine=mock_vision)

    dummy_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    cleared = ["0-1", "0-2"]
    target = cruiser._find_next_stage_node(dummy_frame, chapter=0, cleared_stages=cleared)

    assert target is not None
    code, (cx, cy) = target
    assert code == "0-3"

def test_detect_current_chapter():
    mock_vision_17 = MockVisionEngine(mock_text="OPERATION 17-1 17-2 EPISODE 17")
    nav = GlobalNavigator(adb_client=None, vision_engine=mock_vision_17)
    dummy = np.zeros((1080, 1920, 3), dtype=np.uint8)
    assert nav.detect_current_chapter(dummy) == 17

    mock_vision_0 = MockVisionEngine(mock_text="OPERATION 0-1 0-2 EPISODE 00")
    nav0 = GlobalNavigator(adb_client=None, vision_engine=mock_vision_0)
    assert nav0.detect_current_chapter(dummy) == 0
