from core.abort_controller import AbortController
# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Universal Adaptive Combat Pilot & Generic Battle Loop
Author: Emiliamio <mio2110767128@163.com>
"""

import time
import logging
from typing import Dict, Any, Optional, List
import numpy as np

from core.adb_client import ADBClient
from core.vision_engine import VisionEngine, BattleState
from core.touch_humanizer import TouchHumanizer
from core.homography_mapper import HomographyMapper
from tactical.threat_monitor import ThreatMonitor, ThreatLevel
from tactical.panic_daemon import PanicDaemon

logger = logging.getLogger("ASTA.UniversalCombatPilot")


class UniversalCombatPilot:
    """
    Autonomous battle runner that operates on any normal Arknights stage:
    1. Locks 2x combat speed.
    2. Monitors real-time DP and hand card readiness.
    3. Executes golden tactical deployment sequence (Vanguard ➔ DPS ➔ Tank ➔ Medic).
    4. Sentry Panic Daemon intercepts leaks in real-time.
    5. Handles victory/defeat settlement dismissal.
    """

    def __init__(
        self,
        adb_client: Optional[ADBClient] = None,
        vision_engine: Optional[VisionEngine] = None,
        humanizer: Optional[TouchHumanizer] = None,
        mapper: Optional[HomographyMapper] = None
    ):
        self.client = adb_client or ADBClient(instance_index=0)
        self.vision = vision_engine or VisionEngine()
        self.humanizer = humanizer or TouchHumanizer()
        self.mapper = mapper or HomographyMapper.create_synthetic_arknights_mapper()
        self.threat_monitor = ThreatMonitor()
        self.panic_daemon = PanicDaemon()

    def run_combat(self, max_duration_sec: int = 180) -> Dict[str, Any]:
        """Runs autonomous combat loop until victory or timeout."""
        logger.info("[*] Universal Combat Pilot engaged on battlefield...")
        t_start = time.time()
        speed_ensured = False

        # Tactical landing goals (generic relative coordinates)
        # 1. Primary ground blocker center (e.g. 960, 540 facing RIGHT, DP>=10)
        # 2. Secondary ground blocker (e.g. 1100, 540 facing RIGHT, DP>=14)
        # 3. High ground DPS (e.g. 960, 380 facing DOWN, DP>=18)
        # 4. High ground Medic (e.g. 800, 380 facing RIGHT, DP>=24)
        tactical_steps = [
            {"target": (960, 540), "orientation": "right", "min_dp": 10, "name": "Vanguard/Melee"},
            {"target": (1100, 540), "orientation": "right", "min_dp": 14, "name": "Guard/Blocker"},
            {"target": (960, 380), "orientation": "down", "min_dp": 18, "name": "Sniper/Ranged"},
            {"target": (800, 380), "orientation": "right", "min_dp": 24, "name": "Medic/Support"}
        ]
        deployed_idx = 0

        while time.time() - t_start < max_duration_sec:
            if AbortController.is_aborted():
                logger.warning("🛑 [UniversalCombatPilot] Emergency stop signal detected. Ceasing battle execution...")
                return {"result": "ABORTED", "elapsed_sec": time.time() - t_start, "deployed_count": deployed_idx}
            frame = self.client.screencap()
            if frame is None or frame.size == 0:
                time.sleep(0.5)
                continue

            state = self.vision.detect_battle_state(frame)

            # 1. Settlement check
            if state in (BattleState.VICTORY, BattleState.DEFEAT):
                elapsed = time.time() - t_start
                logger.info(f"[+] Combat settled: {state.name} in {elapsed:.1f}s!")
                self._dismiss_settlement()
                return {
                    "result": state.name,
                    "elapsed_sec": elapsed,
                    "deployed_count": deployed_idx
                }

            # 2. Speed check
            if not speed_ensured:
                if not self.vision.is_2x_speed_active(frame):
                    logger.info("[*] Toggling 2x speed at (1645, 69)...")
                    self.client.tap(1645, 69)
                speed_ensured = True

            # 3. Threat & Panic Leak Sentry
            enemies = self.threat_monitor.detect_enemies(frame, self.mapper)
            threat_lvl, leak_info = self.threat_monitor.evaluate_threat(
                enemies, self.panic_daemon.active_blockers
            )
            if threat_lvl == ThreatLevel.PANIC_LEAK and leak_info:
                logger.warning("[!] PANIC_LEAK DETECTED! Executing emergency intercept...")
                cards = self.vision.detect_deployable_cards(frame)
                self.panic_daemon.execute_emergency_intercept(
                    leak_info=leak_info,
                    cards=cards,
                    mapper=self.mapper,
                    humanizer=self.humanizer,
                    adb_client=self.client
                )
                time.sleep(1.0)
                continue

            # 4. Progressive deployment
            dp = self.vision.read_cost(frame)
            if dp is not None and deployed_idx < len(tactical_steps):
                step = tactical_steps[deployed_idx]
                if dp >= step["min_dp"]:
                    cards = self.vision.detect_deployable_cards(frame)
                    ready_card = next((c for c in cards if c["is_ready"]), None)
                    if ready_card:
                        cx, cy = ready_card["center"]
                        tx, ty = step["target"]
                        logger.info(f"[+] Deploying {step['name']} (DP={dp}): Hand ({cx}, {cy}) ➔ Grid ({tx}, {ty}) facing {step['orientation']}")
                        gesture = self.humanizer.generate_deploy_gesture(
                            cx, cy, tx, ty, orientation=step["orientation"]
                        )
                        self.client.deploy_operator_gesture(gesture)
                        self.panic_daemon.register_blocker(tx, ty)
                        deployed_idx += 1
                        time.sleep(1.2)
                        continue

            time.sleep(0.5)

        logger.warning("[!] Combat loop timed out.")
        self._dismiss_settlement()
        return {"result": "TIMEOUT", "elapsed_sec": time.time() - t_start, "deployed_count": deployed_idx}

    def _dismiss_settlement(self):
        """Taps screen center twice to return from victory settlement to stage lobby."""
        logger.info("[*] Dismissing settlement screen...")
        time.sleep(2.0)
        self.client.tap(960, 540)
        time.sleep(2.5)
        self.client.tap(960, 540)
        time.sleep(2.0)
