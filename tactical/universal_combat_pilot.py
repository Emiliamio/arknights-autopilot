from core.abort_controller import AbortController
# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Universal Adaptive Combat Pilot & Generic Battle Loop
Author: Emiliamio <mio2110767128@163.com>
"""

import time
import logging
from typing import Dict, Any, Optional, List, Tuple
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
    1. Pre-battle adaptive handshake (auto start & wait for battlefield loading).
    2. Locks 2x combat speed.
    3. Monitors real-time DP and hand card readiness.
    4. Executes golden tactical deployment sequence (Vanguard ➔ DPS ➔ Tank ➔ Medic).
    5. Continuous skill rotation engine & emergency burst cast.
    6. Sentry Panic Daemon intercepts leaks in real-time.
    7. Multi-tap state-driven settlement dismissal (skips drops, EXP, and level-ups).
    8. Global abort controller & timeout watchdog.
    """

    def __init__(
        self,
        adb_client: Optional[ADBClient] = None,
        vision_engine: Optional[VisionEngine] = None,
        humanizer: Optional[TouchHumanizer] = None,
        mapper: Optional[HomographyMapper] = None,
        threat_monitor: Optional[ThreatMonitor] = None,
        panic_daemon: Optional[PanicDaemon] = None
    ):
        self.client = adb_client or ADBClient(instance_index=0)
        self.vision = vision_engine or VisionEngine()
        self.humanizer = humanizer or TouchHumanizer()
        self.mapper = mapper or HomographyMapper.create_synthetic_arknights_mapper()
        self.threat_monitor = threat_monitor or ThreatMonitor()
        self.panic_daemon = panic_daemon or PanicDaemon()

        self.deployed_operators: List[Dict[str, Any]] = []
        self.skill_rotation_interval: float = 6.0
        self.last_skill_cycle_time: float = 0.0
        self.skills_triggered_count: int = 0
        self.max_dismiss_taps: int = 12

    def enter_and_wait_battlefield(self, max_wait_sec: int = 30) -> bool:
        """
        Detects pre-battle screen and taps action buttons to load into battlefield.
        Screen 1: Blue Start Action button (1700, 920) or (1767, 987)
        Screen 2: Red Squad Start Action button (1655, 780)
        """
        logger.info("[*] Pre-battle handshake: checking and entering battlefield...")
        t0 = time.time()

        for _ in range(max_wait_sec):
            if AbortController.is_aborted():
                logger.warning("🛑 [UniversalCombatPilot] Abort signal during pre-battle entrance.")
                return False

            frame = self.client.screencap()
            if frame is None or frame.size == 0:
                time.sleep(1.0)
                continue

            state = self.vision.detect_battle_state(frame)
            if state == BattleState.IN_BATTLE:
                logger.info(f"[+] Battlefield confirmed loaded in {time.time() - t0:.1f}s!")
                return True

            if state == BattleState.PRE_BATTLE:
                h, w = frame.shape[:2]
                br_crop = frame[int(h * 0.80):, int(w * 0.70):]
                # Red mask indicates Squad Formation screen (Screen 2)
                red_mask = (br_crop[:, :, 2] > 140) & (br_crop[:, :, 0] < 80) & (br_crop[:, :, 1] < 80)
                if np.sum(red_mask) / float(br_crop.shape[0] * br_crop.shape[1]) > 0.04:
                    logger.info("[*] Tapping Red Squad Start Action at (1655, 780)...")
                    self.client.tap(1655, 780)
                else:
                    logger.info("[*] Tapping Blue Start Action at (1767, 987)...")
                    self.client.tap(1767, 987)
                time.sleep(2.0)
                continue

            time.sleep(1.0)

        logger.warning("[!] Timeout waiting to enter battlefield.")
        return False

    def ensure_speed_2x(self, frame: np.ndarray) -> bool:
        """Checks and toggles 2x speed icon at top right."""
        if not self.vision.is_2x_speed_active(frame):
            logger.info("[*] Toggling 2x speed at (1645, 69)...")
            self.client.tap(1645, 69)
            return True
        return False

    def deploy_step(
        self,
        step: Dict[str, Any],
        ready_card: Dict[str, Any],
        current_dp: int
    ) -> bool:
        """
        Executes atomic Bezier gesture deployment for a single operator.
        Supports raw screen coordinates (target) or 2.5D grid tiles (tile).
        """
        if "tile" in step:
            col, row = step["tile"]
            tx, ty = self.mapper.get_tile_center(col, row)
        elif "target" in step:
            tx, ty = step["target"]
        else:
            tx, ty = 960, 540

        cx, cy = ready_card["center"]
        orientation = step.get("orientation", "right")

        logger.info(
            f"[+] Deploying {step.get('name', 'Operator')} (DP={current_dp}): "
            f"Hand ({cx}, {cy}) ➔ Pos ({tx}, {ty}) facing {orientation}"
        )
        gesture = self.humanizer.generate_deploy_gesture(
            cx, cy, tx, ty, orientation=orientation
        )
        self.client.deploy_operator_gesture(gesture)

        if "tile" in step:
            self.panic_daemon.register_blocker(step["tile"][0], step["tile"][1])
        else:
            self.panic_daemon.register_blocker(int(tx), int(ty))

        self.deployed_operators.append({
            "name": step.get("name", f"Op_{len(self.deployed_operators) + 1}"),
            "pos": (tx, ty),
            "tile": step.get("tile", None),
            "orientation": orientation,
            "deployed_at": time.time(),
            "last_skill_attempt": time.time(),
            "auto_skill": step.get("auto_skill", True),
            "skill_cooldown": step.get("skill_cooldown", self.skill_rotation_interval)
        })
        return True

    def cycle_skills(self, current_time: Optional[float] = None) -> int:
        """
        Iterates over deployed operators and attempts to cast ready manual skills.
        Sequence: Tap operator body (tx, ty) ➔ Tap skill button (tx, ty - 60).
        """
        now = current_time or time.time()
        triggered = 0

        for op in self.deployed_operators:
            if not op.get("auto_skill", True):
                continue

            cooldown = op.get("skill_cooldown", self.skill_rotation_interval)
            if now - op["last_skill_attempt"] >= cooldown:
                tx, ty = op["pos"]
                logger.info(f"[*] Triggering skill for [{op['name']}] at ({tx}, {ty})...")
                self.client.tap(tx, ty)
                time.sleep(0.12)
                self.client.tap(tx, ty - 60)
                op["last_skill_attempt"] = now
                triggered += 1
                self.skills_triggered_count += 1
                time.sleep(0.15)

        return triggered

    def trigger_all_skills(self) -> int:
        """Forces immediate skill cast attempt for all deployed operators (Burst Mode)."""
        logger.info("⚡ [UniversalCombatPilot] Force All Skills (Burst Mode) Activated!")
        count = 0
        now = time.time()
        for op in self.deployed_operators:
            tx, ty = op["pos"]
            self.client.tap(tx, ty)
            time.sleep(0.10)
            self.client.tap(tx, ty - 60)
            op["last_skill_attempt"] = now
            count += 1
            self.skills_triggered_count += 1
            time.sleep(0.10)
        return count

    def dismiss_settlement(self, max_taps: Optional[int] = None, tap_interval: float = 1.5) -> bool:
        """
        State-driven dynamic settlement dismissal loop:
        Taps neutral screen area repeatedly to skip:
        1. Mission Clear animation.
        2. EXP / Trust gain.
        3. Item drops list.
        4. Account Level-Up popups.
        Exits dynamically once screen state is no longer VICTORY/DEFEAT.
        """
        limit = max_taps or self.max_dismiss_taps
        logger.info(f"[*] Dismissing settlement screen (Max {limit} dynamic taps)...")
        time.sleep(1.5)

        for attempt in range(limit):
            if AbortController.is_aborted():
                logger.warning("🛑 [UniversalCombatPilot] Abort signal detected in settlement dismissal.")
                return False

            frame = self.client.screencap()
            if frame is not None and frame.size > 0:
                state = self.vision.detect_battle_state(frame)
                if state not in (BattleState.VICTORY, BattleState.DEFEAT):
                    logger.info(f"[+] Settlement successfully dismissed at attempt #{attempt + 1}! State: {state.name}")
                    return True

            # Tap safe neutral right-center area to dismiss popups
            tap_x = 960 if attempt % 2 == 0 else 1120
            tap_y = 540
            logger.info(f"[*] Dismiss settlement tap #{attempt + 1} at ({tap_x}, {tap_y})...")
            self.client.tap(tap_x, tap_y)
            time.sleep(tap_interval)

        logger.info("[*] Settlement dismissal loop finished.")
        return True

    def _dismiss_settlement(self):
        """Backward-compatible alias for dismiss_settlement."""
        return self.dismiss_settlement()

    def run_combat(
        self,
        max_duration_sec: int = 180,
        tactical_steps: Optional[List[Dict[str, Any]]] = None,
        auto_handle_pre_battle: bool = True
    ) -> Dict[str, Any]:
        """
        Runs autonomous end-to-end combat loop until victory, defeat, abort or timeout.
        """
        logger.info("[*] Universal Combat Pilot engaged on battlefield...")
        t_start = time.time()
        speed_ensured = False

        # 1. Pre-battle entrance handling if needed
        if auto_handle_pre_battle:
            init_frame = self.client.screencap()
            if init_frame is not None and init_frame.size > 0:
                if self.vision.detect_battle_state(init_frame) == BattleState.PRE_BATTLE:
                    if not self.enter_and_wait_battlefield(max_wait_sec=25):
                        return {
                            "result": "PRE_BATTLE_TIMEOUT",
                            "elapsed_sec": time.time() - t_start,
                            "deployed_count": 0,
                            "skills_triggered": 0
                        }

        # 2. Reset runtime state
        self.deployed_operators.clear()
        self.skills_triggered_count = 0

        steps = tactical_steps or [
            {"target": (960, 540), "orientation": "right", "min_dp": 10, "name": "Vanguard/Melee"},
            {"target": (1100, 540), "orientation": "right", "min_dp": 14, "name": "Guard/Blocker"},
            {"target": (960, 380), "orientation": "down", "min_dp": 18, "name": "Sniper/Ranged"},
            {"target": (800, 380), "orientation": "right", "min_dp": 24, "name": "Medic/Support"}
        ]
        deployed_idx = 0

        # 3. Active battle loop
        while time.time() - t_start < max_duration_sec:
            if AbortController.is_aborted():
                logger.warning("🛑 [UniversalCombatPilot] Emergency stop signal detected. Ceasing battle execution...")
                return {
                    "result": "ABORTED",
                    "elapsed_sec": time.time() - t_start,
                    "deployed_count": deployed_idx,
                    "skills_triggered": self.skills_triggered_count
                }

            frame = self.client.screencap()
            if frame is None or frame.size == 0:
                time.sleep(0.5)
                continue

            state = self.vision.detect_battle_state(frame)

            # Step A: Settlement check (Highest Priority)
            if state in (BattleState.VICTORY, BattleState.DEFEAT):
                elapsed = time.time() - t_start
                logger.info(f"[+] Combat settled: {state.name} in {elapsed:.1f}s!")
                self.dismiss_settlement()
                return {
                    "result": state.name,
                    "elapsed_sec": elapsed,
                    "deployed_count": deployed_idx,
                    "skills_triggered": self.skills_triggered_count
                }

            # Step B: 2x Combat speed lock
            if not speed_ensured:
                self.ensure_speed_2x(frame)
                speed_ensured = True

            # Step C: Threat & Panic Leak Sentry
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

            # Step D: Progressive Operator Deployment
            dp = self.vision.read_cost(frame)
            if dp is not None and deployed_idx < len(steps):
                step = steps[deployed_idx]
                if dp >= step["min_dp"]:
                    cards = self.vision.detect_deployable_cards(frame)
                    ready_card = next((c for c in cards if c["is_ready"]), None)
                    if ready_card:
                        self.deploy_step(step, ready_card, dp)
                        deployed_idx += 1
                        time.sleep(1.2)
                        continue

            # Step E: Periodic Skill Rotation
            self.cycle_skills(current_time=time.time())

            time.sleep(0.4)

        logger.warning("[!] Combat loop timed out.")
        self.dismiss_settlement()
        return {
            "result": "TIMEOUT",
            "elapsed_sec": time.time() - t_start,
            "deployed_count": deployed_idx,
            "skills_triggered": self.skills_triggered_count
        }
