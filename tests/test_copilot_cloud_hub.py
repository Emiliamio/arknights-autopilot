# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Unit tests for MAA Copilot Cloud Hub
Author: Emiliamio <mio2110767128@163.com>
"""

import os
import json
import pytest
from tactical.copilot_cloud_hub import CopilotCloudHub


def test_copilot_cloud_hub_init_and_cache_dir():
    """Verify CopilotCloudHub initializes cache directory correctly."""
    hub = CopilotCloudHub()
    assert os.path.isdir(hub.cache_dir)
    assert os.path.isabs(hub.cache_dir)


def test_copilot_cloud_hub_search_cloud_plans():
    """Verify search_cloud_plans returns valid list of plans with live or fallback data."""
    hub = CopilotCloudHub()
    res = hub.search_cloud_plans(stage_keyword="1-7", page=1, limit=5)

    assert isinstance(res, list)
    assert len(res) > 0

    first_plan = res[0]
    assert "id" in first_plan
    assert "title" in first_plan
    assert "uploader" in first_plan
    assert "likes" in first_plan


def test_copilot_cloud_hub_auto_resolve_best_plan():
    """Verify auto_resolve_best_plan returns a valid CopilotPlan and cached plan file path."""
    hub = CopilotCloudHub()
    plan, plan_path = hub.auto_resolve_best_plan("1-7")

    assert plan is not None
    assert os.path.isfile(plan_path)
    assert plan_path.endswith(".json")

    # Verify content is valid JSON
    with open(plan_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "stage_name" in data
    assert "actions" in data


def test_copilot_cloud_hub_fallback_for_obscure_stage():
    """Verify fallback mechanism produces a valid baseline plan for non-existent stage."""
    hub = CopilotCloudHub()
    plan, plan_path = hub.auto_resolve_best_plan("NON_EXISTENT_STAGE_999")

    assert plan is not None
    assert os.path.isfile(plan_path)
    with open(plan_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["stage_name"] == "NON_EXISTENT_STAGE_999"
    assert len(data["actions"]) >= 1
