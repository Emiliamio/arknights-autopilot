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

    assert snap["stage"]["id"] == "1-7"
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
