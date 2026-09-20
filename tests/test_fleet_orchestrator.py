# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Unit Tests for FleetOrchestrator (Multi-Instance Concurrency & ThreadPool)
Author: Emiliamio <mio2110767128@163.com>
"""

import pytest
from fleet.fleet_orchestrator import FleetOrchestrator
from fleet.mission_manager import MissionManager, MissionStatus, MissionType
from fleet.account_manager import AccountManager
from core.abort_controller import AbortController


@pytest.fixture
def mock_fleet(tmp_path):
    # Reset singleton
    FleetOrchestrator._instance = None
    db_missions = str(tmp_path / "test_orch_missions.db")
    db_accounts = str(tmp_path / "test_orch_accounts.db")
    mMgr = MissionManager(db_path=db_missions)
    aMgr = AccountManager(db_path=db_accounts)

    # Enroll 2 accounts: one on VM 0, one on VM 1
    aMgr.add_or_update_account("ACC_VM0", "大客户0", service_tier="SVIP", assigned_instance=0)
    aMgr.add_or_update_account("ACC_VM1", "大客户1", service_tier="MONTHLY", assigned_instance=1)

    orchestrator = FleetOrchestrator(mission_manager=mMgr, account_manager=aMgr, max_workers=2)
    return orchestrator, mMgr, aMgr


def test_fleet_orchestrator_initialization(mock_fleet):
    orch, mMgr, aMgr = mock_fleet
    telemetry = orch.get_fleet_telemetry()

    assert "max_concurrency" in telemetry
    assert "slots" in telemetry
    assert len(telemetry["slots"]) >= 1

    # Check port calculation (16384 for slot 0, 16416 for slot 1)
    slot0 = next((s for s in telemetry["slots"] if s["instance_index"] == 0), None)
    assert slot0 is not None
    assert slot0["port"] == 16384


def test_fleet_orchestrator_stop_all(mock_fleet):
    orch, mMgr, aMgr = mock_fleet
    AbortController.reset()

    orch.stop_all("测试紧急熔断")
    assert AbortController.is_aborted() is True
    AbortController.reset()

    telemetry = orch.get_fleet_telemetry()
    for s in telemetry["slots"]:
        assert s["status"] == "IDLE"
