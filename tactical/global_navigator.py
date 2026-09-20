# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
PRTS Global Hierarchy Scene Recognizer & Autonomous Navigator
Author: Emiliamio <mio2110767128@163.com>
"""

import time
import logging
from enum import Enum
from typing import Optional, Tuple, Dict, Any
import numpy as np

from core.adb_client import ADBClient
from core.vision_engine import VisionEngine, BattleState

logger = logging.getLogger("ASTA.GlobalNavigator")

def _get_ocr_text(res_item):
    val = res_item[1]
    if isinstance(val, (tuple, list)):
        return str(val[0])
    return str(val)


class SceneType(Enum):
    UNKNOWN = "UNKNOWN"
    HOME = "HOME"
    TERMINAL = "TERMINAL"
    MAIN_THEME = "MAIN_THEME"
    STAGE_LIST = "STAGE_LIST"
    STAGE_DETAIL = "STAGE_DETAIL"
    SQUAD_CONFIRM = "SQUAD_CONFIRM"
    STORY = "STORY"
    IN_BATTLE = "IN_BATTLE"
    SETTLEMENT = "SETTLEMENT"


class GlobalNavigator:
    """
    Automates scene recognition and hierarchical scene traversal:
    HOME ➔ TERMINAL ➔ MAIN_THEME ➔ CHAPTER_X ➔ STAGE_LIST
    """

    def __init__(self, adb_client: Optional[ADBClient] = None, vision_engine: Optional[VisionEngine] = None):
        self.client = adb_client or ADBClient(instance_index=0)
        self.vision = vision_engine or VisionEngine()

    def detect_scene(self, frame: np.ndarray) -> SceneType:
        """Detect current high-level Arknights UI scene using semantic visual OCR anchors."""
        if frame is None or frame.size == 0:
            return SceneType.UNKNOWN

        h, w = frame.shape[:2]
        res_all, _ = self.vision.ocr(frame) if self.vision.ocr else ([], None)
        all_text = " ".join(_get_ocr_text(r) for r in (res_all or []))

        # 1. Check Settlement
        if any(k in all_text for k in ["MISSION ACCOMPLISHED", "行动结束", "RESULTS", "EXP", "CLEAR"]):
            return SceneType.SETTLEMENT

        # 2. Check In-Battle
        if self.vision.detect_battle_state(frame) == BattleState.IN_BATTLE or "1X" in all_text or "2X" in all_text:
            return SceneType.IN_BATTLE

        # 3. Check Story Dialogue (Look for "跳过" / "SKIP" at top right)
        crop_top_right = frame[0:int(h*0.15), int(w*0.8):w]
        res_tr, _ = self.vision.ocr(crop_top_right) if self.vision.ocr else ([], None)
        tr_text = " ".join(_get_ocr_text(r) for r in (res_tr or []))
        if any(k in tr_text for k in ["跳过", "SKIP", "LOG", "AUTO"]):
            return SceneType.STORY

        # 4. Check Terminal Overview (category tabs: 资源收集 / 别传 / 插曲)
        if any(k in all_text for k in ["资源收集", "别传", "插曲"]):
            return SceneType.TERMINAL
        if ("MAIN THEME" in all_text or "集成战略" in all_text) and ("终端" in all_text or "RHODES" in all_text):
            return SceneType.TERMINAL

        # 5. Check Squad Confirm (Red start button at bottom right ~1655, 780)
        crop_squad = frame[int(h*0.65):int(h*0.85), int(w*0.75):w]
        res_sq, _ = self.vision.ocr(crop_squad) if self.vision.ocr else ([], None)
        sq_text = " ".join(_get_ocr_text(r) for r in (res_sq or []))
        if "开始行动" in sq_text:
            if any(k in all_text for k in ["编队", "队伍", "支援"]):
                return SceneType.SQUAD_CONFIRM
            return SceneType.STAGE_DETAIL

        # 6. Check Stage Detail (Blue start action button at ~1767, 987)
        crop_detail = frame[int(h*0.8):h, int(w*0.8):w]
        res_dt, _ = self.vision.ocr(crop_detail) if self.vision.ocr else ([], None)
        dt_text = " ".join(_get_ocr_text(r) for r in (res_dt or []))
        if "开始行动" in dt_text:
            return SceneType.STAGE_DETAIL

        # 7. Check Main Theme Chapter Select (specific episodes) / Stage List
        if any(k in all_text for k in ["主题曲", "黑暗时代", "觉醒", "残阳", "EPISODE", "序章", "OPERATION", "当前进度"]):
            import re
            if re.search(r'\d+-\d+', all_text) or "OPERATION" in all_text:
                return SceneType.STAGE_LIST
            return SceneType.MAIN_THEME

        # 8. Check Home Screen
        if any(k in all_text for k in ["终端", "作战", "基建", "干员", "采购中心"]):
            return SceneType.HOME

        return SceneType.UNKNOWN

    def navigate_to_terminal(self) -> bool:
        """Navigates from HOME to TERMINAL."""
        for _ in range(5):
            frame = self.client.screencap()
            scene = self.detect_scene(frame)
            if scene == SceneType.TERMINAL:
                return True
            # Auto-dismiss announcement if blocking HOME
            res_all, _ = self.vision.ocr(frame) if self.vision.ocr else ([], None)
            all_text = " ".join(_get_ocr_text(r) for r in (res_all or []))
            if any(k in all_text for k in ["活动公告", "系统公告", "资讯速报"]):
                logger.info("[*] Announcement popup blocking Terminal navigation. Tapping close 'X' at (1706, 97)...")
                self.client.tap(1706, 97)
                time.sleep(1.5)
                continue

            if scene == SceneType.HOME:
                logger.info("[*] At HOME. Tapping 终端 (Terminal) at (1250, 220)...")
                self.client.tap(1250, 220)
                time.sleep(2.0)
            else:
                self.return_to_home()
        return False

    def navigate_to_main_theme(self) -> bool:
        """Navigates from TERMINAL to MAIN_THEME chapter select."""
        if not self.navigate_to_terminal():
            return False

        for _ in range(5):
            frame = self.client.screencap()
            scene = self.detect_scene(frame)
            if scene in (SceneType.MAIN_THEME, SceneType.STAGE_LIST):
                return True
            if scene == SceneType.TERMINAL:
                logger.info("[*] At TERMINAL. Tapping 主题曲 (Main Theme) at (300, 500)...")
                self.client.tap(1050, 520)
                time.sleep(2.0)
        return False

    def detect_current_chapter(self, frame: np.ndarray) -> Optional[int]:
        """Infers the active chapter number from stage codes (e.g. 17-1 -> 17, 0-1 -> 0)."""
        import re
        res_all, _ = self.vision.ocr(frame) if self.vision.ocr else ([], None)
        if not res_all:
            return None

        all_text = " ".join(_get_ocr_text(r) for r in res_all)
        ep_match = re.search(r'EPISODE\s*0?(\d+)', all_text, re.IGNORECASE)
        if ep_match:
            return int(ep_match.group(1))

        stage_matches = re.findall(r'(\d+)-\d+', all_text)
        if stage_matches:
            from collections import Counter
            counts = Counter(int(m) for m in stage_matches)
            return counts.most_common(1)[0][0]

        return None

    def navigate_to_chapter(self, chapter_num: int) -> bool:
        """Selects a specific chapter (0, 1, 2, etc.) and enters its stage list."""
        logger.info(f"[*] Navigating to target Chapter {chapter_num}...")

        for attempt in range(25):
            frame = self.client.screencap()
            res_all, _ = self.vision.ocr(frame) if self.vision.ocr else ([], None)
            all_text = " ".join(_get_ocr_text(r) for r in (res_all or []))

            # 1. If trapped in Music/Event archive (has 曲谱 / 乐章收录 / 进入活动), reset to HOME
            if any(k in all_text for k in ["乐章收录", "进入活动", "追迹日落", "巴别塔", "曲谱"]):
                logger.info("[*] Detected non-combat archive screen. Resetting to HOME via (210, 50)...")
                self.client.tap(210, 50)
                time.sleep(2.5)
                continue

            # 2. Check if at HOME screen -> Tap Terminal
            if any(k in all_text for k in ["多汁炸鸡", "SANITY", "欢迎回家"]) and any(k in all_text for k in ["OPERATOR", "SQUADS", "MISSION"]):
                logger.info("[*] At HOME screen. Tapping Terminal / 作战 at (1300, 260)...")
                self.client.tap(1300, 260)
                time.sleep(2.5)
                continue

            # 3. Check if at Terminal Overview -> Tap MAIN THEME card at (1080, 550)
            if any(k in all_text for k in ["资源收集", "别传", "插曲", "MAIN THEME"]) and ("终端" in all_text or "PRTS" in all_text or "ROUTINE" in all_text):
                logger.info("[*] At Terminal Overview. Tapping MAIN THEME card at (1080, 550)...")
                self.client.tap(1080, 550)
                time.sleep(2.5)
                continue

            # 4. Check if already in target chapter's stage list
            scene = self.detect_scene(frame)
            if scene == SceneType.STAGE_LIST:
                cur_ch = self.detect_current_chapter(frame)
                if cur_ch == chapter_num:
                    logger.info(f"[+] Confirmed arrived at Chapter {chapter_num} STAGE_LIST!")
                    return True
                else:
                    logger.info(f"[*] In Chapter {cur_ch} stage list, not target {chapter_num}. Tapping back to cover...")
                    self.client.tap(60, 50)
                    time.sleep(2.0)
                    continue

            # 5. Check if on an Episode Cover screen (has 前往章节 / 本章回想)
            if "前往章节" in all_text or "本章回想" in all_text or "相变临界" in all_text or "反常光谱" in all_text:
                cur_ch = self.detect_current_chapter(frame)
                if cur_ch is None:
                    # Default heuristic from cover title if regex misses
                    cur_ch = 17 if "相变" in all_text else (16 if "反常" in all_text else 0)

                if cur_ch == chapter_num:
                    logger.info(f"[+] At Chapter {chapter_num} cover. Tapping 前往章节 at (1750, 860)...")
                    self.client.tap(1750, 860)
                    time.sleep(3.0)
                    continue
                elif cur_ch > chapter_num:
                    logger.info(f"[*] Current cover is Chapter {cur_ch} > target {chapter_num}. Tapping previous chapter at (120, 920)...")
                    self.client.tap(120, 920)
                    time.sleep(2.0)
                    continue
                else:
                    logger.info(f"[*] Current cover is Chapter {cur_ch} < target {chapter_num}. Tapping next chapter at (450, 920)...")
                    self.client.tap(450, 920)
                    time.sleep(2.0)
                    continue

            # Fallback tap back if stuck in arbitrary submenus
            logger.info("[*] In intermediate submenu. Tapping back at (60, 50)...")
            self.client.tap(60, 50)
            time.sleep(2.0)

        frame = self.client.screencap()
        cur_ch = self.detect_current_chapter(frame)
        return cur_ch == chapter_num

    def handle_story_skip(self) -> bool:
        """Detects story dialogue and clicks Skip -> Confirm."""
        frame = self.client.screencap()
        if self.detect_scene(frame) == SceneType.STORY:
            logger.info("[*] Story detected! Tapping top-right Skip at (1820, 60)...")
            self.client.tap(1820, 60)
            time.sleep(1.0)

            # Confirm dialog: Tap confirm "跳过" at (1300, 750)
            logger.info("[*] Confirming skip dialog at (1300, 750)...")
            self.client.tap(1300, 750)
            time.sleep(2.0)
            return True
        return False

    def return_to_home(self):
        """Repeatedly taps top-left Home/Back button until HOME screen is reached."""
        for _ in range(6):
            frame = self.client.screencap()
            if self.detect_scene(frame) == SceneType.HOME:
                return True
            logger.info("[*] Navigating backwards to HOME. Tapping top-left at (60, 50)...")
            self.client.tap(60, 50)
            time.sleep(1.5)
        return False
