from core.abort_controller import AbortController
# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Autonomous Game Lifecycle Launcher & Popup Clearance Engine (Multi-Platform: Bilibili & Official)
Author: Emiliamio <mio2110767128@163.com>
"""

import time
import logging
import cv2
import numpy as np
from typing import Optional, Tuple, List

from core.adb_client import ADBClient
from core.vision_engine import VisionEngine

logger = logging.getLogger("ASTA.GameLauncher")

SUPPORTED_PACKAGES = [
    "com.hypergryph.arknights.bilibili",  # B服 (Bilibili)
    "com.hypergryph.arknights"             # 官服 (Official Hypergryph)
]


class GameLauncher:
    """
    Handles complete cold-start lifecycle of Arknights (Official & Bilibili):
    1. Auto-detects installed package (Bilibili / Official)
    2. ADB process launch (monkey / am start)
    3. Splash screen & hot-patch download wait
    4. Bilibili SDK / Wake-up login screen tap
    5. Auto-clearing all daily announcements, check-ins, and popups
    6. Confirmed landing on main Home dashboard
    """

    def __init__(self, adb_client: Optional[ADBClient] = None, vision_engine: Optional[VisionEngine] = None):
        self.client = adb_client or ADBClient(instance_index=0)
        self.vision = vision_engine or VisionEngine()
        self.package_name = self.detect_installed_package()
        logger.info(f"[*] GameLauncher initialized for target package: {self.package_name}")

    def detect_installed_package(self) -> str:
        """Probe connected device to find which Arknights flavor is installed."""
        try:
            out = self.client.shell("pm list packages arknights")
            for pkg in SUPPORTED_PACKAGES:
                if pkg in out:
                    return pkg
        except Exception as e:
            logger.warning(f"[!] Package detection query failed: {e}")
        # Default fallback to Bilibili server based on user environment
        return "com.hypergryph.arknights.bilibili"

    def is_game_running(self) -> bool:
        """Check if Arknights package process is currently alive in Android OS."""
        out = self.client.shell(f"pidof {self.package_name}")
        if out and out.strip().isdigit():
            return True
        ps_out = self.client.shell(f"ps -A | grep {self.package_name}")
        return self.package_name in (ps_out or "")

    def ensure_game_launched(self, max_wait_sec: int = 30, auto_launch_emulator: bool = False) -> bool:
        """Ensure MuMu emulator and Arknights are running in foreground."""
        # 1. Connect to emulator
        try:
            if not self.client.device_serial:
                if not self.client.is_instance_running():
                    if auto_launch_emulator:
                        logger.info("[*] MuMu 12 emulator not running. Auto-launching...")
                        self.client.connect(auto_launch=True)
                    else:
                        logger.info("[*] MuMu 12 模拟器未在运行，等待指挥官在桌面手动开启...")
                        return False
                else:
                    self.client.connect(auto_launch=False)
        except Exception as e:
            logger.warning(f"[!] Warning connecting to MuMu 12: {e}")
            return False

        # 2. Check if Arknights app is alive, cold launch if needed
        if not self.is_game_running():
            if hasattr(self.client, 'bring_mumu_to_foreground'): self.client.bring_mumu_to_foreground()
            logger.info(f"[*] Arknights ({self.package_name}) not running. Cold launching via ADB...")
            self.client.shell(f"monkey -p {self.package_name} -c android.intent.category.LAUNCHER 1")
            time.sleep(3.0)

        if hasattr(self.client, 'bring_mumu_to_foreground'): self.client.bring_mumu_to_foreground()
        logger.info(f"[*] Waiting for Arknights ({self.package_name}) splash & startup...")
        t0 = time.time()
        while time.time() - t0 < max_wait_sec:
            if self.is_game_running():
                return True
            time.sleep(1.0)
        return False

    def navigate_through_login_and_popups(self, max_attempts: int = 25) -> bool:
        """
        Loops through login clicks and popup closures until HOME screen is reached.
        Returns True if HOME reached, False if timeout.
        """
        logger.info("[*] Engaging Autonomous Login & Popup Annihilation Sentinels...")

        for attempt in range(max_attempts):
            if AbortController.is_aborted():
                logger.warning("🛑 [GameLauncher] Abort detected during login. Stopping launcher...")
                return False
            frame = self.client.screencap()
            if frame is None or frame.size == 0:
                time.sleep(1.5)
                continue

            # 1. Check if already at HOME screen
            if self.is_at_home_screen(frame):
                logger.info(f"[+] HOME SCREEN CONFIRMED on attempt #{attempt+1}!")
                return True

            # 2. Check for Bilibili / Official Login or Start screen ("开始唤醒" / "点击屏幕进入" / "START")
            if self._check_and_handle_login_screen(frame):
                time.sleep(4.0)
                continue

            # 3. Check for generic close / dismiss buttons (X or "关闭" / "确认" / "同意")
            closed_popup = self._check_and_dismiss_popups(frame)
            if closed_popup:
                time.sleep(1.5)
                continue

            # Neutral tap to advance fade-ins
            time.sleep(1.5)

        # Final check
        final_frame = self.client.screencap()
        return self.is_at_home_screen(final_frame)

    def is_at_home_screen(self, frame: np.ndarray) -> bool:
        """Determines if the current visual frame is the main Arknights home hub."""
        if frame is None or frame.size == 0:
            return False

        h, w = frame.shape[:2]
        crop_terminal = frame[int(h*0.12):int(h*0.35), int(w*0.55):int(w*0.85)]
        res, _ = self.vision.ocr(crop_terminal) if self.vision.ocr else ([], None)
        text_terminal = "".join(self._get_text(r) for r in (res or []))

        crop_bottom = frame[int(h*0.75):h, int(w*0.5):w]
        res_b, _ = self.vision.ocr(crop_bottom) if self.vision.ocr else ([], None)
        text_bottom = "".join(self._get_text(r) for r in (res_b or []))

        all_text = text_terminal + " " + text_bottom
        res_all, _ = self.vision.ocr(frame) if self.vision.ocr else ([], None)
        full_text = " ".join(self._get_text(r) for r in (res_all or []))

        # If an announcement popup is covering the screen, not yet at home
        if any(k in full_text for k in ["活动公告", "系统公告", "资讯速报"]):
            return False

        if any(k in all_text for k in ["终端", "作战", "TERMINAL", "基建", "干员"]):
            return True

        return False

    def _check_and_handle_login_screen(self, frame: np.ndarray) -> bool:
        """Check for Start Wakeup screen or Bilibili account confirmation and click to enter."""
        h, w = frame.shape[:2]
        # Crop bottom half all the way to bottom edge (capturing START rhombus at y=1020)
        crop_center = frame[int(h*0.4):h, int(w*0.2):int(w*0.8)]
        res, _ = self.vision.ocr(crop_center) if self.vision.ocr else ([], None)
        text = "".join(self._get_text(r) for r in (res or [])).upper()

        if any(k in text for k in ["开始唤醒", "点击屏幕", "START", "唤醒", "TOUCH", "进入游戏"]):
            logger.info("[*] Login / Start prompt detected. Tapping START button at (960, 960)...")
            self.client.tap(w // 2, int(h * 0.88))
            return True
        return False

    def _check_and_dismiss_popups(self, frame: np.ndarray) -> bool:
        """Search for popups (announcements, check-ins, user agreement) and close them."""
        h, w = frame.shape[:2]
        res_all, _ = self.vision.ocr(frame) if self.vision.ocr else ([], None)
        if not res_all:
            return False

        # Look for explicit close text buttons
        for item in res_all:
            box = item[0]
            text = self._get_text(item)
            if any(k in text for k in ["关闭", "CLOSE", "确认", "领取", "我知道了", "同意"]):
                pts = np.array(box).astype(int)
                cx = int(np.mean(pts[:, 0]))
                cy = int(np.mean(pts[:, 1]))
                logger.info(f"[*] Popup button '{text}' detected at ({cx}, {cy}). Tapping...")
                self.client.tap(cx, cy)
                return True

        # 2. Check for Arknights Announcement dialog with circular close 'X' at (1706, 97)
        all_words = " ".join(self._get_text(r) for r in res_all)
        if any(k in all_words for k in ["公告", "活动公告", "系统公告", "资讯速报", "更新公告", "活动", "更新", "签到", "月卡"]):
            logger.info("[*] Announcement modal detected. Tapping top-right close 'X' at (1706, 97)...")
            self.client.tap(1706, 97)
            time.sleep(1.0)
            return True

        return False

    def _get_text(self, ocr_item) -> str:
        val = ocr_item[1]
        if isinstance(val, (tuple, list)):
            return str(val[0])
        return str(val)
