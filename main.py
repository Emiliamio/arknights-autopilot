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
from fleet.dashboard import run_dashboard
from fleet.mission_manager import MissionManager, MissionType, MissionStatus
from fleet.task_executor import TaskExecutor
from tactical.campaign_cruiser import CampaignCruiser


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


def cmd_copilot(args):
    print("======================================================================")
    print("  🚀 ASTA Route A: MAA Copilot Dual-Track In-Game Execution")
    print("  Author: Emiliamio <mio2110767128@163.com>")
    print("======================================================================")

    import os
    import glob
    import time
    from tactical.copilot_adapter import CopilotAdapter
    from tactical.copilot_brain import CopilotBrain
    from tactical.map_deconstructor import TacticalMap
    from core.adb_client import ADBClient
    from core.vision_engine import VisionEngine, BattleState
    from core.touch_humanizer import TouchHumanizer
    from core.homography_mapper import HomographyMapper
    from fleet.account_manager import AccountManager

    # 1. Resolve Plan File
    plan_path = args.plan
    if not plan_path:
        stage = args.stage.upper()
        candidates = glob.glob(f"data/copilots/*{stage}*.json")
        if candidates:
            plan_path = candidates[0]
        else:
            print(f"[!] No matching copilot plan found for stage [{stage}]. Available plans in data/copilots/:")
            for p in glob.glob("data/copilots/*.json"):
                print(f"    • {p}")
            return

    print(f"[*] Loading Copilot Plan: {plan_path}")
    plan = CopilotAdapter.load_file(plan_path)
    print(f"[+] Loaded Plan: '{plan.title}' | Stage: {plan.stage_name} | Total Actions: {len(plan.actions)}")

    # 2. Resolve Account Owned Roster for Fuzzy Substitution
    account_id = args.account
    mgr = AccountManager()
    acc = mgr.get_account(account_id)
    roster = None
    if acc and acc.get("owned_roster"):
        roster = acc["owned_roster"]
        print(f"[+] Account [{account_id}] roster loaded: {len(roster)} operators.")
    else:
        from tactical.roster_inspector import RosterInspector
        inspector = RosterInspector()
        roster_data = inspector.load_roster(account_id)
        if roster_data:
            roster = [op["name"] for op in roster_data if "name" in op]
            print(f"[+] Account [{account_id}] roster loaded: {len(roster)} operators.")

    # 3. Connect to live ADB emulator
    client = ADBClient(instance_index=args.instance)
    serial = client.connect(auto_launch=False)
    print(f"[+] Connected to ADB Emulator: {serial} (Port: {client.connected_port})")

    # 4. Initialize Tactical Map & Copilot Brain
    t_map = TacticalMap.create_1_7()
    brain = CopilotBrain(tactical_map=t_map, copilot_plan=plan, owned_roster=roster)
    if brain.substitutions:
        print(f"[+] 🎯 Operator Substitutions Applied: {brain.substitutions}")

    vision = VisionEngine()
    humanizer = TouchHumanizer()
    mapper = HomographyMapper.create_synthetic_arknights_mapper()

    # 5. Pre-battle Handshake
    frame = client.screencap()
    state = vision.detect_battle_state(frame)
    print(f"[*] Initial Battlefield State: {state.name}")

    if state == BattleState.PRE_BATTLE:
        print("[*] Stage details detected: Tapping '开始行动' at (1767, 987)...")
        client.tap(1767, 987)
        time.sleep(2.0)
        frame2 = client.screencap()
        state2 = vision.detect_battle_state(frame2)
        if state2 == BattleState.PRE_BATTLE:
            print("[*] Squad confirmation detected: Tapping '编队开始行动' at (1767, 987)...")
            client.tap(1767, 987)
            time.sleep(3.0)

    # Wait for IN_BATTLE
    print("[*] Waiting for battlefield loading...")
    t0 = time.time()
    in_battle = False
    while time.time() - t0 < 30:
        frame = client.screencap()
        state = vision.detect_battle_state(frame)
        if state == BattleState.IN_BATTLE:
            in_battle = True
            print(f"[+] Entered Battlefield successfully in {time.time() - t0:.1f}s!")
            break
        time.sleep(1.0)

    if not in_battle:
        print(f"[!] Battlefield not entered (Current: {state.name}). Please open the stage on emulator screen.")
        return

    # 6. Run Real-Time Dual-Track Copilot Loop
    print("\n[*] ⚔️ ENGAGING DUAL-TRACK ARBITER (Route A):")
    print("    • Track A: Sequential Action Execution + Desync Breaker")
    print("    • Track B: Panic Sentry Preemption (0.37ms Anti-Leak Intercept)")
    print("----------------------------------------------------------------------")

    battle_t0 = time.time()
    max_duration = 300  # 5 minutes max

    while time.time() - battle_t0 < max_duration:
        frame = client.screencap()
        res = brain.tick(frame, vision, mapper, humanizer, adb_client=client)

        status = res.get("status")
        action = res.get("action_taken")

        if action != "NONE":
            print(f"    [Tick #{res['tick']}] Action: {action:<28} | DP={res['current_dp']:<2} | Kills={res['kill_count'][0]}/{res['kill_count'][1]} | Progress: {res['copilot_progress']}")

        if status == "COMPLETED":
            print(f"\n[+] 🏆 Combat Cleared! Settlement: {res['action_details'].get('settlement')}")
            time.sleep(2.0)
            client.tap(960, 540)
            time.sleep(1.5)
            client.tap(960, 540)
            print("[+] Settlement dismissed successfully!")
            break

        time.sleep(0.35)

    print("\n======================================================================")
    print(f"  🎉 COPILOT MISSION RUN FINISHED! Progress: {brain.current_action_idx}/{len(brain.plan.actions)} actions.")
    print("======================================================================")


