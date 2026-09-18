# -*- coding: utf-8 -*-
"""
Unit tests for AccountManager & Priority Queue
Author: Emiliamio <mio2110767128@163.com>
"""

import os
import pytest
from fleet.account_manager import AccountManager


@pytest.fixture
def temp_account_mgr(tmp_path):
    db_file = tmp_path / "test_accounts.db"
    return AccountManager(str(db_file))


def test_add_and_get_account(temp_account_mgr):
    acc = temp_account_mgr.add_or_update_account(
        account_id="TB_10001",
        client_name="淘宝客户张三",
        service_tier="SVIP",
        target_tasks=["1-7_farm", "dorm_rotation"]
    )
    assert acc["account_id"] == "TB_10001"
    assert acc["client_name"] == "淘宝客户张三"
    assert acc["service_tier"] == "SVIP"
    assert "1-7_farm" in acc["target_tasks"]
    assert acc["current_status"] == "IDLE"


def test_priority_queue_svip_first(temp_account_mgr):
    # Add 3 accounts with different tiers
    temp_account_mgr.add_or_update_account("DAILY_1", "散单客户A", service_tier="DAILY")
    temp_account_mgr.add_or_update_account("MONTHLY_1", "月卡客户B", service_tier="MONTHLY")
    temp_account_mgr.add_or_update_account("SVIP_1", "保姆级客户C", service_tier="SVIP")

    # Dispatch #1: Must pick SVIP
    p1 = temp_account_mgr.get_next_dispatchable_account()
    assert p1["account_id"] == "SVIP_1"
    temp_account_mgr.update_status("SVIP_1", "RUNNING")

    # Dispatch #2: Must pick MONTHLY
    p2 = temp_account_mgr.get_next_dispatchable_account()
    assert p2["account_id"] == "MONTHLY_1"
    temp_account_mgr.update_status("MONTHLY_1", "RUNNING")

    # Dispatch #3: Must pick DAILY
    p3 = temp_account_mgr.get_next_dispatchable_account()
    assert p3["account_id"] == "DAILY_1"
    temp_account_mgr.update_status("DAILY_1", "RUNNING")

    # No more idle accounts
    assert temp_account_mgr.get_next_dispatchable_account() is None


def test_status_update_and_validation(temp_account_mgr):
    temp_account_mgr.add_or_update_account("ACC_1", "客户1", service_tier="MONTHLY")
    temp_account_mgr.update_status("ACC_1", "SANITY_EMPTY", instance_idx=1)

    acc = temp_account_mgr.get_account("ACC_1")
    assert acc["current_status"] == "SANITY_EMPTY"
    assert acc["assigned_instance"] == 1
    assert acc["last_run_time"] is not None

    with pytest.raises(ValueError):
        temp_account_mgr.update_status("ACC_1", "ILLEGAL_STATUS")


def test_task_run_logging(temp_account_mgr):
    temp_account_mgr.add_or_update_account("ACC_RUN", "客户Run", service_tier="DAILY")
    run_id = temp_account_mgr.record_task_run(
        account_id="ACC_RUN",
        task_name="1-7_farm",
        runs_completed=20,
        drops={"固源岩": 25},
        sanity_spent=120,
        start_time="2026-09-18 10:00:00",
        end_time="2026-09-18 10:30:00"
    )
    assert run_id > 0

    logs = temp_account_mgr.get_run_logs("ACC_RUN")
    assert len(logs) == 1
    assert logs[0]["runs_completed"] == 20
    assert logs[0]["drops_summary"]["固源岩"] == 25

    acc = temp_account_mgr.get_account("ACC_RUN")
    assert acc["daily_sanity_consumed"] == 120