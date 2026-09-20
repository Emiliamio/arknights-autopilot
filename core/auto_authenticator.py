# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Autonomous Game Login & Account Switching Engine (Bilibili & Official Support)
Author: Emiliamio <mio2110767128@163.com>
"""

import time
import logging
from typing import Dict, Any, Optional

from core.adb_client import ADBClient
from core.vision_engine import VisionEngine
from core.game_launcher import GameLauncher

logger = logging.getLogger("ASTA.AutoAuthenticator")


class AutoAuthenticator:
    """
    Automates credential entry and account switching for both Bilibili and Official servers:
    1. Distinguishes server flavors and launches target APK package.
    2. Switches active account if another user is logged in.
    3. Types customer credentials via non-invasive ADB input stream.
    4. Confirms user agreement and clears post-login popups.
    """

    def __init__(
        self,
        adb_client: Optional[ADBClient] = None,
        vision_engine: Optional[VisionEngine] = None,
        game_launcher: Optional[GameLauncher] = None
    ):
        self.client = adb_client or ADBClient(instance_index=0)
        self.vision = vision_engine or VisionEngine()
        self.launcher = game_launcher or GameLauncher(adb_client=self.client, vision_engine=self.vision)

    def authenticate_account(self, account_profile: Dict[str, Any]) -> bool:
        """
        Takes an account dictionary from data/accounts.db and logs into Arknights.
        """
        acc_id = account_profile.get("account_id")
        platform = account_profile.get("platform", "BILIBILI").upper()
        login_user = account_profile.get("login_account")
        login_pwd = account_profile.get("login_password")

        logger.info(f"[*] Commencing authentication sequence for {acc_id} (Platform: {platform})...")

        # 1. Target correct APK flavor with automatic device fallback
        desired_pkg = "com.hypergryph.arknights.bilibili" if platform == "BILIBILI" else "com.hypergryph.arknights"
        installed_out = self.client.shell("pm list packages arknights")
        
        if desired_pkg in installed_out:
            self.launcher.package_name = desired_pkg
        else:
            # Fallback to installed package flavor
            if "com.hypergryph.arknights.bilibili" in installed_out:
                self.launcher.package_name = "com.hypergryph.arknights.bilibili"
                logger.info(f"[*] Fallback to installed Bilibili package: {self.launcher.package_name}")
            elif "com.hypergryph.arknights" in installed_out:
                self.launcher.package_name = "com.hypergryph.arknights"
                logger.info(f"[*] Fallback to installed Official package: {self.launcher.package_name}")
            else:
                self.launcher.package_name = desired_pkg

        # 2. Boot game
        if not self.launcher.ensure_game_launched():
            logger.error(f"[!] Failed to launch package {self.launcher.package_name}")
            return False

        time.sleep(3.0)
        frame = self.client.screencap()

        # 3. Check if already at Home screen
        if self.launcher.is_at_home_screen(frame):
            logger.info("[*] Game already logged in at Home. Checking if account switch is needed...")
            if not login_user:
                # If no credentials provided, assume existing session is target
                logger.info("[+] Reusing existing logged-in session.")
                return True
            # Otherwise perform logout switch
            self._perform_logout_switch()
            time.sleep(4.0)

        # 4. Perform Credential Typing on Login Dialog if credentials provided
        if login_user and login_pwd:
            self._type_credentials(login_user, login_pwd, platform)

        # 5. Navigate through Wakeup & popups to Home
        success = self.launcher.navigate_through_login_and_popups(max_attempts=15)
        if success:
            logger.info(f"[+] Account {acc_id} successfully authenticated and arrived at Home screen!")
        return success

    def _type_credentials(self, username: str, password: str, platform: str):
        """Input username and password into server login dialog."""
        logger.info(f"[*] Entering credentials for platform {platform}...")
        time.sleep(2.0)
        frame = self.client.screencap()
        h, w = frame.shape[:2]

        # Standard login dialog field relative positions on 1920x1080:
        # Username input box: ~ (960, 420)
        # Password input box: ~ (960, 520)
        # Login button: ~ (960, 620)

        logger.info("[*] Tapping account input field...")
        self.client.tap(w // 2, int(h * 0.40))
        time.sleep(0.8)
        self.client.shell(f"input text {username}")
        time.sleep(0.8)

        logger.info("[*] Tapping password input field...")
        self.client.tap(w // 2, int(h * 0.50))
        time.sleep(0.8)
        self.client.shell(f"input text {password}")
        time.sleep(0.8)

        logger.info("[*] Tapping Login / Confirm button...")
        self.client.tap(w // 2, int(h * 0.60))
        time.sleep(3.0)

    def _perform_logout_switch(self):
        """Navigate to Settings and tap Switch Account."""
        logger.info("[*] Performing logout / switch account sequence...")
        # Tap top-left settings gear (approx 60, 50)
        self.client.tap(60, 50)
        time.sleep(1.5)
        # Tap "退出登录" / "账号中心" (approx 960, 850)
        self.client.tap(960, 850)
        time.sleep(1.5)
        # Confirm logout dialog (approx 1150, 650)
        self.client.tap(1150, 650)
        time.sleep(3.0)
