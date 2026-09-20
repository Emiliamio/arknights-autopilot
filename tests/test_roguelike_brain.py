# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Unit Tests for RoguelikeBrain (Heuristic Pathfinding & Theme Support)
Author: Emiliamio <mio2110767128@163.com>
"""

import pytest
from tactical.roguelike_brain import (
    RoguelikeBrain, RoguelikeTheme, RoguelikeNodeType, RoguelikeState
)


class MockADBClient:
    def __init__(self):
        self.device_serial = "127.0.0.1:16384"

    def tap(self, x, y):
        return {"status": "OK"}


class MockPilot:
    def run_combat(self, max_duration_sec=180):
        return {"result": "VICTORY", "elapsed_sec": 45.0}


def test_roguelike_brain_heuristic_evaluation_low_life():
    brain = RoguelikeBrain(adb_client=MockADBClient(), combat_pilot=MockPilot(), theme=RoguelikeTheme.IS4_SAMI)
    state = RoguelikeState(theme=RoguelikeTheme.IS4_SAMI)

    # When life points is critically low (<=3), EMERGENCY should be strongly avoided
    state.life_points = 2
    candidates = [
        {"type": RoguelikeNodeType.EMERGENCY, "pos": (900, 300)},
        {"type": RoguelikeNodeType.SAFEHOUSE, "pos": (900, 700)}
    ]
    best = brain.evaluate_best_node(candidates, state)
    assert best["type"] == RoguelikeNodeType.SAFEHOUSE


def test_roguelike_brain_heuristic_evaluation_rich_ingots():
    brain = RoguelikeBrain(adb_client=MockADBClient(), combat_pilot=MockPilot(), theme=RoguelikeTheme.IS3_MIZUKI)
    state = RoguelikeState(theme=RoguelikeTheme.IS3_MIZUKI)

    # When rich in ingots (>=16), TRADER is heavily prioritized
    state.ingots = 20
    state.life_points = 8
    candidates = [
        {"type": RoguelikeNodeType.COMBAT, "pos": (900, 300)},
        {"type": RoguelikeNodeType.TRADER, "pos": (900, 500)}
    ]
    best = brain.evaluate_best_node(candidates, state)
    assert best["type"] == RoguelikeNodeType.TRADER


def test_roguelike_brain_mock_expedition_run(monkeypatch):
    from core.abort_controller import AbortController
    AbortController.reset()
    import time
    monkeypatch.setattr(time, "sleep", lambda s: None)
    brain = RoguelikeBrain(adb_client=MockADBClient(), combat_pilot=MockPilot(), theme=RoguelikeTheme.IS4_SAMI)
    res = brain.run_roguelike_exploration(max_floors=2)

    assert res["status"] == "COMPLETED"
    assert res["theme"] == "IS4"
    assert res["final_floor"] >= 2
    assert "萨米" in res["summary"] or "IS4" in res["summary"]