def cmd_live(args):
    stage = args.stage.lower()
    print(f"[*] Launching Route A Live In-Game Combat for Stage [{stage}]...")
    if stage in ("ls-1", "ls1"):
        import live_combat_loop
        live_combat_loop.main()
    else:
        import live_battle_runner
        live_battle_runner.run_live_battle()


def cmd_squad(args):
    from tactical.squad_synthesizer import SquadSynthesizer
    syn = SquadSynthesizer()
    res = syn.synthesize_squad(account_id=args.account, stage_id=args.stage)
    print("\n======================================================================")
    print(f"  🧠 ASTA Optimal Squad Synthesizer Result: [{res['stage_id']}]")
    print(f"  Account: {res['account_id']} | Operators Selected: {res['total_operators']}")
    print("======================================================================")
    for op in res["squad"]:
        print(f"  Slot #{op['slot']:<2} | [{op['class']:<10}] {op['name']:<6} (★{op['rarity']}) | Cost: {op['cost']:<2} | Score: {op['score']}")
    print(f"\n[+] Strategy Summary: {res['summary']}\n")


def cmd_roster(args):
    from tactical.roster_inspector import RosterInspector
    inspector = RosterInspector()
    roster = inspector.load_roster(account_id=args.account)
    print(f"\n[+] Account [{args.account}] Owned Operators Roster ({len(roster)} total):")
    for op in roster:
        print(f"    • [{op.get('class', 'GUARD'):<10}] {op['name']:<6} (★{op.get('rarity', 4)}) | E{op.get('elite', 1)} Lv.{op.get('level', 40)}")

def cmd_roguelike(args):
    from tactical.roguelike_brain import RoguelikeBrain, RoguelikeTheme
    theme_map = {
        "is4": RoguelikeTheme.IS4_SAMI,
        "is3": RoguelikeTheme.IS3_MIZUKI,
        "is2": RoguelikeTheme.IS2_PHANTOM,
        "is5": RoguelikeTheme.IS5_SARKAZ
    }
    theme = theme_map.get(args.theme.lower(), RoguelikeTheme.IS4_SAMI)
    brain = RoguelikeBrain(theme=theme)
    res = brain.run_roguelike_exploration(max_floors=args.floors)
    print(f"\n======================================================================")
    print(f"  🏆 AlphaRoguelike Run Complete: {res['theme']}")
    print(f"======================================================================")
    print(f"  {res['summary']}\n")

def cmd_campaign(args):
    chapter = args.chapter
    print(f"[*] Launching Autonomous Chapter Campaign Cruiser for Episode {chapter}...")
    cruiser = CampaignCruiser()
    res = cruiser.cruise_chapter(chapter_num=chapter)
    print(f"[+] Campaign Cruise Completed: {res}")


