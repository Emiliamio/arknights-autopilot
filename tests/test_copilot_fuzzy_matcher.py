# -*- coding: utf-8 -*-
"""
Unit tests for CopilotFuzzyMatcher
Author: Emiliamio <mio2110767128@163.com>
"""

import pytest
from tactical.copilot_fuzzy_matcher import CopilotFuzzyMatcher
from tactical.copilot_adapter import CopilotPlan, CopilotAction, CopilotActionType


def test_exact_match_when_owned():
    matcher = CopilotFuzzyMatcher(owned_roster=["玛恩纳", "塞雷娅", "芬"])
    sub, delta, reason = matcher.match_substitute("玛恩纳")
    assert sub == "玛恩纳"
    assert delta == 0
    assert reason == "EXACT_MATCH"


def test_explicit_chain_guard_substitution():
    # Customer lacks 玛恩纳 (cost 12), but has 银灰 (cost 18)
    matcher = CopilotFuzzyMatcher(owned_roster=["银灰", "芬", "克洛丝"])
    sub, delta, reason = matcher.match_substitute("玛恩纳")
    assert sub == "银灰"
    assert delta == 6  # 18 - 12 = 6
    assert reason == "EXPLICIT_CHAIN"


def test_defender_healing_substitution():
    # Customer lacks 塞雷娅 (cost 18), but has 斑点 (cost 15)
    matcher = CopilotFuzzyMatcher(owned_roster=["斑点", "芬", "克洛丝"])
    sub, delta, reason = matcher.match_substitute("塞雷娅")
    assert sub == "斑点"
    assert delta == -3  # 15 - 18 = -3
    assert reason == "EXPLICIT_CHAIN"


def test_medic_substitution():
    # Customer lacks 纯烬艾雅法拉 (cost 17), but has 白面鸮 (cost 15)
    matcher = CopilotFuzzyMatcher(owned_roster=["白面鸮", "芬", "克洛丝"])
    sub, delta, reason = matcher.match_substitute("纯烬艾雅法拉")
    assert sub == "白面鸮"
    assert delta == -2
    assert reason == "EXPLICIT_CHAIN"


def test_heuristic_fallback_matching():
    # Unknown/custom guard in explicit chains -> falls back to heuristic matching
    matcher = CopilotFuzzyMatcher(owned_roster=["拉普兰德", "安塞尔"])
    # Suppose target is a generic guard not in explicit chain
    sub, delta, reason = matcher.match_substitute("神秘近卫")
    assert sub == "拉普兰德"


def test_adapt_copilot_plan_renaming_and_cost_offset():
    actions = [
        CopilotAction(step_index=1, action_type=CopilotActionType.DEPLOY, name="芬", col=9, row=2, min_costs=10),
        CopilotAction(step_index=2, action_type=CopilotActionType.DEPLOY, name="玛恩纳", col=7, row=2, min_costs=12),
        CopilotAction(step_index=3, action_type=CopilotActionType.SKILL, name="玛恩纳", col=7, row=2, min_kills=15),
    ]
    plan = CopilotPlan(stage_name="1-7", title="测试作业", actions=actions)

    # Customer only has 银灰 (cost 18, delta=+6) and 芬
    matcher = CopilotFuzzyMatcher(owned_roster=["芬", "银灰"])
    adapted_plan, subs = matcher.adapt_plan(plan)

    assert "玛恩纳" in subs
    assert subs["玛恩纳"]["substitute"] == "银灰"
    assert subs["玛恩纳"]["delta_cost"] == 6

    # Action 1: 芬 unchanged
    assert adapted_plan.actions[0].name == "芬"
    assert adapted_plan.actions[0].min_costs == 10

    # Action 2: 玛恩纳 -> 银灰, min_costs 12 + 6 = 18
    assert adapted_plan.actions[1].name == "银灰"
    assert adapted_plan.actions[1].min_costs == 18

    # Action 3: SKILL 玛恩纳 -> SKILL 银灰
    assert adapted_plan.actions[2].name == "银灰"
