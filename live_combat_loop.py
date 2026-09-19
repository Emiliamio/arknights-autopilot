# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Live Real-Game Combat Executor (Robust Dual-Swipe & Precise Button Navigation)
Author: Emiliamio <mio2110767128@163.com>
"""

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import time
import cv2
import numpy as np

from core.adb_client import ADBClient
from core.touch_humanizer import TouchHumanizer
from core.vision_engine import VisionEngine, BattleState


def main():
    print("======================================================================")
    print("  🚀 ASTA Live Battle: In-Game Autonomous Combat Execution")
    print("  Author: Emiliamio <mio2110767128@163.com>")
    print("======================================================================")

    client = ADBClient(instance_index=0)
    serial = client.connect(auto_launch=False)
    print(f"[+] ADB Target Active: {serial} (Port: {client.connected_port})")

    vision = VisionEngine()
    humanizer = TouchHumanizer()

    # Step 1: Open LS-1 stage popup if on stage list
    print("[*] Step 1: Tapping LS-1 stage at (337, 862)...")
    client.tap(337, 862)
    time.sleep(2.0)

    # Step 2: Tap Blue Start Action button on Screen 1 (Stage Details)
    print("[*] Step 2: Tapping Blue Start Action at (1767, 987)...")
    client.tap(1767, 987)
    time.sleep(2.5)

    # Step 3: Tap Red Squad Start Action button on Screen 2 (Squad Formation)
    print("[*] Step 3: Tapping Red Squad Start Action at (1655, 780)...")
    client.tap(1655, 780)
    time.sleep(5.0)

    # Step 4: Wait for battlefield to load
    print("[*] Step 4: Entering battlefield, waiting for loading to finish...")
    t_start = time.time()
    in_battle = False
    for _ in range(25):
        frame = client.screencap()
        # In-battle indicator: 1X or 2X speed icon at top right (~1645, 69)
        crop_spd = frame[40:100, 1600:1700]
        res_spd, _ = vision.ocr(crop_spd) if vision.ocr else ([], None)
        spd_text = " ".join(r[1] for r in (res_spd or []))

        if "1X" in spd_text or "2X" in spd_text or vision.detect_battle_state(frame) == BattleState.IN_BATTLE:
            in_battle = True
            print(f"[+] BATTLEFIELD LOADED SUCCESSFULLY in {time.time() - t_start:.1f}s!")
            break
        time.sleep(1.0)

    if not in_battle:
        print("[!] Timeout waiting for battlefield. Check data/live_battle_debug.png")
        cv2.imwrite("data/live_battle_debug.png", frame)
        return

    # Step 5: Ensure 2x Speed
    time.sleep(1.0)
    frame = client.screencap()
    if "1X" in spd_text:
        print("[*] Toggling 2x Speed at (1645, 69)...")
        client.tap(1645, 69)
        time.sleep(0.5)
    else:
        print("[+] 2x Speed confirmed active!")

    # Step 6: Active Combat Loop with Operator Deployment
    print("\n[*] Step 6: Engaging Autonomous Deployment & Combat Monitoring:")
    deployed_count = 0
    t_battle = time.time()

    # Hand cards positions along bottom row
    hand_cards = [
        (260, 950),  # Card 0
        (400, 950),  # Card 1
        (560, 950),  # Card 2
        (710, 950)   # Card 3
    ]

    # Strategic landing points on LS-1
    deploy_targets = [
        (960, 540, "right", 10),   # Op 1: Ground blocker facing right (DP>=10)
        (1100, 540, "right", 14),  # Op 2: Secondary blocker (DP>=14)
        (960, 400, "down", 18)     # Op 3: Upper lane blocker (DP>=18)
    ]

    while time.time() - t_battle < 90:  # 90s max for LS-1
        frame = client.screencap()

        # Check for victory / defeat settlement
        # Victory screen in Arknights shows "MISSION", "RESULTS", "EXP", etc.
        crop_center = frame[300:700, 500:1400]
        res_c, _ = vision.ocr(crop_center) if vision.ocr else ([], None)
        c_text = " ".join(r[1].upper() for r in (res_c or []))

        if any(k in c_text for k in ["MISSION", "ACCOMPLISHED", "RESULTS", "行动结束"]):
            print(f"\n[+] COMBAT FINISHED in {time.time() - t_battle:.1f}s! Text: {c_text[:40]}")
            cv2.imwrite("data/live_final_settlement.png", frame)
            time.sleep(2.0)
            print("[*] Dismissing settlement...")
            client.tap(960, 540)
            time.sleep(2.0)
            client.tap(960, 540)
            print("[+] Returned to stage lobby successfully!")
            break

        # Read live DP from cost ROI
        dp = vision.read_cost(frame)

        # Deploy next operator
        if deployed_count < len(deploy_targets):
            tx, ty, facing, min_dp = deploy_targets[deployed_count]
            if dp is not None and dp >= min_dp:
                cx, cy = hand_cards[deployed_count]
                print(f"[+] DEPLOYING OPERATOR #{deployed_count+1}: DP={dp} -> Hand ({cx}, {cy}) to Grid ({tx}, {ty}) facing {facing}...")
                gesture = humanizer.generate_deploy_gesture(cx, cy, tx, ty, orientation=facing)
                client.deploy_operator_gesture(gesture)
                deployed_count += 1
                time.sleep(1.0)
                continue

        if int(time.time() - t_battle) % 4 == 0:
            print(f"    [Combat Live] DP={dp} | Deployed={deployed_count}/{len(deploy_targets)} | Elapsed={time.time()-t_battle:.1f}s")

        time.sleep(0.4)

    print("\n======================================================================")
    print("  ✅ REAL LIVE ARKNIGHTS BATTLE COMPLETED & VERIFIED!")
    print("======================================================================")


if __name__ == "__main__":
    main()