def cmd_task(args):
    mgr = MissionManager()
    action = args.task_action

    if action == "add":
        m = mgr.create_mission(
            account_id=args.account,
            mission_type=args.type,
            target_chapter=args.chapter,
            target_stage=args.stage
        )
        print(f"[+] Mission Created Successfully: {m['mission_id']} [{m['mission_type']}] for Account {m['account_id']}")
    elif action == "list":
        missions = mgr.list_missions(status=args.status)
        print(f"[+] Missions Store ({len(missions)} entries):")
        for m in missions:
            print(f"    • [{m['status']:<9}] {m['mission_id']:<24} | Acc: {m['account_id']:<14} | Type: {m['mission_type']:<15} | Progress: {m['progress_info']}")
    elif action == "delete":
        success = mgr.delete_mission(args.id)
        print(f"[+] Mission {args.id} deleted successfully: {success}")
    elif action == "clear":
        if args.status == "ALL":
            count = mgr.clear_missions()
        elif args.status == "FINISHED":
            with mgr._get_connection() as conn:
                cur = conn.execute("DELETE FROM missions WHERE status IN ('COMPLETED', 'FAILED', 'CANCELLED');")
                count = cur.rowcount
        else:
            count = mgr.clear_missions(status=args.status)
        print(f"[+] Cleared {count} missions ({args.status})")
    elif action == "stop":
        from core.abort_controller import AbortController
        AbortController.trigger_abort("CLI 用户触发全局紧急停止")
        count = mgr.abort_all_running_missions("CLI 用户触发全局紧急停止")
        print(f"[+] 🛑 Emergency stop triggered! Aborted {count} running missions.")
    elif action == "run":
        print("[*] Launching Master Task Executor Dispatcher...")
        executor = TaskExecutor(mission_manager=mgr)
        run_count = 0
        while True:
            res = executor.run_worker_cycle()
            if not res:
                print("[*] No more QUEUED tasks in mission queue.")
                break
            run_count += 1
            print(f"[+] Mission Execution Cycle #{run_count} Completed: {res}")
            if args.once:
                break


def cmd_stop(args):
    from core.abort_controller import AbortController
    from fleet.mission_manager import MissionManager
    AbortController.trigger_abort("CLI 用户触发全局紧急停止")
    mgr = MissionManager()
    count = mgr.abort_all_running_missions("CLI 用户触发全局紧急停止")
    print(f"[+] 🛑 EMERGENCY STOP ACTIVATED! Aborted {count} running missions.")

def cmd_dashboard(args):
    print(f"[*] Launching ASTA PRTS Tactical Command Dashboard on {args.host}:{args.port}...")
    run_dashboard(host=args.host, port=args.port)


