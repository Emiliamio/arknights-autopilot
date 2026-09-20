# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Unit Tests for StageDatabase (All Mainline Chapters 0~14 & Resources)
Author: Emiliamio <mio2110767128@163.com>
"""

import pytest
from tactical.stage_database import StageDatabase


def test_stage_database_chapter_coverage():
    # Verify all mainline chapters 0 through 17 exist
    for ch in range(18):
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

    # Check Chapter 14
    stages_14 = StageDatabase.list_chapter_stages(14)
    assert len(stages_14) == 23
    assert stages_14[0] == "14-1"
    assert stages_14[-1] == "14-23"

    # Check Chapter 17 (Latest Main Theme)
    stages_17 = StageDatabase.list_chapter_stages(17, include_h_stages=True)
    assert len(stages_17) == 26
    assert stages_17[0] == "17-1"
    assert "H17-4" in stages_17


def test_stage_database_catalog():
    catalog = StageDatabase.get_stage_catalog()
    assert "categories" in catalog
    assert len(catalog["categories"]) == 3

    main_cat = catalog["categories"][0]
    assert main_cat["id"] == "MAIN_THEME"
    assert len(main_cat["groups"]) == 18  # Episodes 00 to 17

    events_cat = catalog["categories"][1]
    assert events_cat["id"] == "EVENTS"
    assert len(events_cat["groups"]) >= 15


def test_stage_database_resource_stages():
    meta_1_7 = StageDatabase.get_stage_metadata("1-7")
    assert meta_1_7["type"] == "MATERIAL"
    assert meta_1_7["cost"] == 6

    meta_ls5 = StageDatabase.get_stage_metadata("LS-5")
    assert meta_ls5["type"] == "EXP"
    assert meta_ls5["cost"] == 30

    meta_event = StageDatabase.get_stage_metadata("HS-1")
    assert meta_event["type"] == "SIDE_STORY"
    assert meta_event["event_name"] == "怀黍离"
