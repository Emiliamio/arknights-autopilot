# -*- coding: utf-8 -*-
"""
Unit tests for FleetNotifier
Author: Emiliamio <mio2110767128@163.com>
"""

import pytest
from fleet.notifier import FleetNotifier


@pytest.fixture
def notifier():
    return FleetNotifier()


def test_format_daily_report_markdown(notifier):
    md = notifier.format_daily_report_markdown(
        account_id="TB_9999",
        client_name="闲鱼VIP客户",
        task_name="1-7_farm",
        runs_completed=30,
        drops={"固源岩": 38, "赤金": 15},
        sanity_spent=180
    )
    assert "ASTA" in md
    assert "闲鱼VIP客户" in md
    assert "TB_9999" in md
    assert "1-7_farm" in md
    assert "30" in md
    assert "固源岩" in md
    assert "180" in md


def test_format_captcha_alert_markdown(notifier):
    md = notifier.format_captcha_alert_markdown(
        account_id="XY_8888",
        client_name="测试账号01",
        screenshot_path="/sdcard/captcha.png"
    )
    assert "P0" in md
    assert "CAPTCHA_LOCKED" in md
    assert "XY_8888" in md
    assert "人机验证滑块" in md


def test_dispatch_in_mock_mode(notifier):
    res = notifier.dispatch_daily_report(
        account_id="TEST_01",
        client_name="测试员",
        task_name="daily_sanity",
        runs=10,
        drops={"初级经验书": 20},
        sanity_spent=60,
        mock=True
    )
    assert res["errcode"] == 0
    assert len(notifier.sent_messages) == 1
    assert notifier.sent_messages[0]["type"] == "wecom"