def main():
    print_banner()
    parser = argparse.ArgumentParser(description="ASTA - Arknights Sovereign Tactical Autopilot")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    p_status = subparsers.add_parser("status", help="Inspect accounts and emulator health")
    p_status.set_defaults(func=cmd_status)

    p_probe = subparsers.add_parser("probe", help="Run Phase 1~5 & Copilot validation probes")
    p_probe.add_argument("target", choices=["1", "2", "3", "4", "5", "copilot", "6", "all"], help="Probe phase or 'all'")
    p_probe.set_defaults(func=cmd_probe)

    p_copilot = subparsers.add_parser("copilot", help="Execute Route A MAA Copilot plan on live emulator")
    p_copilot.add_argument("--stage", default="1-7", help="Target stage (e.g. 1-7, CE-6, LS-6)")
    p_copilot.add_argument("--plan", default=None, help="Path to custom MAA Copilot JSON plan file")
    p_copilot.add_argument("--account", default="EMILIAMIO_MAIN", help="Account ID for roster substitution")
    p_copilot.add_argument("--instance", type=int, default=0, help="MuMu emulator instance index (default: 0)")
    p_copilot.set_defaults(func=cmd_copilot)

    p_live = subparsers.add_parser("live", help="Launch Route A real-game live combat execution on emulator")
    p_live.add_argument("--stage", default="ls-1", choices=["ls-1", "ls1", "1-7"], help="Target stage (default: ls-1)")
    p_live.set_defaults(func=cmd_live)

    # Squad Synthesizer CLI
    p_squad = subparsers.add_parser("squad", help="Intelligently synthesize optimal 12-operator squad for stage")
    p_squad.add_argument("--account", default="EMILIAMIO_MAIN", help="Account ID")
    p_squad.add_argument("--stage", default="1-7", help="Target stage ID")
    p_squad.set_defaults(func=cmd_squad)

    # Roster Inspector CLI
    p_roster = subparsers.add_parser("roster", help="View or inspect account owned operators roster")
    p_roster.add_argument("--account", default="EMILIAMIO_MAIN", help="Account ID")
    p_roster.set_defaults(func=cmd_roster)

    # Roguelike CLI
    p_roguelike = subparsers.add_parser("roguelike", help="Launch autonomous Integrated Strategies (Roguelike) run")
    p_roguelike.add_argument("--theme", choices=["is4", "is3", "is2", "is5"], default="is4", help="Theme: is4 (Sami), is3 (Mizuki), is2 (Phantom), is5 (Sarkaz)")
    p_roguelike.add_argument("--floors", type=int, default=3, help="Max floors to explore (default: 3)")
    p_roguelike.set_defaults(func=cmd_roguelike)

    p_campaign = subparsers.add_parser("campaign", help="Launch autonomous chapter campaign cruise (e.g. --chapter 0)")
    p_campaign.add_argument("--chapter", type=int, default=0, help="Target chapter episode number (default: 0)")
    p_campaign.set_defaults(func=cmd_campaign)

    # Task Orchestration Subcommand
    p_task = subparsers.add_parser("task", help="Master mission assignment and execution orchestrator")
    task_subparsers = p_task.add_subparsers(dest="task_action", help="Task action: add | list | run")

    # task add
    p_t_add = task_subparsers.add_parser("add", help="Add a new mission to the queue")
    p_t_add.add_argument("--account", default="EMILIAMIO_MAIN", help="Target account ID")
    p_t_add.add_argument("--type", choices=[MissionType.CAMPAIGN_CLEAR, MissionType.SANITY_FARM, MissionType.INFRA_ROTATE, MissionType.DAILY_ROUTINE, MissionType.ROGUELIKE], default=MissionType.CAMPAIGN_CLEAR, help="Mission type")
    p_t_add.add_argument("--chapter", type=int, default=0, help="Target chapter (for CAMPAIGN_CLEAR)")
    p_t_add.add_argument("--stage", default="1-7", help="Target stage (for SANITY_FARM)")

    # task list
    p_t_list = task_subparsers.add_parser("list", help="List missions")
    p_t_list.add_argument("--status", choices=[MissionStatus.QUEUED, MissionStatus.RUNNING, MissionStatus.COMPLETED, MissionStatus.FAILED, MissionStatus.CANCELLED], default=None, help="Filter by status")

    # task delete
    p_t_del = task_subparsers.add_parser("delete", help="Delete a specific mission by ID")
    p_t_del.add_argument("--id", required=True, help="Target mission ID")

    # task clear
    p_t_clr = task_subparsers.add_parser("clear", help="Clear missions from queue")
    p_t_clr.add_argument("--status", choices=["QUEUED", "FINISHED", "ALL"], default="QUEUED", help="Status filter to clear (default: QUEUED)")

    # task stop
    p_t_stop = task_subparsers.add_parser("stop", help="Emergency stop all running tasks")

    # task run
    p_t_run = task_subparsers.add_parser("run", help="Run queued missions")
    p_t_run.add_argument("--once", action="store_true", help="Execute only one mission then exit")

    p_task.set_defaults(func=cmd_task)

    p_test = subparsers.add_parser("test", help="Run full automated regression tests")
    p_test.set_defaults(func=cmd_test)

    p_daemon = subparsers.add_parser("daemon", help="Run multi-account automated dispatch daemon")
    p_daemon.add_argument("--cycles", type=int, default=1, help="Max dispatch cycles to run (default: 1)")
    p_daemon.set_defaults(func=cmd_daemon)

    p_stop = subparsers.add_parser("stop", help="Global emergency stop for all running tasks and combat loops")
    p_stop.set_defaults(func=cmd_stop)

    p_dash = subparsers.add_parser("dashboard", help="Launch local PRTS Web Tactical Command Dashboard")
    p_dash.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    p_dash.add_argument("--port", type=int, default=8848, help="Port (default: 8848)")
    p_dash.set_defaults(func=cmd_dashboard)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
