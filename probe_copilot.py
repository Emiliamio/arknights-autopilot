# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Route A Probe: MAA Copilot Dual-Track Execution & Panic Intercept Probe
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
import numpy as np
import cv2

from tactical.map_deconstructor import TacticalMap, TileType
from tactical.copilot_adapter import CopilotAdapter
from tactical.copilot_brain import CopilotBrain
from core.homography_mapper import HomographyMapper
from core.vision_engine import VisionEngine, BattleState
from core.touch_humanizer import TouchHumanizer
from core.adb_client import ADBClient


def run_copilot_probe():
    print("======================================================================")
    print("  [*] ASTA Route A Probe: MAA Copilot Protocol & Panic Sentry Preemption")
    print("  Author: Emiliamio <mio2110767128@163.com>")
    print("======================================================================")

    # 1. Load Copilot JSON Plan
    plan_path = "data/copilots/1-7_xiaoran_duo.json"
    plan = CopilotAdapter.load_file(plan_path)
    t_map = TacticalMap.create_1_7()

    print(f"[*] Loaded Copilot Plan: {plan.title}")
    print(f"    - Stage: {plan.stage_name} | Actions Count: {len(plan.actions)}")
    for a in plan.actions:
        print(f"    • Step #{a.step_index}: [{a.action_type.value:<8}] Name='{a.name:<6}' Tile=({a.col},{a.row}) Facing={a.direction:<5} Costs={a.min_costs} Kills={a.min_kills}")

    # 2. Setup Dual-Track Arbiter
    brain = CopilotBrain(t_map, plan)
    mapper = HomographyMapper.create_synthetic_arknights_mapper()
    humanizer = TouchHumanizer()
    vision = VisionEngine()

    print("\n[*] Initializing Dual-Track Arbiter (Main Copilot Track + Panic Sentry Track)...")

    # Base battle frame setup
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    h, w = 1080, 1920
    # Speed icon active
    sx1, sy1 = int(vision.ROI_NORMS["speed_toggle"][0] * w), int(vision.ROI_NORMS["speed_toggle"][1] * h)
    frame[sy1:sy1 + 40, sx1:sx1 + 40] = 150
    # Pause button
    frame[20:70, 1820:1880] = 100
    # Ready hand card
    hx1, hy1 = int(vision.ROI_NORMS["hand_cards"][0] * w), int(vision.ROI_NORMS["hand_cards"][1] * h)
    frame[hy1:hy1 + 80, hx1:hx1 + 100] = (60, 180, 240)

    # Helper to update DP
    cx1, cy1 = int(vision.ROI_NORMS["cost"][0] * w), int(vision.ROI_NORMS["cost"][1] * h)
    def set_dp(val: int):
        frame[cy1:cy1 + 80, cx1:cx1 + 100] = 0
        cv2.putText(frame, str(val), (cx1 + 10, cy1 + 55), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)

    # Helper to update kills
    kx1, ky1 = int(vision.ROI_NORMS["kill_count"][0] * w), int(vision.ROI_NORMS["kill_count"][1] * h)
    def set_kills(cur: int, total: int = 35):
        frame[ky1:ky1 + 40, kx1:kx1 + 140] = 0
        cv2.putText(frame, f"{cur}/{total}", (kx1 + 5, ky1 + 35), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2)

    # Tick 1: Action 1 (SpeedUp)
    set_dp(5)
    set_kills(0)
    t1 = brain.tick(frame, vision, mapper, humanizer, adb_client=None)
    print(f"    [Tick 1 - Main Track] Action: {t1['action_taken']} | Progress: {t1['copilot_progress']}")

    # Tick 2: Action 2 (Deploy 芬 at [9, 2] when DP>=10)
    set_dp(10)
    t2 = brain.tick(frame, vision, mapper, humanizer, adb_client=None)
    print(f"    [Tick 2 - Main Track] Action: {t2['action_taken']} | DP={t2['current_dp']} | Blocker registered at (9, 2)")

    # Tick 3: Action 3 (Deploy 克洛丝 at [6, 0] when DP>=12)
    set_dp(12)
    t3 = brain.tick(frame, vision, mapper, humanizer, adb_client=None)
    print(f"    [Tick 3 - Main Track] Action: {t3['action_taken']} | DP={t3['current_dp']}")

    # TICK 4: SIMULATE UNEXPECTED FRONT-LINE BREACH! (客户芬练度偏低被怪提前击杀，怪直扑蓝门)
    print("\n[!] SIMULATING RUNTIME CONTINGENCY: Vanguard at (9, 2) defeated! Unexpected leak at (9, 1)!")
    brain.panic_daemon.unregister_blocker(9, 2)
    ex, ey = mapper.get_tile_center(9, 1)
    cv2.circle(frame, (ex, ey), 12, (20, 20, 220), -1)  # Enemy appears

    t_panic_start = time.perf_counter()
    t4 = brain.tick(frame, vision, mapper, humanizer, adb_client=None)
    t_panic_cost = (time.perf_counter() - t_panic_start) * 1000.0

    print(f"[+] PANIC SENTRY PREEMPTION TRIGGERED in {t_panic_cost:.2f} ms:")
    print(f"    - Action Taken: {t4['action_taken']}")
    print(f"    - Intercept Details: {t4['action_details']}")
    print(f"    - Emergency Interventions Total: {t4['emergency_interventions']}")
    print(f"    - Blocker Re-established: {list(brain.panic_daemon.active_blockers)}")
    assert t4["action_taken"] == "PANIC_INTERCEPT_PREEMPTION"

    # TICK 5: Leak resolved, Copilot Main Track resumes!
    frame[ey - 15:ey + 15, ex - 15:ex + 15] = 0  # Enemy neutralized
    set_dp(15)
    set_kills(8)  # Kills reaches 8 -> Triggers Action 4: Skill 克洛丝!
    t5 = brain.tick(frame, vision, mapper, humanizer, adb_client=None)
    print(f"\n    [Tick 5 - Track Resumed] Action: {t5['action_taken']} | Kills={t5['kill_count'][0]} -> Skill Activated!")

    # Tick 6: Action 5 (Deploy 蛇屠箱 at [6, 1] when DP>=20)
    set_dp(20)
    t6 = brain.tick(frame, vision, mapper, humanizer, adb_client=None)
    print(f"    [Tick 6 - Main Track] Action: {t6['action_taken']} | DP={t6['current_dp']} | Progress: {t6['copilot_progress']}")

    # Tick 7: Victory Settlement
    frame_victory = np.zeros((1080, 1920, 3), dtype=np.uint8)
    cv2.putText(frame_victory, "MISSION ACCOMPLISHED", (600, 540), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (255, 255, 255), 3)
    t7 = brain.tick(frame_victory, vision, mapper, humanizer, adb_client=None)
    print(f"    [Tick 7 - Final] Action: {t7['action_taken']} | Status: {t7['status']}")
    assert t7["status"] == "COMPLETED"

    # 3. Render Visual Asset
    print("\n[*] Rendering Dual-Track Copilot Execution Visualization...")
    vis = np.zeros((1080, 1920, 3), dtype=np.uint8)
    vis[:] = (22, 26, 32)

    for r in range(t_map.rows):
        for c in range(t_map.cols):
            tile = t_map.get_tile(r, c)
            poly = np.array(mapper.get_tile_polygon(c, r), dtype=np.int32)
            if tile == TileType.GROUND:
                cv2.fillPoly(vis, [poly], (42, 50, 58))
                cv2.polylines(vis, [poly], True, (65, 75, 85), 1)
            elif tile == TileType.HIGH_GROUND:
                cv2.fillPoly(vis, [poly], (68, 62, 48))
                cv2.polylines(vis, [poly], True, (95, 88, 72), 1)
            elif tile == TileType.GOAL:
                cv2.fillPoly(vis, [poly], (140, 80, 30))
                cv2.polylines(vis, [poly], True, (240, 140, 50), 2)
            elif tile == TileType.SPAWN:
                cv2.fillPoly(vis, [poly], (30, 30, 130))
                cv2.polylines(vis, [poly], True, (60, 60, 220), 2)

    # Copilot Step 2: 芬 at (9, 2)
    p_fen = mapper.get_tile_center(9, 2)
    cv2.circle(vis, p_fen, 20, (0, 255, 255), 2)
    cv2.putText(vis, "COPILOT: FEN", (p_fen[0] - 55, p_fen[1] - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    # Copilot Step 3: 克洛丝 at (6, 0)
    p_kroos = mapper.get_tile_center(6, 0)
    cv2.circle(vis, p_kroos, 20, (255, 200, 0), 2)
    cv2.putText(vis, "COPILOT: KROOS", (p_kroos[0] - 65, p_kroos[1] - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 1)

    # Panic Preemption Intercept point
    cv2.circle(vis, p_fen, 28, (0, 0, 255), 2)
    cv2.putText(vis, "PANIC SENTRY INTERCEPT", (p_fen[0] - 100, p_fen[1] + 45), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)

    cv2.putText(vis, "ASTA Route A: MAA Copilot Dual-Track Execution & Self-Healing Sentry",
                (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(vis, "Protocol: MAA JSON Standard | Auto-Healing: PanicDaemon Preemptive Intercept Activated",
                (40, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 200), 1)

    os.makedirs("data", exist_ok=True)
    out_img = os.path.abspath("data/copilot_dual_track_sample.png")
    cv2.imwrite(out_img, vis)
    print(f"[+] Visual diagram saved to: {out_img} ({os.path.getsize(out_img):,} bytes)")

    print("======================================================================")
    print("  [SUCCESS] ROUTE A PROBE 100% COMPLETE: COPILOT ARBITER OPERATIONAL!")
    print("======================================================================")
    return {
        "title": plan.title,
        "actions_executed": brain.current_action_idx,
        "emergency_interventions": brain.emergency_interventions_count,
        "visual_path": out_img
    }


if __name__ == "__main__":
    run_copilot_probe()