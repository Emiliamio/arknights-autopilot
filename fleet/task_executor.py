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

            elif m_type == MissionType.COPILOT_CLEAR or (m_type == MissionType.SANITY_FARM and mission.get("params", {}).get("copilot_plan")):
                stage = mission.get("target_stage", "1-7")
                plan_path = mission.get("params", {}).get("copilot_plan")
                self.mission_mgr.update_progress(m_id, f"正在进行关卡 [{stage}] Route A 智能作业推演与通关...")
                self._log("INFO", f"⚔️ [Route A 作业通关] 正在锁定目标关卡 [{stage}] 并准备作业协议...")

                # Resolve Copilot Plan
                from tactical.copilot_cloud_hub import CopilotCloudHub
                from tactical.copilot_adapter import CopilotAdapter
                from tactical.copilot_brain import CopilotBrain
                from tactical.map_deconstructor import TacticalMap

                hub = CopilotCloudHub()
                if plan_path and os.path.exists(plan_path):
                    plan = CopilotAdapter.load_file(plan_path)
                else:
                    self._log("INFO", f"🌐 [云端检索] 本地未指定作业，正在全网智能检索 [{stage}] 最高赞通关作业...")
                    plan, plan_path = hub.auto_resolve_best_plan(stage)
                    self._log("INFO", f"📥 [云端抓取] 成功命中并下载作业: '{plan.title}' ({len(plan.actions)} 步动作)")

                # Load Account Roster for Fuzzy Substitution
                acc_profile = self.account_mgr.get_account(acc_id)
                roster = None
                if acc_profile and acc_profile.get("owned_roster"):
                    roster = acc_profile["owned_roster"]
                else:
                    from tactical.roster_inspector import RosterInspector
                    inspector = RosterInspector(adb_client=self.client, vision_engine=self.vision)
                    roster_data = inspector.load_roster(acc_id)
                    if roster_data:
                        roster = [op["name"] for op in roster_data if "name" in op]

                # Initialize Tactical Map and CopilotBrain
                t_map = TacticalMap.create_1_7()
                brain = CopilotBrain(tactical_map=t_map, copilot_plan=plan, owned_roster=roster)
                if brain.substitutions:
                    self._log("INFO", f"🎯 [干员平替] 已自适应替换干员: {brain.substitutions}")

                # Enter battlefield via pilot
                entered = self.pilot.enter_and_wait_battlefield(max_wait_sec=35)
                if not entered:
                    self.mission_mgr.fail_mission(m_id, "未能成功进入战斗场景")
                    return {"status": "FAILED", "error": "Battlefield entrance timeout"}

                # Update TelemetryStore with initial copilot steps
                if self.telemetry_store:
                    steps_view = []
                    for idx, act in enumerate(brain.plan.actions):
                        steps_view.append({
                            "step": idx + 1,
                            "name": act.name or act.action_type.value,
                            "action": act.action_type.value,
                            "tile": [act.col, act.row],
                            "cost": act.min_costs,
                            "status": "PENDING"
                        })
                    self.telemetry_store.copilot_name = plan.title or stage
                    self.telemetry_store.copilot_steps = steps_view
                    self.telemetry_store.battle_state = "IN_BATTLE"
                    self.telemetry_store.stage_id = stage

                # Run Real-Time Copilot Loop
                battle_t0 = time.time()
                max_duration = 300
                combat_res = "TIMEOUT"

                while time.time() - battle_t0 < max_duration:
                    if AbortController.is_aborted():
                        self.mission_mgr.cancel_mission(m_id)
                        return {"status": "CANCELLED", "reason": AbortController.get_reason()}

                    frame = self.client.screencap()
                    res = brain.tick(
                        frame=frame,
                        vision_engine=self.vision,
                        mapper=self.pilot.mapper,
                        humanizer=self.pilot.humanizer,
                        adb_client=self.client
                    )

                    # Update Web Telemetry Store in real time
                    if self.telemetry_store:
                        self.telemetry_store.dp = res.get("current_dp", self.telemetry_store.dp)
                        if res.get("kill_count") and res["kill_count"][0] is not None:
                            self.telemetry_store.kill_count = list(res["kill_count"])
                        self.telemetry_store.current_step_idx = brain.current_action_idx

                    action_taken = res.get("action_taken", "NONE")
                    if action_taken != "NONE":
                        self._log("INFO", f"⚔️ [作业执行] {action_taken} | 进度: {res.get('copilot_progress')}")
                        self.mission_mgr.update_progress(m_id, f"执行动作: {action_taken} ({res.get('copilot_progress')})")

                    if res.get("status") == "EMERGENCY_INTERVENING":
                        self._log("WARN", f"🚨 [PanicDaemon 救场] 探测到突发防线威胁，毫秒级空投干员拦截!")
                        if self.telemetry_store:
                            self.telemetry_store.threat_level = "ALERT"

                    if res.get("status") == "COMPLETED":
                        settle = res.get("action_details", {}).get("settlement", "VICTORY")
                        combat_res = settle
                        self._log("INFO", f"🏆 [战斗结束] 判定状态: {settle}!")
                        if self.telemetry_store:
                            self.telemetry_store.battle_state = settle
                        time.sleep(1.5)
                        self.client.tap(960, 540)
                        time.sleep(1.5)
                        self.client.tap(960, 540)
                        break

                    time.sleep(0.35)

                summary = f"关卡 [{stage}] Route A 作业通关完成: {combat_res} (进度 {brain.current_action_idx}/{len(brain.plan.actions)})"
                self.mission_mgr.complete_mission(m_id, summary)
                self._log("INFO", f"✅ [任务完成] {summary}")
                return {"status": "SUCCESS", "summary": summary}

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
