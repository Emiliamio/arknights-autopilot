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


def test_recruitment_drafter_high_hope_prefers_s_tier():
    """Verify that when Hope budget is abundant (>=6), drafter selects top S-tier 6-star core."""
    from tactical.roguelike_brain import OperatorRecruitmentDrafter

    current_roster = [{"name": "克洛丝", "class": "SNIPER"}]
    ranked = OperatorRecruitmentDrafter.rank_candidates_for_voucher(
        voucher_type="近卫",
        current_hope=8,
        current_roster=current_roster
    )

    assert len(ranked) > 0
    top = ranked[0]
    assert top["tier"] == "S"
    assert top["hope_cost"] == 6
    assert top["name"] in ("玛恩纳", "史尔特尔")
    assert "肉鸽S级核心" in top["reasons"]


def test_recruitment_drafter_low_hope_zero_cost_fallback():
    """Verify that when Hope is scarce (<2), drafter reliably falls back to affordable 0-hope 3-star anchor."""
    from tactical.roguelike_brain import OperatorRecruitmentDrafter

    current_roster = [{"name": "德克萨斯", "class": "VANGUARD"}]
    # Hope is only 1 point: cannot afford 6★ (6), 5★ (3), 4★ (2)
    ranked = OperatorRecruitmentDrafter.rank_candidates_for_voucher(
        voucher_type="重装",
        current_hope=1,
        current_roster=current_roster
    )

    assert len(ranked) > 0
    top = ranked[0]
    # Should choose Spot (斑点, 3★, 0 Hope) or Beagle (米戈)
    assert top["hope_cost"] == 0
    assert top["name"] == "斑点"
    assert "0希望极高性价比" in top["reasons"]


def test_recruitment_drafter_squad_deficit_weighting():
    """Verify that severe team deficits (0 healers) heavily amplify role urgency for medics."""
    from tactical.roguelike_brain import OperatorRecruitmentDrafter

    # Team has zero healers
    roster_without_medic = [
        {"name": "银灰", "class": "GUARD"},
        {"name": "星熊", "class": "DEFENDER"}
    ]
    deficits = OperatorRecruitmentDrafter.evaluate_squad_deficits(roster_without_medic)
    assert deficits["medics"] == 0

    ranked = OperatorRecruitmentDrafter.rank_candidates_for_voucher(
        voucher_type="医疗",
        current_hope=6,
        current_roster=roster_without_medic
    )

    assert len(ranked) > 0
    top = ranked[0]
    assert "补齐阵容关键短板" in top["reasons"]


def test_theme_is3_mizuki_low_light_penalty():
    """Verify that in IS3 (Mizuki), low light (<50) severely penalizes EMERGENCY nodes and picks SAFEHOUSE."""
    brain = RoguelikeBrain(adb_client=MockADBClient(), combat_pilot=MockPilot(), theme=RoguelikeTheme.IS3_MIZUKI)
    state = RoguelikeState(theme=RoguelikeTheme.IS3_MIZUKI)
    state.life_points = 7
    state.light_value = 35  # Night danger state

    candidates = [
        {"type": RoguelikeNodeType.EMERGENCY, "pos": (900, 300)},
        {"type": RoguelikeNodeType.SAFEHOUSE, "pos": (900, 700)}
    ]
    best = brain.evaluate_best_node(candidates, state)
    assert best["type"] == RoguelikeNodeType.SAFEHOUSE


def test_theme_is4_sami_collapse_mitigation():
    """Verify that in IS4 (Sami), high collapse (>=3) triggers emergency purification at SAFEHOUSE."""
    brain = RoguelikeBrain(adb_client=MockADBClient(), combat_pilot=MockPilot(), theme=RoguelikeTheme.IS4_SAMI)
    state = RoguelikeState(theme=RoguelikeTheme.IS4_SAMI)
    state.collapse_level = 4  # High collapse hazard

    candidates = [
        {"type": RoguelikeNodeType.COMBAT, "pos": (900, 300)},
        {"type": RoguelikeNodeType.SAFEHOUSE, "pos": (900, 700)}
    ]
    best = brain.evaluate_best_node(candidates, state)
    assert best["type"] == RoguelikeNodeType.SAFEHOUSE


def test_brain_recruit_operator_lifecycle():
    """Verify that RoguelikeBrain.recruit_operator_with_voucher executes full hope deduction and roster update."""
    brain = RoguelikeBrain(adb_client=MockADBClient(), combat_pilot=MockPilot(), theme=RoguelikeTheme.IS4_SAMI)
    brain.state.hope = 6
    initial_roster_len = len(brain.state.roster)

    recruited = brain.recruit_operator_with_voucher("狙击")
    assert recruited is not None
    assert brain.state.hope == 6 - recruited["hope_cost"]
    assert len(brain.state.roster) == initial_roster_len + 1
    assert any(op["name"] == recruited["name"] for op in brain.state.roster)

