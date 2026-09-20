# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Unit Tests for StageDatabase (All Mainline Chapters 0~14 & Resources)
Author: Emiliamio <mio2110767128@163.com>
"""

import pytest
from tactical.stage_database import StageDatabase


def test_stage_database_chapter_coverage():
    # Verify all mainline chapters 0 through 14 exist
    for ch in range(15):
        info = StageDatabase.get_chapter_info(ch)
        assert info is not None
        assert "title" in info
        assert "stages_count" in info
        assert info["stages_count"] >= 8

    # Check stage code generation for Chapter 0
    stages_0 = StageDatabase.list_chapter_stages(0)
    assert len(stages_0) == 11
    assert stages_0[0] == "0-1"
    assert stages_0[-1] == "0-11"

    # Check Chapter 14 (Latest Main Theme)
    stages_14 = StageDatabase.list_chapter_stages(14)
    assert len(stages_14) == 23
    assert stages_14[0] == "14-1"
    assert stages_14[-1] == "14-23"


def test_stage_database_resource_stages():
    meta_1_7 = StageDatabase.get_stage_metadata("1-7")
    assert meta_1_7["type"] == "MATERIAL"
    assert meta_1_7["cost"] == 6

    meta_ls5 = StageDatabase.get_stage_metadata("LS-5")
    assert meta_ls5["type"] == "EXP"
    assert meta_ls5["cost"] == 30
