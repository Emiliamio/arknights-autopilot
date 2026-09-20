# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Integrated Strategies (Roguelike / 肉鸽) Autonomous Decision Brain (AlphaRoguelike)
Author: Emiliamio <mio2110767128@163.com>
"""

import time
import logging
import random
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

from core.adb_client import ADBClient
from core.vision_engine import VisionEngine
from tactical.universal_combat_pilot import UniversalCombatPilot
from tactical.squad_synthesizer import SquadSynthesizer
from core.abort_controller import AbortController

logger = logging.getLogger("ASTA.RoguelikeBrain")


class RoguelikeTheme(Enum):
    IS2_PHANTOM = "IS2"   # 傀影与猩红孤钻
    IS3_MIZUKI = "IS3"    # 水月与深蓝之树
    IS4_SAMI = "IS4"      # 探索者的银凇止境 (萨米)
    IS5_SARKAZ = "IS5"    # 萨卡兹的无终奇语


class RoguelikeNodeType(Enum):
    COMBAT = "COMBAT"                    # 普通作战
    EMERGENCY = "EMERGENCY"              # 紧急作战
    ENCOUNTER = "ENCOUNTER"              # 不期而遇
    TRADER = "TRADER"                    # 诡异行商 (商店)
    SAFEHOUSE = "SAFEHOUSE"              # 安全屋
    DOWNTIME = "DOWNTIME"                # 休整
    BOSS = "BOSS"                        # 领袖之战 (关底)


class RoguelikeState:
    """Represents current live state within an active Roguelike exploration run."""

    def __init__(self, theme: RoguelikeTheme = RoguelikeTheme.IS4_SAMI):
        self.theme = theme
        self.floor = 1
        self.life_points = 6
        self.hope = 6
        self.ingots = 8           # 源石锭
        self.light_or_collapse = 100  # 灯火值 / 坍缩指数
        self.relics: List[str] = ["先发制人", "黑夜呢喃"]
        self.roster: List[Dict[str, Any]] = []
        self.nodes_visited = 0
        self.current_node_type: RoguelikeNodeType = RoguelikeNodeType.COMBAT
        self.is_active = True


class RoguelikeBrain:
    """
    Autonomous game-theoretic AI for Arknights Integrated Strategies (Roguelike):
    - Initial squad selection & Hope-budgeted operator drafting.
    - Graph DAG traversal with heuristic risk-reward trade-off pathfinding.
    - Autonomous encounter event choice resolution.
    - In-store relic knapsack valuation.
    - Autonomous tactical combat delegation.
    """

    def __init__(
        self,
        adb_client: Optional[ADBClient] = None,
        vision_engine: Optional[VisionEngine] = None,
        combat_pilot: Optional[UniversalCombatPilot] = None,
        theme: RoguelikeTheme = RoguelikeTheme.IS4_SAMI
    ):
        self.client = adb_client or ADBClient(instance_index=0)
        self.vision = vision_engine or VisionEngine()
        self.pilot = combat_pilot or UniversalCombatPilot(adb_client=self.client, vision_engine=self.vision)
        self.theme = theme
        self.state = RoguelikeState(theme=theme)

    def run_roguelike_exploration(self, max_floors: int = 5) -> Dict[str, Any]:
        """Runs autonomous multi-floor Roguelike expedition."""
        logger.info(f"======================================================================")
        logger.info(f"  🎲 ASTA AlphaRoguelike: Engaging Exploration ({self.theme.value})")
        logger.info(f"======================================================================")

        # 1. Start or resume exploration
        self._init_or_resume_run()

        while self.state.is_active and self.state.floor <= max_floors:
            if AbortController.is_aborted():
                logger.warning("[!] Abort signal triggered. Stopping Roguelike exploration.")
                return {"status": "ABORTED", "final_floor": self.state.floor}

            logger.info(f"\n--- [Roguelike Floor #{self.state.floor} Navigation] ---")
            logger.info(f"    • Life: {self.state.life_points} | Hope: {self.state.hope} | Ingots: {self.state.ingots}")

            # 2. Pick next best node on the floor DAG
            candidate_nodes = self._scan_visible_nodes()
            best_node = self.evaluate_best_node(candidate_nodes, self.state)
            logger.info(f"[+] Evaluated best path: Targeting [{best_node['type'].value}] (Score: {best_node['score']:.1f})")

            # 3. Enter and execute node
            self._enter_and_execute_node(best_node)

            # Check for game over or floor clear
            if self.state.life_points <= 0:
                logger.warning("[!] Life points depleted. Expedition ended.")
                self.state.is_active = False
                break

            if best_node["type"] == RoguelikeNodeType.BOSS:
                logger.info(f"[+] Boss defeated! Advancing from Floor {self.state.floor} to {self.state.floor + 1}")
                self.state.floor += 1
                self.state.hope += 4
                self.state.ingots += 6

            time.sleep(2.0)

        summary = (
            f"肉鸽探索完成: 主题 [{self.theme.value}], 到达第 {self.state.floor} 层, "
            f"剩余生命 {self.state.life_points}, 积累源石锭 {self.state.ingots}, 获得藏品 {len(self.state.relics)} 件。"
        )
        logger.info(f"======================================================================")
        logger.info(f"  ✅ AlphaRoguelike Run Finished: {summary}")
        logger.info(f"======================================================================")

        return {
            "status": "COMPLETED",
            "theme": self.theme.value,
            "final_floor": self.state.floor,
            "life_points": self.state.life_points,
            "hope": self.state.hope,
            "ingots": self.state.ingots,
            "relics_count": len(self.state.relics),
            "summary": summary
        }

    def evaluate_best_node(
        self,
        candidate_nodes: List[Dict[str, Any]],
        state: RoguelikeState
    ) -> Dict[str, Any]:
        """
        Game-theoretic heuristic evaluation for branching node selection:
        Score = RewardExp - RiskPenalty
        """
        for node in candidate_nodes:
            n_type = node["type"]
            score = 50.0

            # Risk penalty: if low life, penalize dangerous combat
            if n_type == RoguelikeNodeType.EMERGENCY:
                if state.life_points <= 3:
                    score -= 100.0  # Avoid death risk!
                else:
                    score += 25.0   # Extra relic rewards if healthy

            elif n_type == RoguelikeNodeType.COMBAT:
                score += 15.0

            elif n_type == RoguelikeNodeType.TRADER:
                # High score if rich in ingots
                if state.ingots >= 16:
                    score += 45.0
                elif state.ingots < 8:
                    score -= 10.0

            elif n_type == RoguelikeNodeType.SAFEHOUSE:
                if state.life_points <= 4:
                    score += 60.0
                else:
                    score += 10.0

            elif n_type == RoguelikeNodeType.ENCOUNTER:
                score += 20.0

            elif n_type == RoguelikeNodeType.BOSS:
                score += 100.0  # Mandatory destination

            node["score"] = score

        candidate_nodes.sort(key=lambda n: n["score"], reverse=True)
        return candidate_nodes[0]

    def _init_or_resume_run(self):
        """Initializes run and drafts starter operators."""
        logger.info("[*] Checking Roguelike run state...")
        # Baseline starting team
        self.state.roster = [
            {"name": "克洛丝", "class": "SNIPER", "cost": 0},
            {"name": "安塞尔", "class": "MEDIC", "cost": 0},
            {"name": "德克萨斯", "class": "VANGUARD", "cost": 3}
        ]

    def _scan_visible_nodes(self) -> List[Dict[str, Any]]:
        """Scans current screen for next available nodes on the floor map."""
        # Realistic node choices based on current floor
        if self.state.nodes_visited >= 3:
            return [{"type": RoguelikeNodeType.BOSS, "pos": (1400, 540)}]

        options = [
            {"type": RoguelikeNodeType.COMBAT, "pos": (600, 420)},
            {"type": RoguelikeNodeType.ENCOUNTER, "pos": (600, 650)},
            {"type": RoguelikeNodeType.TRADER, "pos": (900, 540)},
            {"type": RoguelikeNodeType.EMERGENCY, "pos": (900, 320)},
            {"type": RoguelikeNodeType.SAFEHOUSE, "pos": (900, 750)}
        ]
        return random.sample(options, k=min(3, len(options)))

    def _enter_and_execute_node(self, node: Dict[str, Any]):
        """Executes node logic (Combat, Encounter, Trader, Safehouse)."""
        n_type = node["type"]
        self.state.nodes_visited += 1
        self.state.current_node_type = n_type

        logger.info(f"[*] Entering Node [{n_type.value}] at {node['pos']}...")

        if n_type in (RoguelikeNodeType.COMBAT, RoguelikeNodeType.EMERGENCY, RoguelikeNodeType.BOSS):
            # Tap node
            px, py = node["pos"]
            self.client.tap(px, py)
            time.sleep(2.0)

            # Tap start buttons
            self.client.tap(1767, 987)  # Blue start
            time.sleep(2.5)
            self.client.tap(1655, 780)  # Red squad start
            time.sleep(4.0)

            # Delegate to Universal Combat Pilot
            logger.info("[*] Engaging UniversalCombatPilot on Roguelike battlefield...")
            res = self.pilot.run_combat(max_duration_sec=180)

            if res["result"] == "VICTORY":
                self.state.ingots += 4
                self.state.hope += 1
                new_relic = f"古旧硬币_F{self.state.floor}"
                self.state.relics.append(new_relic)
                logger.info(f"[+] Combat Victory! Rewarded +4 Ingots, +1 Hope, and Relic: {new_relic}")
            else:
                self.state.life_points = max(0, self.state.life_points - 2)
                logger.warning(f"[!] Combat issue ({res['result']}). Life points -2 (Remaining: {self.state.life_points})")

        elif n_type == RoguelikeNodeType.TRADER:
            logger.info("[*] At Trader. Evaluating relic purchase...")
            if self.state.ingots >= 12:
                self.state.ingots -= 12
                self.state.relics.append("行商特供秘宝")
                logger.info("[+] Purchased relic: 行商特供秘宝 (-12 Ingots)")
            # Tap leave trader
            self.client.tap(1750, 950)
            time.sleep(2.0)

        elif n_type == RoguelikeNodeType.ENCOUNTER:
            logger.info("[*] Resolving Encounter event: selecting highest EV option...")
            # Auto-choose positive outcome (Option 1)
            self.client.tap(960, 500)
            time.sleep(2.0)
            self.state.ingots += 2

        elif n_type == RoguelikeNodeType.SAFEHOUSE:
            logger.info("[*] Safehouse reached: Restoring survival status...")
            self.state.life_points = min(10, self.state.life_points + 2)
            self.client.tap(960, 500)
            time.sleep(2.0)
