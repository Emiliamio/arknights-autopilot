# -*- coding: utf-8 -*-
"""
ASTA - Multi-Instance Concurrency & Stress Testing Suite
Author: Emiliamio <mio2110767128@163.com>
"""

import time
import pytest
from unittest.mock import MagicMock, patch

from fleet.fleet_orchestrator import FleetOrchestrator
from fleet.mission_manager import MissionManager, MissionStatus, MissionType
from fleet.account_manager import AccountManager
from core.abort_controller import AbortController


@pytest.fixture
def isolated_fleet(tmp_path):
    FleetOrchestrator._instance = None
    db_missions = str(tmp_path / "stress_missions.db")
    db_accounts = str(tmp_path / "stress_accounts.db")
    mMgr = MissionManager(db_path=db_missions)
    aMgr = AccountManager(db_path=db_accounts)

    # Enroll 3 accounts: SVIP, MONTHLY, DAILY
    aMgr.add_or_update_account("ACC_SVIP", "客户SVIP", service_tier="SVIP", assigned_instance=0)
    aMgr.add_or_update_account("ACC_MONTH", "客户月卡", service_tier="MONTHLY", assigned_instance=1)
    aMgr.add_or_update_account("ACC_DAILY", "客户日常", service_tier="DAILY", assigned_instance=0)

    orchestrator = FleetOrchestrator(
        mission_manager=mMgr,
        account_manager=aMgr,
        max_workers=2
    )
    return orchestrator, mMgr, aMgr


def test_multi_vm_parallel_dispatch(isolated_fleet):
    orch, mMgr, aMgr = isolated_fleet

    # Queue 2 missions targeting VM 0 and VM 1
    m1 = mMgr.create_mission(account_id="ACC_SVIP", mission_type=MissionType.DAILY_ROUTINE)
    m2 = mMgr.create_mission(account_id="ACC_MONTH", mission_type=MissionType.DAILY_ROUTINE)

    # Mock TaskExecutor.execute_mission to simulate work
    with patch("fleet.fleet_orchestrator.TaskExecutor") as mock_exec_cls:
        mock_instance = MagicMock()
        mock_exec_cls.return_value = mock_instance
        mock_instance.execute_mission.return_value = {"status": "SUCCESS"}

        dispatched = orch.dispatch_pending_missions(force_reset_abort=True)
        assert dispatched == 2

        # Verify slots status
        telemetry = orch.get_fleet_telemetry()
        slots = {s["instance_index"]: s for s in telemetry["slots"]}

        assert 0 in slots
        assert 1 in slots
        assert slots[0]["port"] == 16384
        assert slots[1]["port"] == 16416


def test_account_rotation_on_same_slot(tmp_path):
    FleetOrchestrator._instance = None
    db_m = str(tmp_path / "rot_m.db")
    db_a = str(tmp_path / "rot_a.db")
    mMgr = MissionManager(db_path=db_m)
    aMgr = AccountManager(db_path=db_a)

    aMgr.add_or_update_account("ACC_SVIP", "客户SVIP", service_tier="SVIP", assigned_instance=0)
    aMgr.add_or_update_account("ACC_DAILY", "客户日常", service_tier="DAILY", assigned_instance=0)

    orch = FleetOrchestrator(mission_manager=mMgr, account_manager=aMgr, max_workers=2)

    executed_accounts = []

    def mock_exec(mission):
        executed_accounts.append(mission["account_id"])
        time.sleep(0.05)
        return {"status": "SUCCESS"}

    with patch("fleet.fleet_orchestrator.TaskExecutor") as mock_exec_cls:
        mock_instance = MagicMock()
        mock_exec_cls.return_value = mock_instance
        mock_instance.execute_mission.side_effect = mock_exec

        # 1. Dispatch first mission for ACC_SVIP on slot 0
        m1 = mMgr.create_mission(account_id="ACC_SVIP", mission_type=MissionType.DAILY_ROUTINE)
        orch.dispatch_pending_missions(force_reset_abort=True)
        time.sleep(0.2)

        # Slot 0 ran ACC_SVIP
        assert orch._slots[0]["last_used_account"] == "ACC_SVIP"

        # 2. Dispatch second mission for ACC_DAILY on slot 0 (rotation)
        m2 = mMgr.create_mission(account_id="ACC_DAILY", mission_type=MissionType.DAILY_ROUTINE)
        orch.dispatch_pending_missions(force_reset_abort=True)
        time.sleep(0.2)

        # Account rotation occurred on slot 0: now last_used_account is ACC_DAILY
        assert orch._slots[0]["last_used_account"] == "ACC_DAILY"
        assert executed_accounts == ["ACC_SVIP", "ACC_DAILY"]


def test_sanity_depletion_auto_skip(isolated_fleet):
    orch, mMgr, aMgr = isolated_fleet

    # Mark ACC_SVIP as SANITY_EMPTY
    aMgr.update_status("ACC_SVIP", "SANITY_EMPTY", instance_idx=0)

    # Queue missions for ACC_SVIP and ACC_MONTH
    m1 = mMgr.create_mission(account_id="ACC_SVIP", mission_type=MissionType.SANITY_FARM, target_stage="1-7")
    m2 = mMgr.create_mission(account_id="ACC_MONTH", mission_type=MissionType.DAILY_ROUTINE)

    executed_accounts = []

    def mock_exec(mission):
        executed_accounts.append(mission["account_id"])
        return {"status": "SUCCESS"}

    with patch("fleet.fleet_orchestrator.TaskExecutor") as mock_exec_cls:
        mock_instance = MagicMock()
        mock_exec_cls.return_value = mock_instance
        mock_instance.execute_mission.side_effect = mock_exec

        dispatched = orch.dispatch_pending_missions(force_reset_abort=True)
        time.sleep(0.1)

        # ACC_SVIP should be skipped due to SANITY_EMPTY, only ACC_MONTH dispatched
        assert dispatched == 1
        assert "ACC_MONTH" in executed_accounts
        assert "ACC_SVIP" not in executed_accounts


def test_concurrent_emergency_stop_all(isolated_fleet):
    orch, mMgr, aMgr = isolated_fleet
    AbortController.reset()

    # Queue missions
    mMgr.create_mission(account_id="ACC_SVIP", mission_type=MissionType.DAILY_ROUTINE)
    mMgr.create_mission(account_id="ACC_MONTH", mission_type=MissionType.DAILY_ROUTINE)

    with patch("fleet.fleet_orchestrator.TaskExecutor") as mock_exec_cls:
        mock_instance = MagicMock()
        mock_exec_cls.return_value = mock_instance
        # Simulate long-running task
        mock_instance.execute_mission.side_effect = lambda m: time.sleep(5)

        orch.dispatch_pending_missions(force_reset_abort=True)

        # Trigger emergency stop across all fleet slots
        orch.stop_all(reason="压测紧急制动")

        assert AbortController.is_aborted() is True
        telemetry = orch.get_fleet_telemetry()
        for slot in telemetry["slots"]:
            assert slot["status"] == "IDLE"
            assert "已中止" in slot["progress"]

    AbortController.reset()


def test_fleet_telemetry_detailed_reporting(isolated_fleet):
    orch, mMgr, aMgr = isolated_fleet
    telemetry = orch.get_fleet_telemetry()

    assert telemetry["total_slots"] >= 2
    assert telemetry["max_concurrency"] == 2
    for slot in telemetry["slots"]:
        assert "port" in slot
        assert "instance_index" in slot
        assert "status" in slot
