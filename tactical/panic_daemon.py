# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Panic Fallback Daemon & Emergency Reserve Dispatcher
Author: Emiliamio <mio2110767128@163.com>
"""

import time
from typing import List, Tuple, Dict, Any, Optional, Set
import logging

from tactical.map_deconstructor import TacticalMap
from core.homography_mapper import HomographyMapper
from core.touch_humanizer import TouchHumanizer
from core.adb_client import ADBClient

logger = logging.getLogger("ASTA.PanicDaemon")


class PanicDaemon:
    """
    Emergency intervention daemon for sudden front-line breaches.
    Preemptively intercepts leaks by deploying emergency reserves within <= 350ms.
    """

    def __init__(self, tactical_map: TacticalMap):
        self.map = tactical_map
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