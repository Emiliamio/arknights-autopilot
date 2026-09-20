# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Unit tests for Copilot Plans Integrity and Fuzzy Adaptation
Author: Emiliamio <mio2110767128@163.com>
"""

import glob
import os
import pytest

from tactical.copilot_adapter import CopilotAdapter, CopilotActionType
from tactical.copilot_fuzzy_matcher import CopilotFuzzyMatcher


def get_all_copilot_files():
    pattern = os.path.join("data", "copilots", "*.json")
    files = glob.glob(pattern)
    assert len(files) >= 4, f"Expected at least 4 copilot plans, found {len(files)}"
    return files


@pytest.mark.parametrize("filepath", get_all_copilot_files())
def test_copilot_plan_parsing_integrity(filepath):
    plan = CopilotAdapter.load_file(filepath)

    assert plan.stage_name, f"{filepath}: missing stage_name"
    assert len(plan.opers) > 0, f"{filepath}: opers list should not be empty"
    assert len(plan.actions) > 0, f"{filepath}: actions list should not be empty"

    # Verify each operator has a valid name
    for op in plan.opers:
        assert "name" in op and op["name"], f"{filepath}: operator missing valid name"

    # Verify each action has a valid type and step_index
    for idx, act in enumerate(plan.actions):
        assert act.step_index == idx + 1
        assert isinstance(act.action_type, CopilotActionType)

        if act.action_type == CopilotActionType.DEPLOY:
            assert act.name, f"{filepath}: deploy action must have operator name"
            assert len(act.direction) > 0


def test_copilot_fuzzy_matcher_on_all_plans():
    matcher = CopilotFuzzyMatcher()
    files = get_all_copilot_files()

    # User roster lacking high-star ops, using low-star budget replacements
    budget_roster = [
        "芬", "讯使", "克洛丝", "斑点", "米格鲁", "炎熔", "玫兰莎", "砾", "夜刀"
    ]

    for filepath in files:
        plan = CopilotAdapter.load_file(filepath)
        adapted_plan, substitutions = matcher.adapt_plan(plan, budget_roster)

        assert adapted_plan is not None
        assert len(adapted_plan.actions) == len(plan.actions)

        # For any operator in adapted_plan not in original, it should be in substitutions
        for op in adapted_plan.opers:
            assert op["name"] in budget_roster or any(orig["name"] == op["name"] for orig in plan.opers)
