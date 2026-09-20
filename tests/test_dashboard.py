# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Unit & Integration Tests for PRTS Web Tactical Command Dashboard
Author: Emiliamio <mio2110767128@163.com>
"""

import time
import json
import urllib.request
import urllib.error
import pytest

from fleet.dashboard.server import DashboardServer, TelemetryStore


def test_telemetry_store_lifecycle():
    """Verify thread-safe TelemetryStore updates and snapshot serialization."""
    store = TelemetryStore()
    snap = store.get_snapshot()

    assert "telemetry" in snap
    assert "stage" in snap
    assert "operators" in snap
    assert "copilot" in snap
    assert "anti_cheat" in snap
    assert "logs" in snap

    assert snap["stage"]["id"] in ("1-7", "IDLE")
    assert snap["telemetry"]["dp"] == 0
    assert snap["telemetry"]["threat_level"] == "SAFE"

    # Test live combat update
    store.update_from_combat(dp=45, battle_state="VICTORY", speed_2x=False)
    updated_snap = store.get_snapshot()
    assert updated_snap["telemetry"]["dp"] == 45
    assert updated_snap["telemetry"]["battle_state"] == "VICTORY"
    assert updated_snap["telemetry"]["speed_2x"] is False

    # Test event logging
    store.add_log("ALERT", "Test emergency interception log")
    logs = store.get_snapshot()["logs"]
    assert any("Test emergency interception log" in l["msg"] for l in logs)


def test_dashboard_server_startup_and_endpoints():
    """Verify DashboardServer launches, handles REST API and static files, and shuts down."""
    test_port = 18848
    server = DashboardServer(host="127.0.0.1", port=test_port)
    server.start(block=False)

    time.sleep(0.5)  # Wait for server thread startup
    assert server.is_running is True

    base_url = f"http://127.0.0.1:{test_port}"

    try:
        # 1. Test Static Index serving
        req = urllib.request.Request(f"{base_url}/")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            content = resp.read().decode("utf-8")
            assert "PRTS TACTICAL COMMAND DASHBOARD" in content

        # 2. Test GET /api/status
        req = urllib.request.Request(f"{base_url}/api/status")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "ONLINE"
            assert "Emiliamio" in data["author"]
            assert data["port"] == test_port

        # 3. Test GET /api/telemetry
        req = urllib.request.Request(f"{base_url}/api/telemetry")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "telemetry" in data
            assert "operators" in data

        # 4. Test GET /api/accounts
        req = urllib.request.Request(f"{base_url}/api/accounts")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "accounts" in data
            assert data["total"] >= 1

        # 5. Test GET /api/fleet
        req = urllib.request.Request(f"{base_url}/api/fleet")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "instances" in data

        # 6. Test POST /api/override (PANIC_INTERCEPT)
        post_data = json.dumps({"action": "PANIC_INTERCEPT"}).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/api/override",
            data=post_data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "SUCCESS"

        # Verify threat level changed in store
        snap = server.telemetry_store.get_snapshot()
        assert snap["telemetry"]["threat_level"] == "PANIC_LEAK"

        # 7. Test POST /api/override (CLEAR_PANIC)
        post_data = json.dumps({"action": "CLEAR_PANIC"}).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/api/override",
            data=post_data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200

        snap = server.telemetry_store.get_snapshot()
        assert snap["telemetry"]["threat_level"] == "SAFE"

    finally:
        server.stop()
        time.sleep(0.3)
        assert server.is_running is False


def test_dashboard_full_api_crud_and_controls():
    """Verify full CRUD operations on missions, accounts, roster, and emergency stop via Dashboard."""
    test_port = 18849
    server = DashboardServer(host="127.0.0.1", port=test_port)
    server.start(block=False)
    time.sleep(0.5)

    base_url = f"http://127.0.0.1:{test_port}"

    try:
        # 1. Test POST /api/missions (create new mission)
        payload = json.dumps({
            "account_id": "EMILIAMIO_MAIN",
            "mission_type": "SANITY_FARM",
            "target_stage": "1-7",
            "params": {"auto_skip_story": True}
        }).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/api/missions", data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "SUCCESS"
            assert "mission" in data
            m_id = data["mission"]["mission_id"]

        # 2. Test GET /api/missions
        req = urllib.request.Request(f"{base_url}/api/missions")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert any(m["mission_id"] == m_id for m in data["missions"])

        # 3. Test POST /api/missions/delete
        del_payload = json.dumps({"mission_id": m_id}).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/api/missions/delete", data=del_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "SUCCESS"
            assert data["deleted"] is True

        # 4. Test POST /api/accounts/create and /api/accounts/delete
        test_acc_id = "TEST_CLIENT_999"
        acc_payload = json.dumps({
            "account_id": test_acc_id,
            "client_name": "自动化测试客户",
            "platform": "BILIBILI",
            "service_tier": "MONTHLY"
        }).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/api/accounts/create", data=acc_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "SUCCESS"

        del_acc_payload = json.dumps({"account_id": test_acc_id}).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/api/accounts/delete", data=del_acc_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "SUCCESS"
            assert data["deleted"] is True

        # 5. Test GET /api/roster
        req = urllib.request.Request(f"{base_url}/api/roster?account_id=EMILIAMIO_MAIN")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "operators" in data
            assert data["total"] > 0

        # 6. Test POST /api/squad/synthesize
        syn_payload = json.dumps({"account_id": "EMILIAMIO_MAIN", "stage_id": "1-7"}).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/api/squad/synthesize", data=syn_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "squad" in data
            assert data["total_operators"] == 12

        # 7. Test POST /api/stop (emergency stop)
        stop_payload = json.dumps({"action": "EMERGENCY_STOP"}).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/api/stop", data=stop_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "ABORTED"

    finally:
        server.stop()
        time.sleep(0.3)
        assert server.is_running is False


def test_dashboard_stage_catalog_and_copilot_cloud_api():
    """Verify /api/stages/catalog, /api/copilot/cloud/search, and /api/copilot/auto_dispatch."""
    test_port = 18850
    server = DashboardServer(host="127.0.0.1", port=test_port)
    server.start(block=False)
    time.sleep(0.5)

    base_url = f"http://127.0.0.1:{test_port}"

    try:
        # 1. Test GET /api/stages/catalog
        req = urllib.request.Request(f"{base_url}/api/stages/catalog")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "main_theme" in data
            assert "events" in data
            assert "resources" in data
            assert len(data["main_theme"]) == 18  # Episode 00 to 17
            assert len(data["events"]) >= 10

        # 2. Test GET /api/copilot/cloud/search?stage=1-7
        req = urllib.request.Request(f"{base_url}/api/copilot/cloud/search?stage=1-7&page=1&limit=5")
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["stage"] == "1-7"
            assert "plans" in data
            assert len(data["plans"]) > 0

        # 3. Test POST /api/copilot/auto_dispatch (auto-resolve best plan and dispatch mission)
        payload = json.dumps({
            "account_id": "EMILIAMIO_MAIN",
            "stage_name": "1-7"
        }).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/api/copilot/auto_dispatch", data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "SUCCESS"
            assert "mission_id" in data
            assert data["stage"] == "1-7"

    finally:
        server.stop()
        time.sleep(0.3)
        assert server.is_running is False

