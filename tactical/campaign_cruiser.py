from core.abort_controller import AbortController
# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Autonomous Chapter Campaign Progression Cruiser (One-Click Chapter Cleared)
Author: Emiliamio <mio2110767128@163.com>
"""

import time
import logging
import re
from typing import List, Dict, Any, Optional
import numpy as np

from core.adb_client import ADBClient
from core.vision_engine import VisionEngine
from tactical.global_navigator import GlobalNavigator, SceneType
from tactical.universal_combat_pilot import UniversalCombatPilot

logger = logging.getLogger("ASTA.CampaignCruiser")


class CampaignCruiser:
    """
    Executes end-to-end continuous chapter progression:
    - Scans chapter map for current progress.
    - Automatically advances through stages (0-1, 0-2, 0-3...).
    - Skips story-only dialogue nodes in 0 seconds.
    - Executes autonomous combat on tactical battle stages.
    - Loops until the entire chapter is 100% cleared.
    """

    def __init__(
        self,
        adb_client: Optional[ADBClient] = None,
        vision_engine: Optional[VisionEngine] = None,
        navigator: Optional[GlobalNavigator] = None,
        pilot: Optional[UniversalCombatPilot] = None
    ):
        self.client = adb_client or ADBClient(instance_index=0)
        self.vision = vision_engine or VisionEngine()
        self.navigator = navigator or GlobalNavigator(adb_client=self.client, vision_engine=self.vision)
        self.pilot = pilot or UniversalCombatPilot(adb_client=self.client, vision_engine=self.vision)

    def cruise_chapter(self, chapter_num: int, max_stages: int = 15) -> Dict[str, Any]:
        """Runs autonomous progression through the designated chapter."""
        logger.info(f"======================================================================")
        f"  🚀 ASTA Autonomous Campaign Cruiser: EPISODE {chapter_num} ENGAGED"
        logger.info(f"======================================================================")

        # 1. Navigate to target chapter stage list
        if not self.navigator.navigate_to_chapter(chapter_num):
            logger.error(f"[!] Failed to navigate to Chapter {chapter_num}. Aborting cruiser.")
            return {"status": "FAILED", "reason": "Navigation failure", "cleared_stages": []}

        cleared_stages: List[str] = []
        consecutive_misses = 0

        for cycle in range(max_stages):
            if AbortController.is_aborted():
                logger.warning("🛑 [CampaignCruiser] Emergency stop signal detected. Halting cruiser...")
                return {"status": "CANCELLED", "reason": AbortController.get_reason(), "cleared_stages": cleared_stages}
            logger.info(f"\n--- [Campaign Cruise Step #{cycle+1}] ---")
            frame = self.client.screencap()

            # Check if any story dialogue is currently active
            if self.navigator.handle_story_skip():
                time.sleep(2.0)
                continue

            # Ensure we are in the correct chapter before scanning stages
            cur_ch = self.navigator.detect_current_chapter(frame)
            if cur_ch is not None and cur_ch != chapter_num:
                logger.warning(f"[!] Detected Chapter {cur_ch} on screen, but mission target is Chapter {chapter_num}! Re-routing...")
                if not self.navigator.navigate_to_chapter(chapter_num):
                    logger.error(f"[!] Re-navigation to Chapter {chapter_num} failed.")
                    time.sleep(2.0)
                    continue
                frame = self.client.screencap()

            # Identify target stage node on screen
            target_node = self._find_next_stage_node(frame, chapter_num, cleared_stages)

            if not target_node:
                # Swipe right on the map to reveal further stages
                logger.info("[*] No uncompleted stages in view. Swiping map rightwards...")
                self.client.swipe(1300, 540, 500, 540, 600)
                time.sleep(2.5)
                consecutive_misses += 1
                if consecutive_misses >= 3:
                    logger.info("[+] Chapter complete! No more pending stages detected.")
                    break
                continue

            consecutive_misses = 0
            code, (cx, cy) = target_node
            logger.info(f"[*] Targeting Stage [{code}] at ({cx}, {cy}). Tapping to open details...")
            self.client.tap(cx, cy)
            time.sleep(2.5)

            # Check if Stage Detail opened (Blue start button)
            detail_frame = self.client.screencap()
            scene = self.navigator.detect_scene(detail_frame)

            # If story popup or direct story
            if self.navigator.handle_story_skip():
                cleared_stages.append(f"{code} (Story Cleared)")
                time.sleep(2.0)
                continue

            # Tap Blue Start Action button at (1700, 920) or (1767, 987)
            logger.info(f"[*] Tapping Blue Start Action button...")
            self.client.tap(1700, 920)
            self.client.tap(1767, 987)
            time.sleep(2.5)

            # Check if Squad Confirm screen (Red start button at 1655, 780)
            sq_frame = self.client.screencap()
            logger.info(f"[*] Tapping Red Squad Start Action at (1655, 780)...")
            self.client.tap(1655, 780)
            time.sleep(4.0)

            # Check if enters Story before combat
            if self.navigator.handle_story_skip():
                time.sleep(2.0)

            # Execute Autonomous Combat
            logger.info(f"[*] Commencing combat for Stage [{code}]...")
            combat_res = self.pilot.run_combat(max_duration_sec=180)
            logger.info(f"[+] Combat finished: {combat_res}")

            cleared_stages.append(f"{code} ({combat_res['result']})")
            time.sleep(3.0)

        logger.info(f"======================================================================")
        logger.info(f"  ✅ Chapter {chapter_num} Campaign Cruiser finished! Cleared {len(cleared_stages)} stages.")
        logger.info(f"======================================================================")

        return {
            "status": "COMPLETED",
            "chapter": chapter_num,
            "cleared_count": len(cleared_stages),
            "cleared_stages": cleared_stages
        }

    def _find_next_stage_node(
        self,
        frame: np.ndarray,
        chapter: int,
        cleared_stages: List[str]
    ) -> Optional[tuple]:
        """Scan current frame for stage node code like '0-1', '0-2', etc."""
        res_all, _ = self.vision.ocr(frame) if self.vision.ocr else ([], None)
        if not res_all:
            return None

        pattern = re.compile(rf"^{chapter}-\d+$")
        candidates = []

        for item in res_all:
            box = item[0]
            val = item[1]
            text = val[0] if isinstance(val, (tuple, list)) else str(val)
            clean_text = text.strip().upper()
            if pattern.match(clean_text) or any(clean_text.startswith(f"{chapter}-{i}") for i in range(1, 20)):
                if not any(clean_text in s for s in cleared_stages):
                    pts = np.array(box).astype(int)
                    cx = int(np.mean(pts[:, 0]))
                    cy = int(np.mean(pts[:, 1]))
                    candidates.append((clean_text, (cx, cy)))

        if candidates:
            # Sort by x coordinate (left to right progression)
            candidates.sort(key=lambda item: item[1][0])
            return candidates[0]

        return None
