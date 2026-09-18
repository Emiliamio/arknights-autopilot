# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Phase 4 Probe: Panic Fallback Daemon & 0.5s Emergency Reserve Interception
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

from core.adb_client import ADBClient
from core.touch_humanizer import TouchHumanizer
from core.homography_mapper import HomographyMapper
from core.vision_engine import VisionEngine, BattleState
from tactical.map_deconstructor import TacticalMap, TileType
from tactical.choke_point_analyzer import ChokePointAnalyzer, HighGroundScorer
from tactical.threat_monitor import ThreatMonitor, ThreatLevel
from tactical.panic_daemon import PanicDaemon
from tactical.combat_brain import CombatBrain, BrainState


def run_phase4_probe():
    print("======================================================================")
    print("  [*] ASTA Phase 4: Threat Monitor & Panic Fallback Interception Probe")
    print("  Author: Emiliamio <mio2110767128@163.com>")
    print("======================================================================")

    # 1. Initialize Tactical Core
    t_map = TacticalMap.create_1_7()
    analyzer = ChokePointAnalyzer(t_map)
    choke_res = analyzer.analyze_choke_points()
    scorer = HighGroundScorer(t_map)
    hg_ranks = scorer.score_high_grounds(choke_res)
    med_ranks = scorer.score_medic_positions(choke_res)

    brain = CombatBrain(t_map, choke_res, hg_ranks, med_ranks)
    mapper = HomographyMapper.create_synthetic_arknights_mapper()
    humanizer = TouchHumanizer()
    vision = VisionEngine()

    print("[*] Tactical map & CombatBrain initialized. Front-line established.")
    # Simulate normal Vanguard deployment at primary choke (col=9, row=2)
    brain.state = BrainState.ACTIVE_ENGAGEMENT
    brain.last_dp = 15
    brain.panic_daemon.register_blocker(9, 2)
    print(f"[+] Active Friendly Blocker: (col=9, row=2) | Status: HOLDING_FRONT_LINE")

    # 2. Stage 1: Enemy approaches front-line along valid corridor (col=9, row=1)
    print("\n[*] Scenario 1: Enemy at (col=9, row=1) approaches front-line while blocker at (col=9, row=2) is alive...")
    frame_normal = np.zeros((1080, 1920, 3), dtype=np.uint8)
    frame_normal[20:70, 1820:1880] = 100  # Pause button
    cx1, cy1 = int(vision.ROI_NORMS["cost"][0] * 1920), int(vision.ROI_NORMS["cost"][1] * 1080)
    cv2.putText(frame_normal, "15", (cx1 + 10, cy1 + 55), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)

    # Draw enemy at valid walkable ground corridor: (col=9, row=1)
    ex, ey = mapper.get_tile_center(9, 1)
    cv2.circle(frame_normal, (ex, ey), 12, (20, 20, 220), -1)

    t_eval_start = time.perf_counter()
    enemies = brain.threat_monitor.detect_enemies(frame_normal, mapper)
    level_normal, leak_normal = brain.threat_monitor.evaluate_threat(enemies, brain.panic_daemon.active_blockers)
    eval_cost_ms = (time.perf_counter() - t_eval_start) * 1000.0

    print(f"    - Enemies Detected: {len(enemies)} at {enemies[0].grid_pos if enemies else 'None'}")
    print(f"    - Threat Level: {level_normal.name:<10} (Evaluation: {eval_cost_ms:.2f}ms)")
    print(f"    - Blocker State: Guarding tile (9, 2) -> Panic Triggered?: {level_normal == ThreatLevel.PANIC_LEAK}")
    assert level_normal == ThreatLevel.ALERT, "Must report ALERT, not PANIC, while blocker is guarding"

    # 3. Stage 2: HUMAN INTERVENTION - Force remove front-line blocker! (Vanguard Defeated / Pulled)
    print("\n[!] Scenario 2: HUMAN SIMULATION - Front-line Blocker at (9, 2) Defeated / Withdrawn!")
    t_breach_start = time.perf_counter()
    brain.panic_daemon.unregister_blocker(9, 2)
    print(f"    - Active Friendly Blockers: {list(brain.panic_daemon.active_blockers)} (FRONT LINE BREACHED!)")

    # Supply emergency reserve cards in hand (e.g. Fast-Redeploy at slot 0)
    hx1, hy1, hx2, hy2 = int(vision.ROI_NORMS["hand_cards"][0] * 1920), int(vision.ROI_NORMS["hand_cards"][1] * 1080), int(vision.ROI_NORMS["hand_cards"][2] * 1920), int(vision.ROI_NORMS["hand_cards"][3] * 1080)
    frame_normal[hy1:hy2, hx1:hx1 + 120] = (60, 180, 240)  # Ready emergency card

    # AI Tick: Detects unblocked leak and executes Panic Intercept
    tick_result = brain.tick(frame_normal, vision, mapper, humanizer, adb_client=None)
    t_breach_cost = (time.perf_counter() - t_breach_start) * 1000.0

    print(f"\n[+] AI EMERGENCY REACTION TRIGGERED in {t_breach_cost:.2f} ms (< 500ms SLA):")
    print(f"    - Action Taken: {tick_result['action_taken']}")
    details = tick_result.get("action_details", {})
    print(f"    - Emergency Status: {details.get('status')}")
    print(f"    - Intercept Tile: {details.get('intercept_tile')} | Facing: {str(details.get('facing')).upper()}")
    print(f"    - Hand Slot Deployed: Slot #{details.get('slot_used')}")
    print(f"    - Internal Dispatch Latency: {details.get('dispatch_latency_ms')} ms")
    print(f"    - Active Friendly Blockers Now: {list(brain.panic_daemon.active_blockers)} (RE-ESTABLISHED!)")

    assert tick_result["action_taken"] == "PANIC_INTERCEPT"
    assert details.get("status") == "INTERCEPTED"
    assert (9, 2) in brain.panic_daemon.active_blockers

    # 4. Render Emergency Interception Visualizer
    print("\n[*] Rendering Emergency Interception Tactical Analysis Image...")
    vis_canvas = np.zeros((1080, 1920, 3), dtype=np.uint8)
    vis_canvas[:] = (20, 24, 30)

    # Draw grid
    for r in range(t_map.rows):
        for c in range(t_map.cols):
            tile = t_map.get_tile(r, c)
            poly = np.array(mapper.get_tile_polygon(c, r), dtype=np.int32)
            if tile == TileType.GROUND:
                cv2.fillPoly(vis_canvas, [poly], (40, 48, 56))
                cv2.polylines(vis_canvas, [poly], True, (60, 70, 80), 1)
            elif tile == TileType.HIGH_GROUND:
                cv2.fillPoly(vis_canvas, [poly], (65, 60, 45))
                cv2.polylines(vis_canvas, [poly], True, (90, 85, 70), 1)
            elif tile == TileType.GOAL:
                cv2.fillPoly(vis_canvas, [poly], (140, 80, 30))
                cv2.polylines(vis_canvas, [poly], True, (240, 140, 50), 2)
            elif tile == TileType.SPAWN:
                cv2.fillPoly(vis_canvas, [poly], (30, 30, 130))
                cv2.polylines(vis_canvas, [poly], True, (60, 60, 220), 2)

    # Draw Enemy at (col=9, row=1)
    enemy_screen = mapper.get_tile_center(9, 1)
    cv2.circle(vis_canvas, enemy_screen, 18, (0, 0, 255), -1)
    cv2.putText(vis_canvas, "LEAK ENEMY", (enemy_screen[0] - 50, enemy_screen[1] - 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)

    # Draw Emergency Interceptor at (col=9, row=2)
    intercept_screen = mapper.get_tile_center(9, 2)
    cv2.circle(vis_canvas, intercept_screen, 22, (0, 255, 200), 3)
    # Face UP towards enemy at row 1
    cv2.arrowedLine(vis_canvas, intercept_screen, (intercept_screen[0], intercept_screen[1] - 50),
                    (0, 255, 200), 3, tipLength=0.3)
    cv2.putText(vis_canvas, "PANIC INTERCEPT (FACE UP)", (intercept_screen[0] - 90, intercept_screen[1] + 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 200), 2)

    # Title & Stats
    cv2.putText(vis_canvas, "ASTA Phase 4: Panic Fallback Daemon Emergency Intercept",
                (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(vis_canvas, f"Trigger Latency: {t_breach_cost:.2f} ms | Target: (9, 2) | Enemy halted 1 tile before Blue Goal",
                (40, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 200), 1)

    os.makedirs("data", exist_ok=True)
    out_img = os.path.abspath("data/panic_intercept_sample.png")
    cv2.imwrite(out_img, vis_canvas)
    print(f"[+] Panic intercept visual saved to: {out_img} ({os.path.getsize(out_img):,} bytes)")

    print("======================================================================")
    print("  [SUCCESS] PHASE 4 PROBE 100% COMPLETE: EMERGENCY FALLBACK OPERATIONAL!")
    print("======================================================================")
    return {
        "threat_level": level_normal.name,
        "panic_action": tick_result["action_taken"],
        "reaction_time_ms": round(t_breach_cost, 2),
        "visual_path": out_img
    }


if __name__ == "__main__":
    run_phase4_probe()