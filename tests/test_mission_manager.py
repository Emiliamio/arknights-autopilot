# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Unit Tests for Mission Manager & Task Orchestrator (SQLite WAL)
Author: Emiliamio <mio2110767128@163.com>
"""

import os
import pytest
from fleet.mission_manager import MissionManager, MissionStatus, MissionType


@pytest.fixture
def temp_mission_mgr(tmp_path):
    db_file = str(tmp_path / "test_missions.db")
    return MissionManager(db_path=db_file)


def test_mission_crud_lifecycle(temp_mission_mgr):
    mgr = temp_mission_mgr

    # 1. Create Mission
    mission = mgr.create_mission(
        account_id="TB_SVIP_001",
        mission_type=MissionType.CAMPAIGN_CLEAR,
        target_chapter=0,
        params={"auto_skip": True}
    )

    m_id = mission["mission_id"]
    assert m_id.startswith("TASK_")
    assert mission["status"] == MissionStatus.QUEUED
    assert mission["target_chapter"] == 0
    assert mission["params"]["auto_skip"] is True

    # 2. Checkout Next Mission
    checked_out = mgr.checkout_next_queued_mission()
    assert checked_out is not None
    assert checked_out["mission_id"] == m_id
    assert checked_out["status"] == MissionStatus.RUNNING

    # 3. Update Progress
    mgr.update_progress(m_id, "正在通关 0-1...")
    m_progress = mgr.get_mission(m_id)
    assert m_progress["progress_info"] == "正在通关 0-1..."

    # 4. Complete Mission
    mgr.complete_mission(m_id, "第 0 章全关卡通关成功")
    m_completed = mgr.get_mission(m_id)
    assert m_completed["status"] == MissionStatus.COMPLETED
    assert "全关卡通关成功" in m_completed["result_summary"]


def test_mission_fifo_queue(temp_mission_mgr):
    mgr = temp_mission_mgr

    m1 = mgr.create_mission("ACC_1", MissionType.CAMPAIGN_CLEAR, target_chapter=0)
    m2 = mgr.create_mission("ACC_2", MissionType.SANITY_FARM, target_stage="1-7")

    out1 = mgr.checkout_next_queued_mission()
    assert out1["mission_id"] == m1["mission_id"]

    out2 = mgr.checkout_next_queued_mission()
    assert out2["mission_id"] == m2["mission_id"]

    out3 = mgr.checkout_next_queued_mission()
    assert out3 is None


def test_mission_fail_and_cancel(temp_mission_mgr):
    mgr = temp_mission_mgr

    m_fail = mgr.create_mission("ACC_F", MissionType.CAMPAIGN_CLEAR, target_chapter=1)
    mgr.fail_mission(m_fail["mission_id"], "理智耗尽")
    res_f = mgr.get_mission(m_fail["mission_id"])
    assert res_f["status"] == MissionStatus.FAILED
    assert "理智耗尽" in res_f["result_summary"]

    m_cancel = mgr.create_mission("ACC_C", MissionType.DAILY_ROUTINE)
    mgr.cancel_mission(m_cancel["mission_id"])
    res_c = mgr.get_mission(m_cancel["mission_id"])
    assert res_c["status"] == MissionStatus.CANCELLED
