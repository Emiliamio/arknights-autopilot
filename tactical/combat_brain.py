# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
In-Combat Heuristic Planner & HFSM State Machine (Integrated with PanicDaemon)
Author: Emiliamio <mio2110767128@163.com>
"""

from enum import Enum
from typing import List, Tuple, Dict, Any, Optional
import time
import logging

from tactical.map_deconstructor import TacticalMap
from tactical.choke_point_analyzer import ChokePointAnalyzer, HighGroundScorer
from tactical.threat_monitor import ThreatMonitor, ThreatLevel
from tactical.panic_daemon import PanicDaemon
from core.homography_mapper import HomographyMapper
from core.vision_engine import VisionEngine, BattleState
from core.touch_humanizer import TouchHumanizer
from core.adb_client import ADBClient

logger = logging.getLogger("ASTA.CombatBrain")


class BrainState(Enum):
    """Hierarchical states of the Combat Brain."""
    INITIALIZING = "INITIALIZING"
    PRE_COMBAT_DISPATCH = "PRE_COMBAT_DISPATCH"
    ACTIVE_ENGAGEMENT = "ACTIVE_ENGAGEMENT"
    SETTLEMENT_RECOVERY = "SETTLEMENT_RECOVERY"
    COMPLETED = "COMPLETED"


class DeploymentStep:
    """Represents a scheduled operator deployment action."""

    def __init__(
        self,
        step_id: int,
        role: str,
        target_col: int,
        target_row: int,
        orientation: str,
        min_dp: int,
        preferred_slot: int = 0
    ):
        self.step_id = step_id
        self.role = role
        self.col = target_col
        self.row = target_row
        self.target_tile = (target_col, target_row)
        self.orientation = orientation
        self.min_dp = min_dp
        self.preferred_slot = preferred_slot
        self.status = "PENDING"  # PENDING, DEPLOYED, SKIPPED
        self.deployed_at_dp: Optional[int] = None
        self.deployed_timestamp: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "role": self.role,
            "col": self.col,
            "row": self.row,
            "target_tile": [self.col, self.row],
            "orientation": self.orientation,
            "min_dp": self.min_dp,
            "status": self.status,
            "deployed_at_dp": self.deployed_at_dp
        }


class CombatBrain:
    """
    Tactical decision maker and autonomous operator deployment controller.
    Features:
    - Preemptive PanicDaemon for 0.5s emergency leak interception.
    - ThreatMonitor integration for continuous spatial safety monitoring.
    - 4-stage deployment blueprint with atomic continuous motionevent execution.
    """

    def __init__(
        self,
        tactical_map: TacticalMap,
        choke_analysis: Dict[str, Any],
        high_ground_ranks: List[Dict[str, Any]],
        medic_ranks: Optional[List[Dict[str, Any]]] = None
    ):
        self.map = tactical_map
        self.choke_analysis = choke_analysis
        self.high_ground_ranks = high_ground_ranks
        self.medic_ranks = medic_ranks or []

        self.threat_monitor = ThreatMonitor(tactical_map)
        self.panic_daemon = PanicDaemon(tactical_map)

        self.state = BrainState.INITIALIZING
        self.plan: List[DeploymentStep] = []
        self.current_step_idx = 0

        self.last_dp: int = 0
        self.kill_count: Tuple[int, int] = (0, 0)
        self.ticks_count: int = 0
        self.speed_2x_ensured: bool = False
        self.last_pre_battle_click_time: float = 0.0

        self.generate_deployment_plan()

    def generate_deployment_plan(self) -> List[DeploymentStep]:
        """Synthesizes the optimal 4-stage deployment sequence."""
        self.plan = []
        step_id = 1

        primary_choke = self.choke_analysis.get("primary_choke")
        if primary_choke:
            pr, pc = primary_choke["coord"]
            self.plan.append(DeploymentStep(
                step_id=step_id,
                role="VANGUARD",
                target_col=pc,
                target_row=pr,
                orientation="right",
                min_dp=10,
                preferred_slot=0
            ))
            step_id += 1

        if self.high_ground_ranks:
            top_hg = self.high_ground_ranks[0]
            hr, hc = top_hg["coord"]
            self.plan.append(DeploymentStep(
                step_id=step_id,
                role="SNIPER",
                target_col=hc,
                target_row=hr,
                orientation=top_hg.get("optimal_orientation", "down"),
                min_dp=12,
                preferred_slot=1
            ))
            step_id += 1

        if self.medic_ranks:
            top_med = self.medic_ranks[0]
            mr, mc = top_med["coord"]
            self.plan.append(DeploymentStep(
                step_id=step_id,
                role="MEDIC",
                target_col=mc,
                target_row=mr,
                orientation=top_med.get("optimal_orientation", "down"),
                min_dp=16,
                preferred_slot=2
            ))
            step_id += 1

        secondaries = self.choke_analysis.get("secondary_chokes", [])
        if secondaries:
            sr, sc = secondaries[0]["coord"]
            self.plan.append(DeploymentStep(
                step_id=step_id,
                role="DEFENDER",
                target_col=sc,
                target_row=sr,
                orientation="right",
                min_dp=20,
                preferred_slot=3
            ))
            step_id += 1

        self.state = BrainState.PRE_COMBAT_DISPATCH
        return self.plan

    def get_current_pending_step(self) -> Optional[DeploymentStep]:
        """Returns the next pending deployment action."""
        if self.current_step_idx < len(self.plan):
            return self.plan[self.current_step_idx]
        return None

    def tick(
        self,
        frame: Any,
        vision_engine: VisionEngine,
        mapper: HomographyMapper,
        humanizer: TouchHumanizer,
        adb_client: Optional[ADBClient] = None
    ) -> Dict[str, Any]:
        """Executes one evaluation cycle of the Combat Brain."""
        self.ticks_count += 1
        action_taken = "NONE"
        action_details = {}

        detected_state = vision_engine.detect_battle_state(frame)

        # 1. HIGHEST PRIORITY: End of combat settlement
        if detected_state in (BattleState.VICTORY, BattleState.DEFEAT):
            self.state = BrainState.SETTLEMENT_RECOVERY
            action_taken = f"SETTLE_{detected_state.name}"
            if adb_client:
                adb_client.tap(960, 540)
            self.state = BrainState.COMPLETED

        # 2. SECOND PRIORITY: Pre-battle mission dispatch with 1.2s debounce
        elif detected_state == BattleState.PRE_BATTLE and self.state != BrainState.ACTIVE_ENGAGEMENT:
            self.state = BrainState.PRE_COMBAT_DISPATCH
            now = time.time()
            if now - self.last_pre_battle_click_time > 1.2:
                action_taken = "START_MISSION"
                self.last_pre_battle_click_time = now
                if adb_client:
                    adb_client.tap(1650, 950)

        # 3. THIRD PRIORITY: Active combat engagement
        elif detected_state == BattleState.IN_BATTLE or self.state == BrainState.ACTIVE_ENGAGEMENT:
            self.state = BrainState.ACTIVE_ENGAGEMENT

            # Auto-ensure 2x speed
            if not self.speed_2x_ensured:
                if not vision_engine.is_2x_speed_active(frame):
                    action_taken = "TOGGLE_2X_SPEED"
                    if adb_client:
                        adb_client.tap(1620, 50)
                self.speed_2x_ensured = True

            current_dp = vision_engine.read_cost(frame)
            if current_dp is not None:
                self.last_dp = current_dp

            kc = vision_engine.read_kill_count(frame)
            if kc[0] is not None:
                self.kill_count = kc

            cards = vision_engine.detect_deployable_cards(frame)

            # EMERGENCY THREAT SCAN: Detect imminent leaks <= 2 tiles from Goal
            enemies = self.threat_monitor.detect_enemies(frame, mapper)
            threat_lvl, leak_info = self.threat_monitor.evaluate_threat(
                enemies, self.panic_daemon.active_blockers
            )

            if threat_lvl == ThreatLevel.PANIC_LEAK and leak_info:
                # PREEMPT REGULAR DEPLOYMENT: Emergency Intercept
                intercept_res = self.panic_daemon.execute_emergency_intercept(
                    leak_info=leak_info,
                    cards=cards,
                    mapper=mapper,
                    humanizer=humanizer,
                    adb_client=adb_client
                )
                action_taken = "PANIC_INTERCEPT"
                action_details = intercept_res

            # Regular planned deployment if no active panic
            if action_taken == "NONE":
                step = self.get_current_pending_step()
                if step and self.last_dp >= step.min_dp:
                    slot_to_use = None
                    if step.preferred_slot < len(cards) and cards[step.preferred_slot]["is_ready"]:
                        slot_to_use = cards[step.preferred_slot]
                    else:
                        for c in cards:
                            if c["is_ready"]:
                                slot_to_use = c
                                break

                    if slot_to_use:
                        card_x, card_y = slot_to_use["center"]
                        target_x, target_y = mapper.get_tile_center(step.col, step.row)

                        gesture = humanizer.generate_deploy_gesture(
                            card_x, card_y, target_x, target_y, orientation=step.orientation
                        )

                        if adb_client:
                            adb_client.deploy_operator_gesture(gesture)

                        # Register ground blocker
                        if step.role in ("VANGUARD", "DEFENDER", "GUARD"):
                            self.panic_daemon.register_blocker(step.col, step.row)

                        step.status = "DEPLOYED"
                        step.deployed_at_dp = self.last_dp
                        step.deployed_timestamp = time.time()
                        self.current_step_idx += 1

                        action_taken = f"DEPLOY_{step.role}"
                        action_details = {
                            "role": step.role,
                            "tile": (step.col, step.row),
                            "orientation": step.orientation,
                            "dp_cost": self.last_dp
                        }

        return {
            "tick": self.ticks_count,
            "brain_state": self.state.value,
            "detected_battle_state": detected_state.name,
            "current_dp": self.last_dp,
            "kill_count": self.kill_count,
            "action_taken": action_taken,
            "action_details": action_details,
            "plan_progress": f"{self.current_step_idx}/{len(self.plan)}"
        }