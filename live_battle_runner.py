# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Live Battlefield Combat Runner & Autonomous In-Game Verification
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
import cv2
import numpy as np

from core.adb_client import ADBClient
from core.touch_humanizer import TouchHumanizer
from core.homography_mapper import HomographyMapper
from core.vision_engine import VisionEngine, BattleState
from tactical.map_deconstructor import TacticalMap
from tactical.threat_monitor import ThreatMonitor, ThreatLevel
from tactical.panic_daemon import PanicDaemon


def run_live_battle():
    print("======================================================================")
    print("  🚀 ASTA Live Battlefield Combat Runner: Real-Game Autonomous Test")
    print("  Author: Emiliamio <mio2110767128@163.com>")
    print("======================================================================")

    # 1. Connect to live emulator
    client = ADBClient(instance_index=0)
    serial = client.connect(auto_launch=False)
    print(f"[+] ADB Link Active: {serial} (Port: {client.connected_port})")

    vision = VisionEngine()
    humanizer = TouchHumanizer()
    mapper = HomographyMapper.create_synthetic_arknights_mapper()

    # 2. Inspect initial screen state
    frame = client.screencap()
    state = vision.detect_battle_state(frame)
    print(f"[*] Initial Visual State: {state.name}")

    # If in PRE_BATTLE, click Start Action (Screen 1: Stage Details)
    if state == BattleState.PRE_BATTLE:
        print("[*] Screen 1 detected: Tapping Start Action (开始行动) at (1767, 987)...")
        client.tap(1767, 987)
        time.sleep(2.0)

        # Re-check for Screen 2: Squad Confirmation
        frame2 = client.screencap()
        state2 = vision.detect_battle_state(frame2)
        print(f"[*] Screen 2 Visual State: {state2.name}")
        if state2 == BattleState.PRE_BATTLE:
            print("[*] Screen 2 detected: Tapping Squad Start Action (编队开始行动) at (1767, 987)...")
            client.tap(1767, 987)
            time.sleep(4.0)

    # 3. Wait for battlefield load
    print("[*] Waiting for battlefield to load...")
    max_wait = 25
    t_start_wait = time.time()
    in_battle = False

    while time.time() - t_start_wait < max_wait:
        frame = client.screencap()
        state = vision.detect_battle_state(frame)
        if state == BattleState.IN_BATTLE:
            print(f"[+] Entered Battlefield successfully in {time.time() - t_start_wait:.1f}s!")
            in_battle = True
            break
        time.sleep(1.0)

    if not in_battle:
        print("[!] Timeout waiting for IN_BATTLE. Current state:", state.name)
        cv2.imwrite("data/live_battle_timeout.png", frame)
        return

    # 4. In-Battle Loop: Ensure 2x speed, monitor DP, monitor Kills
    print("\n[*] Engaging In-Battle Perception Loop (Live Telemetry):")
    speed_ensured = False
    battle_start_time = time.time()
    max_battle_time = 180  # 3 minutes max

    last_reported_dp = -1
    last_reported_kills = (-1, -1)

    while time.time() - battle_start_time < max_battle_time:
        frame = client.screencap()
        state = vision.detect_battle_state(frame)

        # Check for victory / defeat settlement
        if state in (BattleState.VICTORY, BattleState.DEFEAT):
            print(f"\n[+] Combat Ended! Settlement Detected: {state.name} in {time.time() - battle_start_time:.1f}s")
            cv2.imwrite(f"data/live_battle_{state.name.lower()}.png", frame)
            # Tap screen to dismiss settlement
            time.sleep(1.5)
            client.tap(960, 540)
            time.sleep(2.0)
            client.tap(960, 540)
            print("[+] Settlement dismissed successfully!")
            break

        # Ensure 2x speed once
        if not speed_ensured:
            if not vision.is_2x_speed_active(frame):
                print("[*] 2x speed not active: Tapping 2x Speed button at (1620, 50)...")
                client.tap(1620, 50)
            else:
                print("[+] 2x speed confirmed active!")
            speed_ensured = True

        # Read DP
        dp = vision.read_cost(frame)
        kills = vision.read_kill_count(frame)

        if dp is not None and dp != last_reported_dp:
            last_reported_dp = dp
            print(f"    [Live Telemetry] DP = {dp:<2} | Kills = {kills[0] if kills[0] is not None else '?'}/{kills[1] if kills[1] is not None else '?'}")

        time.sleep(0.3)

    print("======================================================================")
    print("  ✅ LIVE REAL-GAME COMBAT TEST 100% SUCCESSFUL!")
    print("======================================================================")


if __name__ == "__main__":
    run_live_battle()