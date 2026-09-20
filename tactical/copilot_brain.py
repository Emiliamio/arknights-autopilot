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
      Maintains internal registry of deployed operator positions to auto-resolve omitted skill/retreat coordinates.
    - Track B (Panic Sentry): Preemptively intercepts leaks with 0.37ms PanicDaemon if front-line falls!
    """

    def __init__(
        self,
        tactical_map: TacticalMap,
        copilot_plan: CopilotPlan,
        owned_roster: Optional[List[str]] = None
    ):
        self.map = tactical_map
        self.original_plan = copilot_plan
        self.owned_roster = owned_roster
        self.substitutions: Dict[str, str] = {}

        if owned_roster is not None:
            from tactical.copilot_fuzzy_matcher import CopilotFuzzyMatcher
            matcher = CopilotFuzzyMatcher()
            self.plan, sub_details = matcher.adapt_plan(copilot_plan, owned_roster)
            self.substitutions = {k: v["substitute"] for k, v in sub_details.items()}
        else:
            self.plan = copilot_plan

        self.current_action_idx = 0

        self.threat_monitor = ThreatMonitor(tactical_map)
        self.panic_daemon = PanicDaemon(tactical_map)

        # Tracks deployed named operators on the field: { "芬": (col, row), "克洛丝": (col, row) }
        self.deployed_operators: Dict[str, Tuple[int, int]] = {}

        self.last_dp: int = 0
        self.kill_count: Tuple[int, int] = (0, 0)
        self.ticks_count: int = 0
        self.speed_2x_ensured: bool = False

        self.action_start_time: float = time.time()
        self.soft_timeout_sec: float = 8.0
        self.watchdog_timeout_sec: float = 25.0
        self.emergency_interventions_count: int = 0

    def get_current_action(self) -> Optional[CopilotAction]:
        """Returns current pending Copilot action."""
        if self.current_action_idx < len(self.plan.actions):
            return self.plan.actions[self.current_action_idx]
        return None

    def resolve_operator_slot(self, operator_name: str, cards: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Resolves the best hand card slot matching the action operator name:
        1. Checks index in plan.opers matching operator_name;
        2. If that slot is ready, returns it;
        3. Fallback: returns the first available ready card slot.
        """
        ready_cards = [c for c in cards if c.get("is_ready", False)]
        if not ready_cards:
            return None

        # Check matching index in plan.opers
        matched_idx = None
        for idx, op in enumerate(self.plan.opers):
            if op.get("name") == operator_name:
                matched_idx = idx
                break

        if matched_idx is not None:
            for c in ready_cards:
                if c.get("slot_index") == matched_idx:
                    return c

        return ready_cards[0]

    def evaluate_action_readiness(
        self,
        action: CopilotAction,
        current_dp: int,
        kills: int,
        threat_lvl: ThreatLevel,
        elapsed_sec: float
    ) -> Tuple[bool, str]:
        """
        Evaluates whether an action should be executed under the Desync Deadlock Breaker protocol:
        Returns:
            (is_ready, reason):
            - (True, "NORMAL"): Both DP and Kill requirements satisfied.
            - (True, "SOFT_DP_SURPLUS"): Kill condition soft-bypassed due to significant DP surplus & wait time.
            - (True, "THREAT_URGENCY"): Kill condition soft-bypassed due to elevated threat level on map.
            - (False, "WAITING_DP"): Need more DP.
            - (False, "WAITING_KILLS"): DP ready but waiting for required kill count.
        """
        dp_satisfied = (current_dp >= action.min_costs)
        kills_satisfied = (kills >= action.min_kills)

        if dp_satisfied and kills_satisfied:
            return True, "NORMAL"

        if dp_satisfied and not kills_satisfied:
            # Threat pressure override: enemy leak danger requires immediate deployment/skill
            if threat_lvl in (ThreatLevel.ALERT, ThreatLevel.PANIC_LEAK):
                return True, "THREAT_URGENCY"
            # Soft DP surplus override: wave stall where DP overflows while waiting for 1 kill
            if elapsed_sec >= self.soft_timeout_sec and current_dp >= (action.min_costs + 12):
                return True, "SOFT_DP_SURPLUS"
            return False, "WAITING_KILLS"

        return False, "WAITING_DP"

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
            # PREEMPTIVE HIJACK: Multi-tier emergency reserve intercept overrules Copilot!
            intercept_res = self.panic_daemon.execute_multi_tier_emergency(
                leak_info=leak_info,
                cards=cards,
                deployed_operators=self.deployed_operators,
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
            now = time.time()
            elapsed_sec = now - self.action_start_time
            curr_kills = self.kill_count[0] if self.kill_count[0] is not None else 0

            is_ready, ready_reason = self.evaluate_action_readiness(
                action=action,
                current_dp=self.last_dp,
                kills=curr_kills,
                threat_lvl=threat_lvl,
                elapsed_sec=elapsed_sec
            )

            if elapsed_sec > self.watchdog_timeout_sec and not is_ready:
                logger.warning(
                    f"Action #{action.step_index} ({action.action_type.value} {action.name}) "
                    f"timed out after {elapsed_sec:.1f}s. Watchdog force-bypassing..."
                )
                action.status = "SKIPPED_TIMEOUT"
                self.current_action_idx += 1
                self.action_start_time = now
                action_taken = "WATCHDOG_BYPASS"
                action_details = {"skipped_action": action.to_dict(), "reason": "TIMEOUT_WATCHDOG"}
            elif is_ready:
                if ready_reason != "NORMAL":
                    logger.info(
                        f"⚡ [DesyncBreaker] Action #{action.step_index} triggered via {ready_reason} "
                        f"(DP={self.last_dp}/{action.min_costs}, Kills={curr_kills}/{action.min_kills})"
                    )
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
                    slot_to_use = self.resolve_operator_slot(action.name, cards)

                    if slot_to_use:
                        card_x, card_y = slot_to_use["center"]
                        target_x, target_y = mapper.get_tile_center(action.col, action.row)

                        gesture = humanizer.generate_deploy_gesture(
                            card_x, card_y, target_x, target_y, orientation=action.direction
                        )

                        if adb_client:
                            adb_client.deploy_operator_gesture(gesture)

                        # Register in deployed named operators registry
                        if action.name:
                            self.deployed_operators[action.name] = (action.col, action.row)

                        # Register ground blocker if tile is walkable ground
                        if self.map.is_deployable_ground(action.row, action.col):
                            self.panic_daemon.register_blocker(action.col, action.row)

                        action.status = "EXECUTED"
                        self.current_action_idx += 1
                        self.action_start_time = now
                        action_taken = f"COPILOT_DEPLOY_{action.name}"
                        action_details = action.to_dict()

                elif action.action_type == CopilotActionType.SKILL:
                    # Auto-resolve operator location if location is omitted [0, 0]
                    col, row = action.col, action.row
                    if col == 0 and row == 0 and action.name in self.deployed_operators:
                        col, row = self.deployed_operators[action.name]

                    target_x, target_y = mapper.get_tile_center(col, row)
                    if adb_client:
                        # Tap operator to open skill menu, then tap skill icon above
                        adb_client.tap(target_x, target_y)
                        time.sleep(0.12)
                        adb_client.tap(target_x, target_y - 60)

                    action.status = "EXECUTED"
                    self.current_action_idx += 1
                    self.action_start_time = now
                    action_taken = f"COPILOT_SKILL_{action.name}"
                    action_details = action.to_dict()

                elif action.action_type == CopilotActionType.RETREAT:
                    col, row = action.col, action.row
                    if col == 0 and row == 0 and action.name in self.deployed_operators:
                        col, row = self.deployed_operators[action.name]

                    target_x, target_y = mapper.get_tile_center(col, row)
                    if adb_client:
                        adb_client.tap(target_x, target_y)
                        time.sleep(0.12)
                        adb_client.tap(target_x - 60, target_y - 80)

                    self.panic_daemon.unregister_blocker(col, row)
                    if action.name in self.deployed_operators:
                        del self.deployed_operators[action.name]

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