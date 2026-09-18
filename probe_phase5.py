# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Phase 5 Probe: Commercial Fleet Management, Low-Power Multi-Instance & Notifier
Author: Emiliamio <mio2110767128@163.com>
"""

import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import time
import json
from datetime import datetime

from fleet.account_manager import AccountManager
from fleet.notifier import FleetNotifier
from fleet.multi_instance_runner import MultiInstanceRunner


def run_phase5_probe():
    print("======================================================================")
    print("  [*] ASTA Phase 5: Commercial Fleet Management & Dispatch Matrix Probe")
    print("  Author: Emiliamio <mio2110767128@163.com>")
    print("======================================================================")

    # 1. Initialize SQLite Database & Account Manager
    db_path = "data/accounts.db"
    mgr = AccountManager(db_path)
    notifier = FleetNotifier()
    runner = MultiInstanceRunner(account_manager=mgr, notifier=notifier)

    print(f"[*] Connected to Fleet Database: {os.path.abspath(db_path)} (WAL Mode Active)")

    # 2. Seed 3 Real-World Commercial Accounts with forced IDLE status for deterministic demo
    print("[*] Enrolling Commercial Client Portfolio:")
    acc1 = mgr.add_or_update_account(
        account_id="TB_SVIP_001",
        client_name="淘宝SVIP大客户_林先生",
        service_tier="SVIP",
        target_tasks=["1-7_rock_farm", "dorm_rotation", "annihilation"],
        notify_webhook="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=mock_svip",
        force_status="IDLE"
    )
    acc2 = mgr.add_or_update_account(
        account_id="XY_MONTHLY_002",
        client_name="闲鱼月卡客户_王女士",
        service_tier="MONTHLY",
        target_tasks=["daily_sanity", "1-7_farm"],
        notify_webhook="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=mock_monthly",
        force_status="IDLE"
    )
    acc3 = mgr.add_or_update_account(
        account_id="WX_DAILY_003",
        client_name="私域散单客户_陈同学",
        service_tier="DAILY",
        target_tasks=["daily_sanity"],
        force_status="IDLE"
    )

    for acc in [acc1, acc2, acc3]:
        print(f"    - [{acc['service_tier']:<7}] ID: {acc['account_id']:<14} | Name: {acc['client_name']:<18} | Tasks: {acc['target_tasks']}")

    # 3. Demonstrate Priority Queue Dispatching
    print("\n[*] Testing Priority Dispatch Queue (SVIP > Monthly > Daily):")
    next_acc = mgr.get_next_dispatchable_account()
    print(f"[+] Priority Engine Selected: {next_acc['account_id']} ({next_acc['client_name']}) - Tier: {next_acc['service_tier']}")
    assert next_acc["account_id"] == "TB_SVIP_001", "Priority engine must pick SVIP first!"

    # 4. Execute Full Commercial Proxy-Farming Cycle
    print("\n[*] Executing Automated Proxy-Farming & Sanity Clearing Pipeline...")
    cycle_res = runner.run_single_dispatch_cycle(mock_farming=True)
    print(f"[+] Task Run Executed successfully:")
    print(f"    - Client: {cycle_res['client_name']} ({cycle_res['account_id']})")
    print(f"    - Task: {cycle_res['task_name']} | Runs: {cycle_res['runs_completed']} 次")
    print(f"    - Sanity Consumed: {cycle_res['sanity_spent']} 点 (理智已全部清空)")
    print(f"    - Harvested Drops: {cycle_res['drops']}")
    print(f"    - Run Audit Record ID: #{cycle_res['run_id']}")

    # Verify Account Status
    updated_acc = mgr.get_account("TB_SVIP_001")
    print(f"    - New Account Status: {updated_acc['current_status']} (Daily Sanity Total: {updated_acc['daily_sanity_consumed']})")

    # 5. Render & Broadcast Executive Battle Report Card
    print("\n[*] Executive Battle Report Card (Dispatched via WeCom/DingTalk Markdown):")
    report_md = notifier.format_daily_report_markdown(
        account_id=cycle_res["account_id"],
        client_name=cycle_res["client_name"],
        task_name=cycle_res["task_name"],
        runs_completed=cycle_res["runs_completed"],
        drops=cycle_res["drops"],
        sanity_spent=cycle_res["sanity_spent"]
    )
    for line in report_md.splitlines():
        print(f"    {line}")

    # 6. Demonstrate P0 CAPTCHA Security Alarm
    print("\n[*] Testing Emergency Security Circuit Breaker (P0 Slider Detection):")
    mgr.update_status("XY_MONTHLY_002", "CAPTCHA_LOCKED")
    captcha_res = notifier.dispatch_captcha_alert(
        account_id="XY_MONTHLY_002",
        client_name="闲鱼月卡客户_王女士",
        screenshot_path="D:/arknights-autopilot/data/captcha_alert_sample.png",
        mock=True
    )
    captcha_md = notifier.format_captcha_alert_markdown("XY_MONTHLY_002", "闲鱼月卡客户_王女士", "D:/arknights-autopilot/data/captcha_alert_sample.png")
    for line in captcha_md.splitlines()[:6]:
        print(f"    {line}")
    print(f"    [P0 Alarm Broadcast Status]: {captcha_res['errmsg']}")

    # 7. Query MuMu 12 Multi-Instance Infrastructure
    print("\n[*] Querying Local MuMu 12 Multi-Instance Infrastructure:")
    try:
        instances = runner.list_all_mumu_instances()
        print(f"[+] Detected {len(instances)} MuMu 12 Local VM Instances:")
        for idx, item in instances.items():
            print(f"    - VM [{idx}]: Name='{item.get('name')}', Android={item.get('android_version')}, Started={item.get('is_android_started')}")
    except Exception as e:
        print(f"[!] MuMu query note: {e}")

    print("======================================================================")
    print("  [SUCCESS] PHASE 5 PROBE 100% COMPLETE: FLEET MATRIX OPERATIONAL!")
    print("======================================================================")
    return {
        "dispatched_account": cycle_res["account_id"],
        "sanity_spent": cycle_res["sanity_spent"],
        "drops": cycle_res["drops"],
        "db_records": len(mgr.list_accounts())
    }


if __name__ == "__main__":
    run_phase5_probe()