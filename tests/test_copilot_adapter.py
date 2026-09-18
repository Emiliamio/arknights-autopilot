# -*- coding: utf-8 -*-
"""
Unit tests for CopilotAdapter
Author: Emiliamio <mio2110767128@163.com>
"""

import os
import pytest
from tactical.copilot_adapter import CopilotAdapter, CopilotActionType


def test_load_1_7_xiaoran_copilot():
    path = "data/copilots/1-7_xiaoran_duo.json"
    assert os.path.exists(path)
    plan = CopilotAdapter.load_file(path)

    assert plan.stage_name == "main_01-07"
    assert len(plan.opers) == 3
    assert len(plan.actions) == 5

    # Action 1: SpeedUp
    a1 = plan.actions[0]
    assert a1.action_type == CopilotActionType.SPEED_UP

    # Action 2: Deploy 芬 at [9, 2]
    a2 = plan.actions[1]
    assert a2.action_type == CopilotActionType.DEPLOY
    assert a2.name == "芬"
    assert a2.col == 9 and a2.row == 2
    assert a2.direction == "right"
    assert a2.min_costs == 10

    # Action 3: Deploy 克洛丝 at [6, 0]
    a3 = plan.actions[2]
    assert a3.name == "克洛丝"
    assert a3.col == 6 and a3.row == 0
    assert a3.direction == "down"
    assert a3.min_costs == 12

    # Action 4: Skill 克洛丝 at 8 kills
    a4 = plan.actions[3]
    assert a4.action_type == CopilotActionType.SKILL
    assert a4.name == "克洛丝"
    assert a4.min_kills == 8


def test_copilot_round_trip_serialization(tmp_path):
    orig_path = "data/copilots/1-7_xiaoran_duo.json"
    plan = CopilotAdapter.load_file(orig_path)

    out_path = str(tmp_path / "serialized_copilot.json")
    CopilotAdapter.save_file(plan, out_path)

    reloaded = CopilotAdapter.load_file(out_path)
    assert reloaded.stage_name == plan.stage_name
    assert len(reloaded.actions) == len(plan.actions)
    assert reloaded.actions[1].name == "芬"
    assert reloaded.actions[1].min_costs == 10