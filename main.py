# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Master Unified CLI Entry Point & Commercial Fleet Daemon
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

import argparse
import subprocess
from fleet.account_manager import AccountManager
from fleet.multi_instance_runner import MultiInstanceRunner
from fleet.notifier import FleetNotifier


def print_banner():
    print(r"""
======================================================================
     ___       _______.___________.    ___      
    /   \     /       |           |   /   \     
   /  ^  \   |   (----`---|  |----`  /  ^  \    
  /  /_\  \   \   \       |  |      /  /_\  \   
 /  _____  \---|   |      |  |     /  _____  \  
/__/     \__|______/      |__|    /__/     \__\ 
                                                
  Arknights Sovereign Tactical Autopilot (ASTA)
  Author: Emiliamio <mio2110767128@163.com>
  System: Industrial Autonomous Proxy-Farming Matrix
======================================================================
""")


def cmd_status(args):
    print("[*] ASTA System Health & Infrastructure Audit:")
    mgr = AccountManager()
    accounts = mgr.list_accounts()
    print(f"[+] Total Enrolled Accounts: {len(accounts)}")
    for acc in accounts:
        print(f"    • [{acc['service_tier']:<7}] {acc['account_id']:<14} | {acc['client_name']:<18} | Status: {acc['current_status']:<14} | Daily Sanity: {acc['daily_sanity_consumed']}")

    runner = MultiInstanceRunner(account_manager=mgr)
    try:
        instances = runner.list_all_mumu_instances()
        print(f"[+] Detected {len(instances)} MuMu Player 12 Instances:")
        for idx, inst in instances.items():
            print(f"    • VM [{idx}]: '{inst.get('name')}' (Android {inst.get('android_version')}) | Running: {inst.get('is_android_started')}")
    except Exception as e:
        print(f"[!] MuMu status note: {e}")


def cmd_probe(args):
    target = args.target.lower()
    probe_map = {
        "1": "probe_phase1.py",
        "2": "probe_phase2.py",
        "3": "probe_phase3.py",
        "4": "probe_phase4.py",
        "5": "probe_phase5.py",
        "copilot": "probe_copilot.py",
        "6": "probe_copilot.py"
    }

    if target in probe_map:
        script = probe_map[target]
        print(f"[*] Launching Probe ({script})...\n")
        subprocess.run([sys.executable, script])
    elif target == "all":
        print("[*] Launching ALL 6 Comprehensive Probes sequentially...\n")
        for k in ["1", "2", "3", "4", "5", "copilot"]:
            script = probe_map[k]
            res = subprocess.run([sys.executable, script])
            if res.returncode != 0:
                print(f"[!] Probe {script} failed with code {res.returncode}")
                break
    else:
        print(f"[!] Unknown probe target: {target}. Choose from: 1, 2, 3, 4, 5, copilot, all")


def cmd_test(args):
    print("[*] Running Industrial Pytest Quality Gate (Target: 100% Pass)...\n")
    subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"])


def cmd_daemon(args):
    print("[*] Launching Commercial Fleet Dispatch Daemon...")
    mgr = AccountManager()
    runner = MultiInstanceRunner(account_manager=mgr)
    print("[*] Daemon listening for queued accounts (Press Ctrl+C to stop)...")

    cycle_count = 0
    max_cycles = args.cycles if args.cycles > 0 else 999999

    while cycle_count < max_cycles:
        cycle_count += 1
        print(f"\n--- [Fleet Dispatch Cycle #{cycle_count}] ---")
        res = runner.run_single_dispatch_cycle(mock_farming=True)
        if res:
            print(f"[+] Dispatched Account: {res['account_id']} ({res['client_name']}) | Task: {res['task_name']} | Sanity Spent: {res['sanity_spent']}")
        else:
            print("[*] Queue empty. All client accounts are in SANITY_EMPTY or COMPLETED state.")
            if args.cycles > 0:
                break
            import time
            time.sleep(10)


def main():
    print_banner()
    parser = argparse.ArgumentParser(description="ASTA - Arknights Sovereign Tactical Autopilot")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    p_status = subparsers.add_parser("status", help="Inspect accounts and emulator health")
    p_status.set_defaults(func=cmd_status)

    p_probe = subparsers.add_parser("probe", help="Run Phase 1~5 & Copilot validation probes")
    p_probe.add_argument("target", choices=["1", "2", "3", "4", "5", "copilot", "6", "all"], help="Probe phase or 'all'")
    p_probe.set_defaults(func=cmd_probe)

    p_test = subparsers.add_parser("test", help="Run full automated regression tests")
    p_test.set_defaults(func=cmd_test)

    p_daemon = subparsers.add_parser("daemon", help="Run multi-account automated dispatch daemon")
    p_daemon.add_argument("--cycles", type=int, default=1, help="Max dispatch cycles to run (default: 1)")
    p_daemon.set_defaults(func=cmd_daemon)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()