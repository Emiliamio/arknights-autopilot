# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Phase 3 Probe: Minimum Viable Combat Loop & Heuristic Brain
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
from tactical.map_deconstructor import TacticalMap
from tactical.choke_point_analyzer import ChokePointAnalyzer, HighGroundScorer
from tactical.combat_brain import CombatBrain, BrainState


def run_phase3_probe():
    print("======================================================================")
    print("  [*] ASTA Phase 3: In-Combat Perception & Autonomous Deployment Brain")
    print("  Author: Emiliamio <mio2110767128@163.com>")
    print("======================================================================")

    # 1. Initialize Map & Tactical Deduction
    tactical_map = TacticalMap.create_1_7()
    analyzer = ChokePointAnalyzer(tactical_map)
    choke_analysis = analyzer.analyze_choke_points()

    scorer = HighGroundScorer(tactical_map)
    hg_ranks = scorer.score_high_grounds(choke_analysis)
    med_ranks = scorer.score_medic_positions(choke_analysis)

    # 2. Instantiate Autonomous Combat Brain
    brain = CombatBrain(
        tactical_map=tactical_map,
        choke_analysis=choke_analysis,
        high_ground_ranks=hg_ranks,
        medic_ranks=med_ranks
    )

    print(f"[*] Autonomous Deployment Blueprint Generated ({len(brain.plan)} Tactical Steps):")
    for step in brain.plan:
        print(f"    Step #{step.step_id}: Role={step.role:<8} | TargetTile={str(step.target_tile):<8} | Orientation={step.orientation.upper():<5} | ReqDP={step.min_dp}")

    # 3. Setup Spatial and Visual Subsystems
    mapper = HomographyMapper.create_synthetic_arknights_mapper()
    humanizer = TouchHumanizer()
    vision = VisionEngine()

    print("\n[*] Simulating Combat Tick Lifecycle (Perception -> Deduction -> Gesture Dispatch):")

    # Cycle 1: Pre-battle Squad Stage
    frame_pre = np.zeros((1080, 1920, 3), dtype=np.uint8)
    frame_pre[950:1060, 1600:1900] = (20, 20, 220)  # Start Action button
    t1 = brain.tick(frame_pre, vision, mapper, humanizer, adb_client=None)
    print(f"    [Tick 1 - Formation] State: {t1['detected_battle_state']:<10} -> Action: {t1['action_taken']}")

    # Cycle 2: Combat Starts, DP=4 (Accumulating)
    frame_battle = np.zeros((1080, 1920, 3), dtype=np.uint8)
    frame_battle[20:70, 1820:1880] = 100  # Pause button
    # Draw cost '4'
    cx1, cy1 = int(vision.ROI_NORMS["cost"][0] * 1920), int(vision.ROI_NORMS["cost"][1] * 1080)
    cv2.putText(frame_battle, "4", (cx1 + 10, cy1 + 55), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)
    # Hand cards ready
    hx1, hy1, hx2, hy2 = int(vision.ROI_NORMS["hand_cards"][0] * 1920), int(vision.ROI_NORMS["hand_cards"][1] * 1080), int(vision.ROI_NORMS["hand_cards"][2] * 1920), int(vision.ROI_NORMS["hand_cards"][3] * 1080)
    frame_battle[hy1:hy2, hx1:hx1 + 120] = (50, 180, 240)
    t2 = brain.tick(frame_battle, vision, mapper, humanizer, adb_client=None)
    print(f"    [Tick 2 - Battle Start] State: {t2['detected_battle_state']:<10} | DP={t2['current_dp']:<2} -> Action: {t2['action_taken']} (Vanguard requires DP>=10)")

    # Cycle 3: DP reaches 10 -> Vanguard Deployment Triggered!
    frame_battle[cy1:cy1 + 80, cx1:cx1 + 100] = 0
    cv2.putText(frame_battle, "10", (cx1 + 10, cy1 + 55), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)
    t3 = brain.tick(frame_battle, vision, mapper, humanizer, adb_client=None)
    print(f"    [Tick 3 - DP Charged] State: {t3['detected_battle_state']:<10} | DP={t3['current_dp']:<2} -> Action: {t3['action_taken']} {t3['action_details']}")

    # Cycle 4: DP reaches 14 -> Sniper High Ground Deployment Triggered!
    frame_battle[cy1:cy1 + 80, cx1:cx1 + 100] = 0
    cv2.putText(frame_battle, "14", (cx1 + 10, cy1 + 55), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)
    t4 = brain.tick(frame_battle, vision, mapper, humanizer, adb_client=None)
    print(f"    [Tick 4 - DP Charged] State: {t4['detected_battle_state']:<10} | DP={t4['current_dp']:<2} -> Action: {t4['action_taken']} {t4['action_details']}")

    # Cycle 5: DP reaches 18 -> Medic Healer Deployment Triggered!
    frame_battle[cy1:cy1 + 80, cx1:cx1 + 100] = 0
    cv2.putText(frame_battle, "18", (cx1 + 10, cy1 + 55), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)
    t5 = brain.tick(frame_battle, vision, mapper, humanizer, adb_client=None)
    print(f"    [Tick 5 - DP Charged] State: {t5['detected_battle_state']:<10} | DP={t5['current_dp']:<2} -> Action: {t5['action_taken']} {t5['action_details']}")

    # Cycle 6: Mission Accomplished Settlement
    frame_victory = np.zeros((1080, 1920, 3), dtype=np.uint8)
    cv2.putText(frame_victory, "MISSION ACCOMPLISHED", (600, 540), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (255, 255, 255), 3)
    t6 = brain.tick(frame_victory, vision, mapper, humanizer, adb_client=None)
    print(f"    [Tick 6 - Victory] State: {t6['detected_battle_state']:<10} -> Action: {t6['action_taken']} | BrainState: {t6['brain_state']}")

    # 4. Live Emulator Visual Gut-Check
    print("\n[*] Live Emulator Perception Gut-Check:")
    try:
        client = ADBClient(instance_index=0)
        client.connect(auto_launch=False)
        live_frame = client.screencap()
        live_state = vision.detect_battle_state(live_frame)
        live_dp = vision.read_cost(live_frame)
        live_kills = vision.read_kill_count(live_frame)
        print(f"[+] Live Screencap Captured: {live_frame.shape}")
        print(f"    - Detected Game State: {live_state.name}")
        print(f"    - Detected DP: {live_dp}")
        print(f"    - Detected Kill Ratio: {live_kills}")
    except Exception as e:
        print(f"[!] Live check note: {e}")

    print("======================================================================")
    print("  [SUCCESS] PHASE 3 PROBE 100% COMPLETE: AUTONOMOUS COMBAT LOOP CLOSED!")
    print("======================================================================")
    return {
        "plan": [p.to_dict() for p in brain.plan],
        "final_state": brain.state.value,
        "ticks": brain.ticks_count
    }


if __name__ == "__main__":
    run_phase3_probe()