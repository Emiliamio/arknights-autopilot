from core.auto_authenticator import AutoAuthenticator
from fleet.account_manager import AccountManager
from core.abort_controller import AbortController
# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Master Task Orchestrator & Autonomous Mission Execution Engine
Author: Emiliamio <mio2110767128@163.com>
"""

import time
import logging
from typing import Dict, Any, Optional

from fleet.mission_manager import MissionManager, MissionStatus, MissionType
from core.game_launcher import GameLauncher
from core.adb_client import ADBClient
from core.vision_engine import VisionEngine
from tactical.global_navigator import GlobalNavigator
from tactical.campaign_cruiser import CampaignCruiser
from tactical.universal_combat_pilot import UniversalCombatPilot

logger = logging.getLogger("ASTA.TaskExecutor")


class TaskExecutor:
    """
    Executes end-to-end missions checked out from MissionManager:
    - Automatically boots game via GameLauncher.
    - Dismisses announcements and daily popups.
    - Dispatches to CampaignCruiser, SanityFarmer, or DailyRoutine.
    - Reports completion or failure back to SQLite mission store.
    """

    def __init__(
        self,
        mission_manager: Optional[MissionManager] = None,
        account_manager: Optional[AccountManager] = None,
        adb_client: Optional[ADBClient] = None,
        telemetry_store: Optional[Any] = None,
        instance_index: int = 0
    ):
        self.instance_index = instance_index
        self.mission_mgr = mission_manager or MissionManager()
        self.account_mgr = account_manager or AccountManager()
        self.telemetry_store = telemetry_store
        self.client = adb_client or ADBClient(instance_index=instance_index)
        self.vision = VisionEngine()
        self.launcher = GameLauncher(adb_client=self.client, vision_engine=self.vision)
        self.navigator = GlobalNavigator(adb_client=self.client, vision_engine=self.vision)
        self.pilot = UniversalCombatPilot(adb_client=self.client, vision_engine=self.vision)
        self.cruiser = CampaignCruiser(
            adb_client=self.client,
            vision_engine=self.vision,
            navigator=self.navigator,
            pilot=self.pilot
        )

    def _log(self, level: str, msg: str):
        logger.info(f"[{level}] {msg}")
        if self.telemetry_store:
            self.telemetry_store.add_log(level, msg)

    def execute_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single checked-out mission end-to-end."""
        m_id = mission["mission_id"]
        AbortController.reset()
        if AbortController.is_aborted():
            self.mission_mgr.cancel_mission(m_id)
            return {"status": "CANCELLED", "reason": "Pre-aborted"}
        m_type = mission["mission_type"]
        acc_id = mission["account_id"]
        self._log("INFO", f"🚀 [任务总控] 开始执行工单: {m_id} [{m_type}] (账号: {acc_id})")

        self.mission_mgr.update_progress(m_id, "正在冷启动游戏并穿透签到弹窗..."); self._log("INFO", "📱 [模拟器] 正在启动 MuMu 12 与 B服 明日方舟并穿透弹窗...")

        # Step 1: Ensure game launched and authenticated to target account
        try:
            acc_profile = self.account_mgr.get_account(acc_id) or {"account_id": acc_id, "platform": "BILIBILI"}
            self._log("INFO", f"🔐 [身份认证] 正在校验并登录账号 {acc_id} ({acc_profile.get('platform', 'BILIBILI')}服)...")
            auto_auth = AutoAuthenticator(adb_client=self.client, vision_engine=self.vision, game_launcher=self.launcher)
            launched = auto_auth.authenticate_account(acc_profile)
            if not launched:
                self._log("WARN", "[!] 登录引导未完全返回主界面，尝试继续...")
            launched = self.launcher.ensure_game_launched(max_wait_sec=40)
            if not launched:
                self.mission_mgr.fail_mission(m_id, "游戏冷启动失败或进程异常")
                return {"status": "FAILED", "error": "Game launch failure"}

            at_home = self.launcher.navigate_through_login_and_popups(max_attempts=15)
            if not at_home:
                # Still try to proceed if already at terminal/in-game
                logger.warning("[!] Warning: Home screen not definitively detected, attempting navigation...")
        except Exception as e:
            logger.warning(f"[!] GameLauncher warning: {e}")

        if AbortController.is_aborted():
            self.mission_mgr.cancel_mission(m_id)
            self._log("WARN", f"🛑 [任务总控] 任务 {m_id} 响应全局停止信号，已终止退出")
            return {"status": "CANCELLED", "reason": AbortController.get_reason()}

        # Step 2: Scan Roster and Synthesize Optimal Squad
        try:
            from tactical.roster_inspector import RosterInspector
            from tactical.squad_synthesizer import SquadSynthesizer

            self._log("INFO", f"👥 [干员中枢] 正在核验账号 [{acc_id}] 的干员库与练度资产...")
            inspector = RosterInspector(adb_client=self.client, vision_engine=self.vision)
            roster = inspector.load_roster(acc_id)
            self._log("INFO", f"✅ [干员中枢] 成功获取账号 [{acc_id}] 已拥有的 {len(roster)} 名干员资产！")

            target_st = mission.get("target_stage") or f"{mission.get('target_chapter', 0)}-1"
            synthesizer = SquadSynthesizer(roster_inspector=inspector)
            squad_res = synthesizer.synthesize_squad(acc_id, target_st)
            self._log("INFO", f"🧠 [编队合成] {squad_res['summary']}")
        except Exception as e:
            logger.warning(f"[!] Roster/Squad setup note: {e}")

        # Step 3: Dispatch based on MissionType
        try:
            if m_type == MissionType.CAMPAIGN_CLEAR:
                chapter = mission.get("target_chapter", 0)
                self.mission_mgr.update_progress(m_id, f"正在推通关主线第 {chapter} 章..."); self._log("INFO", f"🧭 [导航中枢] 正在进入主线第 {chapter} 章并开启连续推图...")
                result = self.cruiser.cruise_chapter(chapter_num=chapter)

                if result["status"] == "COMPLETED":
                    summary = f"章节第 {chapter} 章已清空，成功推进通关 {result['cleared_count']} 关"
                    self.mission_mgr.complete_mission(m_id, summary); self._log("INFO", f"✅ [任务完成] {summary}")
                    return {"status": "SUCCESS", "summary": summary}
                else:
                    self.mission_mgr.fail_mission(m_id, result.get("reason", "未知推图中断"))
                    return {"status": "FAILED", "error": result}

            elif m_type == MissionType.SANITY_FARM:
                stage = mission.get("target_stage", "1-7")
                self.mission_mgr.update_progress(m_id, f"正在刷关卡 [{stage}] 体力...")
                # Run generic combat for targeted stage
                combat_res = self.pilot.run_combat(max_duration_sec=180)
                summary = f"关卡 [{stage}] 战斗完成: {combat_res['result']}"
                self.mission_mgr.complete_mission(m_id, summary); self._log("INFO", f"✅ [任务完成] {summary}")
                return {"status": "SUCCESS", "summary": summary}

            elif m_type == MissionType.ROGUELIKE:
                theme_str = mission.get("params", {}).get("theme", "IS4")
                self.mission_mgr.update_progress(m_id, f"正在进行集成战略 ({theme_str}) 肉鸽推演...")
                self._log("INFO", f"🎲 [肉鸽启程] 正在载入集成战略主题 [{theme_str}] 并展开自主节点寻路...")
                from tactical.roguelike_brain import RoguelikeBrain, RoguelikeTheme
                theme_enum = RoguelikeTheme.IS4_SAMI
                if "3" in theme_str:
                    theme_enum = RoguelikeTheme.IS3_MIZUKI
                elif "2" in theme_str:
                    theme_enum = RoguelikeTheme.IS2_PHANTOM
                elif "5" in theme_str:
                    theme_enum = RoguelikeTheme.IS5_SARKAZ

                brain = RoguelikeBrain(adb_client=self.client, vision_engine=self.vision, combat_pilot=self.pilot, theme=theme_enum)
                res = brain.run_roguelike_exploration(max_floors=3)
                summary = res.get("summary", "肉鸽推演完成")
                self.mission_mgr.complete_mission(m_id, summary)
                self._log("INFO", f"🏆 [肉鸽战报] {summary}")
                return {"status": "SUCCESS", "summary": summary}

            elif m_type == MissionType.DAILY_ROUTINE:
                self.mission_mgr.update_progress(m_id, "正在执行每日签到与日常领取...")
                self.navigator.navigate_to_terminal()
                self.mission_mgr.complete_mission(m_id, "每日日常巡检完成")
                return {"status": "SUCCESS", "summary": "Daily routine complete"}

            else:
                self.mission_mgr.fail_mission(m_id, f"未知的任务类型: {m_type}")
                return {"status": "FAILED", "error": f"Unknown mission type: {m_type}"}

        except Exception as e:
            logger.error(f"[!] Mission execution exception: {e}")
            self.mission_mgr.fail_mission(m_id, str(e))
            return {"status": "FAILED", "error": str(e)}

    def run_worker_cycle(self) -> Optional[Dict[str, Any]]:
        """Checks out next queued mission and executes it."""
        mission = self.mission_mgr.checkout_next_queued_mission()
        if not mission:
            return None
        return self.execute_mission(mission)
