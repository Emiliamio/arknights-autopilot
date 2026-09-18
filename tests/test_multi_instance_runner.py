# -*- coding: utf-8 -*-
"""
Unit tests for MultiInstanceRunner
Author: Emiliamio <mio2110767128@163.com>
"""

import pytest
from fleet.account_manager import AccountManager
from fleet.notifier import FleetNotifier
from fleet.multi_instance_runner import MultiInstanceRunner


@pytest.fixture
def test_env(tmp_path):
    db_file = str(tmp_path / "fleet_test.db")
    mgr = AccountManager(db_file)
    notif = FleetNotifier()
    runner = MultiInstanceRunner(account_manager=mgr, notifier=notif)
    return mgr, notif, runner


def test_runner_single_dispatch_cycle(test_env):
    mgr, notif, runner = test_env

    # Populate accounts
    mgr.add_or_update_account("DAILY_01", "日常单用户", service_tier="DAILY")
    mgr.add_or_update_account("SVIP_01", "SVIP大客户", service_tier="SVIP")

    # Run dispatch cycle: must pick SVIP_01
    res = runner.run_single_dispatch_cycle(mock_farming=True)
    assert res is not None
    assert res["account_id"] == "SVIP_01"
    assert res["service_tier"] == "SVIP"
    assert res["runs_completed"] == 24
    assert res["sanity_spent"] == 144
    assert "固源岩" in res["drops"]

    # Verify account transitioned to SANITY_EMPTY
    acc = mgr.get_account("SVIP_01")
    assert acc["current_status"] == "SANITY_EMPTY"
    assert acc["daily_sanity_consumed"] == 144

    # Second dispatch cycle: must pick DAILY_01
    res2 = runner.run_single_dispatch_cycle(mock_farming=True)
    assert res2 is not None
    assert res2["account_id"] == "DAILY_01"

    # Third dispatch: queue is now empty
    res3 = runner.run_single_dispatch_cycle(mock_farming=True)
    assert res3 is None