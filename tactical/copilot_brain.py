# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Dual-Track Copilot Brain (MAA Action Executor + Preemptive Panic Sentry)
Author: Emiliamio <mio2110767128@163.com>
"""

import time
import logging
from typing import List, Tuple, Dict, Any, Optional

from tactical.copilot_adapter import CopilotPlan, CopilotAction, CopilotActionType
from tactical.map_deconstructor import TacticalMap
from tactical.threat_monitor import ThreatMonitor, ThreatLevel
from tactical.panic_daemon import PanicDaemon
from core.homography_mapper import HomographyMapper
from core.vision_engine import VisionEngine, BattleState
from core.touch_humanizer import TouchHumanizer
from core.adb_client import ADBClient

logger = logging.getLogger("ASTA.CopilotBrain")


class CopilotBrain:
    """
    Dual-Track Arbiter for executing community MAA Copilot JSON plans:
    - Track A (Main Plan): Sequentially steps through MAA actions (Deploy, Skill, Retreat).
    - Track B (Panic Sentry): Preemptively intercepts leaks with 0.37ms PanicDaemon if front-line falls!
    """

    def __init__(
        self,
        tactical_map: TacticalMap,
        copilot_plan: CopilotPlan
    ):
        self.map = tactical_map
        self.plan = copilot_plan
        self.current_action_idx = 0

        self.threat_monitor = ThreatMonitor(tactical_map)
        self.panic_daemon = PanicDaemon(tactical_map)

        self.last_dp: int = 0
        self.kill_count: Tuple[int, int] = (0, 0)
        self.ticks_count: int = 0
        self.speed_2x_ensured: bool = False

        self.action_start_time: float = time.time()
        self.watchdog_timeout_sec: float = 25.0
        self.emergency_interventions_count: int = 0

    def get_current_action(self) -> Optional[CopilotAction]:
        """Returns current pending Copilot action."""
        if self.current_action_idx < len(self.plan.actions):
            return self.plan.actions[self.current_action_idx]
        return None

    def tick(
        self,
        frame: Any,
        vision_engine: VisionEngine,
        mapper: HomographyMapper,
        humanizer: TouchHumanizer,
        adb_client: Optional[ADBClient] = None
    ) -> Dict[str, Any]:
        """
        Executes one cycle of the Dual-Track Arbiter:
        Priority 0: Settlement (Victory/Defeat)
        Priority 1: Panic Sentry Intercept (Overrules Copilot on breach)
        Priority 2: Main Track Copilot Execution (Deploy/Skill/Retreat)
        """
        self.ticks_count += 1
        action_taken = "NONE"
        action_details = {}

        detected_state = vision_engine.detect_battle_state(frame)

        # 1. PRIORITY 0: End of combat settlement
        if detected_state in (BattleState.VICTORY, BattleState.DEFEAT):
            action_taken = f"SETTLE_{detected_state.name}"
            if adb_client:
                adb_client.tap(960, 540)
            return {
                "tick": self.ticks_count,
                "status": "COMPLETED",
                "action_taken": action_taken,
                "action_details": {"settlement": detected_state.name}
            }

        # 2. Update real-time DP and Kill telemetry
        current_dp = vision_engine.read_cost(frame)
        if current_dp is not None:
            self.last_dp = current_dp

        kc = vision_engine.read_kill_count(frame)
        if kc[0] is not None:
            self.kill_count = kc

        cards = vision_engine.detect_deployable_cards(frame)

        # 3. PRIORITY 1: PANIC SENTRY - Check for unexpected front-line breach
        enemies = self.threat_monitor.detect_enemies(frame, mapper)
        threat_lvl, leak_info = self.threat_monitor.evaluate_threat(
            enemies, self.panic_daemon.active_blockers
        )

        if threat_lvl == ThreatLevel.PANIC_LEAK and leak_info:
            # PREEMPTIVE HIJACK: Emergency reserve intercept overrules Copilot!
            intercept_res = self.panic_daemon.execute_emergency_intercept(
                leak_info=leak_info,
                cards=cards,
                mapper=mapper,
                humanizer=humanizer,
                adb_client=adb_client
            )
            self.emergency_interventions_count += 1
            action_taken = "PANIC_INTERCEPT_PREEMPTION"
            action_details = intercept_res
            return {
                "tick": self.ticks_count,
                "status": "EMERGENCY_INTERVENING",
                "action_taken": action_taken,
                "action_details": action_details,
                "current_dp": self.last_dp,
                "kill_count": self.kill_count,
                "copilot_progress": f"{self.current_action_idx}/{len(self.plan.actions)}",
                "emergency_interventions": self.emergency_interventions_count
            }

        # 4. PRIORITY 2: MAIN TRACK COPILOT EXECUTION
        action = self.get_current_action()
        if action:
            # Check readiness criteria: DP >= min_costs and Kills >= min_kills
            dp_satisfied = (self.last_dp >= action.min_costs)
            kills_satisfied = (self.kill_count[0] >= action.min_kills)

            # Watchdog timeout check
            now = time.time()
            if (now - self.action_start_time) > self.watchdog_timeout_sec and not (dp_satisfied and kills_satisfied):
                logger.warning(f"Action #{action.step_index} timed out ({self.watchdog_timeout_sec}s). Force bypassing...")
                action.status = "SKIPPED_TIMEOUT"
                self.current_action_idx += 1
                self.action_start_time = now
                action_taken = "WATCHDOG_BYPASS"
                action_details = {"skipped_action": action.to_dict()}
            elif dp_satisfied and kills_satisfied:
                if action.action_type == CopilotActionType.SPEED_UP:
                    if not self.speed_2x_ensured:
                        if not vision_engine.is_2x_speed_active(frame):
                            if adb_client:
                                adb_client.tap(1620, 50)
                        self.speed_2x_ensured = True
                    action.status = "EXECUTED"
                    action_taken = "SPEED_UP_CONFIRMED"
                    self.current_action_idx += 1
                    self.action_start_time = now

                elif action.action_type == CopilotActionType.DEPLOY:
                    # Find matching ready card slot
                    ready_cards = [c for c in cards if c.get("is_ready", False)]
                    slot_to_use = ready_cards[0] if ready_cards else None

                    if slot_to_use:
                        card_x, card_y = slot_to_use["center"]
                        target_x, target_y = mapper.get_tile_center(action.col, action.row)

                        gesture = humanizer.generate_deploy_gesture(
                            card_x, card_y, target_x, target_y, orientation=action.direction
                        )

                        if adb_client:
                            adb_client.deploy_operator_gesture(gesture)

                        # Register ground blocker if tile is walkable ground
                        if self.map.is_deployable_ground(action.row, action.col):
                            self.panic_daemon.register_blocker(action.col, action.row)

                        action.status = "EXECUTED"
                        self.current_action_idx += 1
                        self.action_start_time = now
                        action_taken = f"COPILOT_DEPLOY_{action.name}"
                        action_details = action.to_dict()

                elif action.action_type == CopilotActionType.SKILL:
                    # Tap target tile to activate operator skill
                    target_x, target_y = mapper.get_tile_center(action.col, action.row)
                    if adb_client:
                        adb_client.tap(target_x, target_y)
                    action.status = "EXECUTED"
                    self.current_action_idx += 1
                    self.action_start_time = now
                    action_taken = f"COPILOT_SKILL_{action.name}"
                    action_details = action.to_dict()

                elif action.action_type == CopilotActionType.RETREAT:
                    # Tap operator to open retreat menu, then tap retreat button
                    target_x, target_y = mapper.get_tile_center(action.col, action.row)
                    if adb_client:
                        adb_client.tap(target_x, target_y)
                        time.sleep(0.1)
                        adb_client.tap(target_x - 60, target_y - 80)  # Retreat button offset
                    self.panic_daemon.unregister_blocker(action.col, action.row)
                    action.status = "EXECUTED"
                    self.current_action_idx += 1
                    self.action_start_time = now
                    action_taken = f"COPILOT_RETREAT_{action.name}"
                    action_details = action.to_dict()

        return {
            "tick": self.ticks_count,
            "status": "RUNNING",
            "action_taken": action_taken,
            "action_details": action_details,
            "current_dp": self.last_dp,
            "kill_count": self.kill_count,
            "copilot_progress": f"{self.current_action_idx}/{len(self.plan.actions)}",
            "emergency_interventions": self.emergency_interventions_count
        }