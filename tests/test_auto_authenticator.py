# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Unit Tests for AutoAuthenticator (Bilibili & Official Account Auto-Login)
Author: Emiliamio <mio2110767128@163.com>
"""

import time
import numpy as np
import pytest
from core.auto_authenticator import AutoAuthenticator
from core.game_launcher import GameLauncher


class MockADBClient:
    def __init__(self):
        self.device_serial = "127.0.0.1:16384"
        self.taps = []
        self.shells = []

    def is_instance_running(self):
        return True

    def bring_mumu_to_foreground(self):
        pass

    def connect(self, auto_launch=True):
        return self.device_serial

    def screencap(self):
        return np.zeros((1080, 1920, 3), dtype=np.uint8)

    def tap(self, x, y):
        self.taps.append((x, y))
        return {"status": "OK"}

    def shell(self, cmd, timeout=15):
        self.shells.append(cmd)
        if "pm list packages" in cmd:
            return "package:com.hypergryph.arknights.bilibili"
        if "pidof" in cmd:
            return "12345"
        return "OK"


class MockVisionEngine:
    def ocr(self, frame):
        return [[[[0, 0], [10, 0], [10, 10], [0, 10]], ("终端 作战 基建 干员", 0.99)]], None


def test_auto_authenticator_bilibili_flavor(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)
    mock_adb = MockADBClient()
    mock_vision = MockVisionEngine()
    auth = AutoAuthenticator(adb_client=mock_adb, vision_engine=mock_vision)

    profile = {
        "account_id": "TEST_BILI_01",
        "platform": "BILIBILI",
        "login_account": "13800138000",
        "login_password": "TestPassword2026"
    }

    success = auth.authenticate_account(profile)
    assert auth.launcher.package_name == "com.hypergryph.arknights.bilibili"
    assert success is True


def test_auto_authenticator_official_flavor(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)
    mock_adb = MockADBClient()
    mock_vision = MockVisionEngine()
    auth = AutoAuthenticator(adb_client=mock_adb, vision_engine=mock_vision)

    profile = {
        "account_id": "TEST_OFFICIAL_01",
        "platform": "OFFICIAL",
        "login_account": "13900139000",
        "login_password": "OfficialPassword"
    }

    success = auth.authenticate_account(profile)
    assert auth.launcher.package_name == "com.hypergryph.arknights"
    assert success is True
