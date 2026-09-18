# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
In-Combat Vision Perception Engine (RapidOCR & ROI Extraction)
Author: Emiliamio <mio2110767128@163.com>
"""

from enum import IntEnum
from typing import List, Tuple, Dict, Any, Optional
import re
import numpy as np
import cv2

try:
    from rapidocr_onnxruntime import RapidOCR
    HAS_RAPIDOCR = True
except ImportError:
    HAS_RAPIDOCR = False


class BattleState(IntEnum):
    """Lifecycle states of the combat view."""
    UNKNOWN = 0
    PRE_BATTLE = 1        # Squad formation or 'Start Action' screen
    IN_BATTLE = 2         # Active combat (DP active, enemies spawning)
    VICTORY = 3           # 3-star clear / Mission Accomplished screen
    DEFEAT = 4            # Mission Failed screen
    PAUSED = 5            # Game paused menu


class VisionEngine:
    """
    Real-time visual perception engine for Arknights combat.
    Processes 1080P/720P frames to extract:
    1. Deployment Points (DP / Cost);
    2. Kill Count (e.g. 15/35);
    3. Global Battle Lifecycle State;
    4. Deployable Hand Operator Cards;
    5. 2x Speed Status.
    """

    ROI_NORMS = {
        "cost": (0.920, 0.890, 0.990, 0.985),         # Bottom-right DP counter
        "kill_count": (0.700, 0.020, 0.800, 0.075),   # Top-bar kill counter (XX/YY)
        "speed_toggle": (0.835, 0.020, 0.880, 0.075), # Top-bar 2x speed button
        "pause_btn": (0.940, 0.020, 0.985, 0.075),    # Top-right pause button
        "hand_cards": (0.180, 0.860, 0.900, 0.995),   # Bottom row hand cards
        "center_banner": (0.250, 0.350, 0.750, 0.650) # Victory/Defeat central banner
    }

    def __init__(self, ocr_engine: Optional[Any] = None):
        if ocr_engine is not None:
            self.ocr = ocr_engine
        elif HAS_RAPIDOCR:
            self.ocr = RapidOCR()
        else:
            self.ocr = None

        self._cost_history: List[int] = []

    def get_roi_crop(self, frame: np.ndarray, roi_name: str) -> np.ndarray:
        """Extracts cropped sub-image corresponding to a normalized ROI name."""
        if roi_name not in self.ROI_NORMS:
            raise KeyError(f"Unknown ROI name: {roi_name}")

        h, w = frame.shape[:2]
        nx1, ny1, nx2, ny2 = self.ROI_NORMS[roi_name]
        x1, y1 = max(0, int(round(nx1 * w))), max(0, int(round(ny1 * h)))
        x2, y2 = min(w, int(round(nx2 * w))), min(h, int(round(ny2 * h)))
        return frame[y1:y2, x1:x2]

    def read_cost(self, frame: np.ndarray) -> Optional[int]:
        """
        Extracts current Deployment Points (DP, 0~99) from the bottom-right counter.
        Solves digit kerning splits (e.g. '1 8' -> 18) by concatenating numeric tokens.
        """
        crop = self.get_roi_crop(frame, "cost")
        if crop.size == 0:
            return None

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_LINEAR)
        _, thresh = cv2.threshold(resized, 160, 255, cv2.THRESH_BINARY)

        extracted_text = ""
        if self.ocr:
            try:
                ocr_input = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
                ocr_res, _ = self.ocr(ocr_input)
                if ocr_res:
                    for item in ocr_res:
                        extracted_text += item[1] + " "
            except Exception:
                pass

        # Concatenate all separated digit fragments to avoid kerning split bug
        digit_fragments = re.findall(r"\d+", extracted_text)
        if digit_fragments:
            merged_str = "".join(digit_fragments)
            try:
                val = int(merged_str)
                # If merged string has more than 2 digits (e.g. noise like 100), take last 2 digits
                if val > 99:
                    val = int(merged_str[-2:])
                if 0 <= val <= 99:
                    self._cost_history.append(val)
                    if len(self._cost_history) > 5:
                        self._cost_history.pop(0)
                    return val
            except ValueError:
                pass

        return self._cost_history[-1] if self._cost_history else None

    def read_kill_count(self, frame: np.ndarray) -> Tuple[Optional[int], Optional[int]]:
        """Extracts current kill count and total enemies (e.g. (15, 35) from '15/35')."""
        crop = self.get_roi_crop(frame, "kill_count")
        if crop.size == 0 or not self.ocr:
            return None, None

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_LINEAR)
        _, thresh = cv2.threshold(resized, 160, 255, cv2.THRESH_BINARY)

        ocr_input = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
        extracted = ""
        try:
            ocr_res, _ = self.ocr(ocr_input)
            if ocr_res:
                for item in ocr_res:
                    extracted += item[1] + " "
        except Exception:
            return None, None

        match = re.search(r"(\d+)\s*/\s*(\d+)", extracted)
        if match:
            return int(match.group(1)), int(match.group(2))

        return None, None

    def is_2x_speed_active(self, frame: np.ndarray) -> bool:
        """Checks whether 2x combat speed is toggled ON."""
        crop = self.get_roi_crop(frame, "speed_toggle")
        if crop.size == 0:
            return False
        # When 2x speed is active in Arknights, the button has higher blue/white brightness
        mean_b = float(np.mean(crop[:, :, 0]))
        mean_g = float(np.mean(crop[:, :, 1]))
        mean_r = float(np.mean(crop[:, :, 2]))
        # 2x indicator glowing has average brightness > 45
        return (mean_b + mean_g + mean_r) / 3.0 > 45.0

    def detect_battle_state(self, frame: np.ndarray) -> BattleState:
        """Classifies current visual state into BattleState enum."""
        h, w = frame.shape[:2]

        # 1. Check Victory / Defeat center banner (Highest Priority)
        banner_crop = self.get_roi_crop(frame, "center_banner")
        if self.ocr and banner_crop.size > 0:
            try:
                ocr_res, _ = self.ocr(banner_crop)
                if ocr_res:
                    full_text = " ".join(item[1].upper() for item in ocr_res)
                    if any(k in full_text for k in ["MISSION ACCOMPLISHED", "ACCOMPLISHED", "行动结束", "三星", "COMPLETE"]):
                        return BattleState.VICTORY
                    if any(k in full_text for k in ["MISSION FAILED", "FAILED", "行动失败", "DEFEAT"]):
                        return BattleState.DEFEAT
            except Exception:
                pass

        # 2. Check In-Battle markers (Cost Counter + Pause button existence)
        pause_crop = self.get_roi_crop(frame, "pause_btn")
        if pause_crop.size > 0 and float(np.mean(pause_crop)) > 15.0:
            cost_val = self.read_cost(frame)
            if cost_val is not None:
                return BattleState.IN_BATTLE

        cost_crop = self.get_roi_crop(frame, "cost")
        if cost_crop.size > 0 and float(np.mean(cost_crop)) > 8.0:
            cost_val = self.read_cost(frame)
            if cost_val is not None:
                return BattleState.IN_BATTLE

        # 3. Check Pre-Battle markers (Start Action red button in bottom right)
        br_crop = frame[int(h * 0.85):, int(w * 0.80):]
        if br_crop.size > 0:
            red_mask = (br_crop[:, :, 2] > 140) & (br_crop[:, :, 0] < 80) & (br_crop[:, :, 1] < 80)
            red_ratio = np.sum(red_mask) / float(br_crop.shape[0] * br_crop.shape[1])
            if red_ratio > 0.08:
                return BattleState.PRE_BATTLE

        return BattleState.UNKNOWN

    def detect_deployable_cards(
        self,
        frame: np.ndarray,
        num_slots: int = 8
    ) -> List[Dict[str, Any]]:
        """Scans the bottom hand cards row and identifies cards ready for deployment."""
        h, w = frame.shape[:2]
        nx1, ny1, nx2, ny2 = self.ROI_NORMS["hand_cards"]
        x1, y1 = int(round(nx1 * w)), int(round(ny1 * h))
        x2, y2 = int(round(nx2 * w)), int(round(ny2 * h))

        hand_width = x2 - x1
        slot_width = hand_width // num_slots

        deployable_cards = []
        for i in range(num_slots):
            sx1 = x1 + i * slot_width
            sx2 = sx1 + slot_width
            slot_crop = frame[y1:y2, sx1:sx2]
            if slot_crop.size == 0:
                continue

            hsv = cv2.cvtColor(slot_crop, cv2.COLOR_BGR2HSV)
            val_mean = float(np.mean(hsv[:, :, 2]))
            sat_mean = float(np.mean(hsv[:, :, 1]))

            center_x = (sx1 + sx2) // 2
            center_y = (y1 + y2) // 2

            is_ready = (val_mean > 70.0 and sat_mean > 35.0)

            deployable_cards.append({
                "slot_index": i,
                "center": (center_x, center_y),
                "is_ready": is_ready,
                "brightness": round(val_mean, 1),
                "saturation": round(sat_mean, 1)
            })

        return deployable_cards