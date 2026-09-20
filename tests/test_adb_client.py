# -*- coding: utf-8 -*-
"""
Integration & Unit tests for ADBClient
Author: Emiliamio <mio2110767128@163.com>
"""

import pytest
import numpy as np
from core.adb_client import ADBClient
from core.touch_humanizer import TouchHumanizer


@pytest.fixture(scope="module")
def live_client():
    client = ADBClient(
        mumu_manager_path=r"D:\mumu模拟器\MuMu Player 12\nx_main\MuMuManager.exe",
        adb_path=r"D:\mumu模拟器\MuMu Player 12\nx_device\12.0\shell\adb.exe",
        instance_index=0
    )
    if not client.is_instance_running():
        pytest.skip("Live MuMu 12 instance 0 is not currently running on desktop.")
    try:
        serial = client.connect(auto_launch=False)
    except Exception as e:
        pytest.skip(f"Live MuMu emulator instance 0 is unreachable: {e}")
    if not serial:
        pytest.skip("Live MuMu emulator instance 0 could not be connected.")
    return client


def test_adb_client_connection(live_client):
    assert live_client.device_serial is not None
    assert live_client.connected_port in [16384, 16416, 7555, 5555, 5557]


def test_screen_resolution_landscape(live_client):
    res = live_client.get_resolution(force_refresh=True)
    assert res == (1920, 1080), f"Expected landscape (1920, 1080), got {res}"


def test_screencap_valid_matrix(live_client):
    frame = live_client.screencap()
    assert isinstance(frame, np.ndarray)
    assert frame.dtype == np.uint8
    assert frame.shape == (1080, 1920, 3)
    # Ensure frame is not all blank/black (standard screen check)
    assert frame.mean() > 0.0


def test_screencap_benchmark_tiers(live_client):
    bench = live_client.benchmark_screencap(n_frames=3)
    assert bench["avg_latency_ms"] < 400.0, f"Screencap latency {bench['avg_latency_ms']}ms exceeded 400ms SLA"
    assert "tiers_benchmark" in bench


def test_humanized_tap_execution(live_client):
    res = live_client.tap(960, 540)
    assert "x" in res and "y" in res
    assert 0 <= res["x"] < 1920
    assert 0 <= res["y"] < 1080
    assert 50 <= res["duration_ms"] <= 150


def test_bezier_motionevent_swipe(live_client):
    res = live_client.swipe_bezier(600, 500, 1200, 500, steps=10)
    assert res["status"] == "success"
    assert res["trajectory_steps"] == 11
    assert res["execution_time_ms"] > 0