# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Unit Tests for AbortController & Global Emergency Stop
Author: Emiliamio <mio2110767128@163.com>
"""

import pytest
from core.abort_controller import AbortController
from fleet.mission_manager import MissionManager, MissionStatus, MissionType


def test_abort_controller_signal_cycle():
    """Verify emergency stop signal trigger, reason recording, and reset."""
    AbortController.reset()
    assert AbortController.is_aborted() is False

    AbortController.trigger_abort("测试全局熔断指令")
    assert AbortController.is_aborted() is True
    assert "测试全局熔断指令" in AbortController.get_reason()

    AbortController.reset()
    assert AbortController.is_aborted() is False
    assert AbortController.get_reason() == ""


def test_abort_running_missions(tmp_path):
    """Verify running missions are immediately flipped to CANCELLED upon abort."""
    db_file = str(tmp_path / "test_abort_missions.db")
    mgr = MissionManager(db_path=db_file)

    # Create mission and check it out as RUNNING
    m = mgr.create_mission("TEST_ACC", MissionType.CAMPAIGN_CLEAR, target_chapter=0)
    checked = mgr.checkout_next_queued_mission()
    assert checked["status"] == MissionStatus.RUNNING

    # Abort all running
    stopped_count = mgr.abort_all_running_missions("单元测试紧急停机")
    assert stopped_count == 1

    aborted_m = mgr.get_mission(m["mission_id"])
    assert aborted_m["status"] == MissionStatus.CANCELLED
    assert "单元测试紧急停机" in aborted_m["result_summary"]
