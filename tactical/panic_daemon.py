# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Panic Fallback Daemon & Emergency Reserve Dispatcher
Author: Emiliamio <mio2110767128@163.com>
"""

import time
from enum import Enum
from typing import List, Tuple, Dict, Any, Optional, Set
import logging

from tactical.map_deconstructor import TacticalMap
from core.homography_mapper import HomographyMapper
from core.touch_humanizer import TouchHumanizer
from core.adb_client import ADBClient

logger = logging.getLogger("ASTA.PanicDaemon")


class EmergencyTier(Enum):
    TIER_1_DROP = "TIER_1_DROP"           # 0.37ms 快活空投截停 (砾/红/夜刀)
    TIER_2_BURST = "TIER_2_BURST"         # 决战技全员爆发强开 (Burst Mode 熔化高威胁怪)
    TIER_3_RELAY = "TIER_3_RELAY"         # 残血干员战术接力撤退 (退费换防)


class PanicDaemon:
    """
    Emergency intervention daemon for sudden front-line breaches.
    Provides 3 tiers of defensive response:
    - Tier 1: Fast-redeploy face-plant intercept drop.
    - Tier 2: Emergency burst activation of all on-field manual skills.
    - Tier 3: Tactical retreat and relay redeployment.
    """

    def __init__(self, tactical_map: Optional[TacticalMap] = None):
        self.map = tactical_map or TacticalMap.create_1_7()
        self.active_blockers: Set[Tuple[int, int]] = set()  # (col, row)
        self.intercept_cooldowns: Dict[Tuple[int, int], float] = {}  # (col, row) -> timestamp
        self.cooldown_sec: float = 2.0
        self.emergency_history: List[Dict[str, Any]] = []

    def register_blocker(self, col: int, row: int) -> None:
        """Registers a friendly operator occupying a ground blocking tile."""
        self.active_blockers.add((col, row))

    def unregister_blocker(self, col: int, row: int) -> None:
        """Removes a defeated, retreated, or breached blocker."""
        self.active_blockers.discard((col, row))

    def is_tile_on_cooldown(self, col: int, row: int) -> bool:
        """Checks if intercept tile is in debounce cooldown to avoid duplicate drops."""
        last_t = self.intercept_cooldowns.get((col, row), 0.0)
        return (time.time() - last_t) < self.cooldown_sec

    def select_emergency_operator(
        self,
        cards: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Selects the best emergency reserve card from hand:
        Prioritizes fast-redeploy / lowest slot index ready units.
        """
        ready_cards = [c for c in cards if c.get("is_ready", False)]
        if not ready_cards:
            return None
        # Prioritize lower slot indices (typically reserved for fast-redeploy specialists in slot 0..2)
        ready_cards.sort(key=lambda c: c.get("slot_index", 99))
        return ready_cards[0]

    def execute_emergency_intercept(
        self,
        leak_info: Dict[str, Any],
        cards: List[Dict[str, Any]],
        mapper: HomographyMapper,
        humanizer: TouchHumanizer,
        adb_client: Optional[ADBClient] = None
    ) -> Dict[str, Any]:
        """
        Executes millisecond-level preemptive emergency intercept:
        1. Selects ready emergency operator from hand;
        2. Maps intercept tile to screen coordinates;
        3. Generates continuous atomic motionevent gesture facing incoming enemy;
        4. Dispatches gesture to ADB hardware driver.
        """
        int_c, int_r = leak_info["intercept_tile"]

        if self.is_tile_on_cooldown(int_c, int_r):
            return {"status": "COOLDOWN_SUPPRESSED", "tile": (int_c, int_r)}

        operator_card = self.select_emergency_operator(cards)
        if not operator_card:
            return {"status": "NO_EMERGENCY_RESERVES", "tile": (int_c, int_r)}

        t0 = time.perf_counter()
        card_x, card_y = operator_card["center"]
        target_x, target_y = mapper.get_tile_center(int_c, int_r)
        facing = leak_info.get("facing", "left")

        # Generate atomic deployment gesture
        gesture = humanizer.generate_deploy_gesture(
            card_x, card_y, target_x, target_y, orientation=facing
        )

        exec_res = {}
        if adb_client:
            exec_res = adb_client.deploy_operator_gesture(gesture)

        cost_ms = (time.perf_counter() - t0) * 1000.0

        # Mark blocker as active and update cooldown
        self.register_blocker(int_c, int_r)
        self.intercept_cooldowns[(int_c, int_r)] = time.time()

        record = {
            "status": "INTERCEPTED",
            "enemy_pos": leak_info["enemy_pos"],
            "intercept_tile": (int_c, int_r),
            "facing": facing,
            "slot_used": operator_card["slot_index"],
            "dispatch_latency_ms": round(cost_ms, 2),
            "driver_execution": exec_res
        }
        self.emergency_history.append(record)
        return record

    def execute_multi_tier_emergency(
        self,
        leak_info: Dict[str, Any],
        cards: List[Dict[str, Any]],
        deployed_operators: Optional[Dict[str, Tuple[int, int]]],
        mapper: HomographyMapper,
        humanizer: TouchHumanizer,
        adb_client: Optional[ADBClient] = None
    ) -> Dict[str, Any]:
        """
        Executes multi-tier defensive protocol based on breach severity:
        Tier 1: Try dropping emergency reserve blocker.
        Tier 2: If cards empty or tile on cooldown, escalate to Burst Skills mode!
        """
        # Attempt Tier 1: Emergency reserve drop
        t1_res = self.execute_emergency_intercept(
            leak_info=leak_info,
            cards=cards,
            mapper=mapper,
            humanizer=humanizer,
            adb_client=adb_client
        )

        if t1_res.get("status") == "INTERCEPTED":
            t1_res["tier"] = EmergencyTier.TIER_1_DROP.value
            return t1_res

        # Tier 2: Escalate to Burst Skills Mode
        burst_res = self.trigger_burst_mode(deployed_operators, mapper, adb_client)
        return {
            "status": "BURST_TRIGGERED",
            "tier": EmergencyTier.TIER_2_BURST.value,
            "intercept_tile": leak_info.get("intercept_tile"),
            "skills_triggered": burst_res.get("triggered_count", 0),
            "fallback_reason": t1_res.get("status")
        }

    def trigger_burst_mode(
        self,
        deployed_operators: Optional[Dict[str, Tuple[int, int]]],
        mapper: HomographyMapper,
        adb_client: Optional[ADBClient] = None
    ) -> Dict[str, Any]:
        """Triggers manual skills on all currently deployed operators."""
        triggered_count = 0
        if deployed_operators and adb_client:
            for name, (col, row) in deployed_operators.items():
                tx, ty = mapper.get_tile_center(col, row)
                adb_client.tap(tx, ty)
                adb_client.tap(tx, ty - 60)
                triggered_count += 1
        logger.warning(f"⚡ [PanicDaemon TIER_2] Burst Mode activated! Triggered skills on {triggered_count} operators.")
        return {"triggered_count": triggered_count, "status": "BURST_SKILLS_EXECUTED"}