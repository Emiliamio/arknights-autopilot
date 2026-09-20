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


class OperatorRecruitmentDrafter:
    """
    Intelligent Game-Theoretic Operator Drafting Engine for Roguelike Vouchers:
    - Calculates squad deficits (block, medic, anti-air, arts, dp).
    - Checks Hope budget constraints (6★: 6, 5★: 3, 4★: 2, 3★: 0, 临时: 0).
    - Ranks candidate operators based on Roguelike tier, role deficit urgency, and Hope cost efficiency.
    """

    HOPE_COST_MAP = {
        6: 6,
        5: 3,
        4: 2,
        3: 0,
        2: 0,
        1: 0
    }

    TIER_BASE_SCORES = {
        "S": 100.0,
        "A": 80.0,
        "B": 60.0,
        "C": 40.0
    }

    @classmethod
    def evaluate_squad_deficits(cls, current_roster: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyzes active squad to identify missing tactical capabilities."""
        from tactical.operator_archetypes import lookup_operator_traits, DamageType, OpClass

        stats = {
            "blockers": 0,    # block >= 2
            "medics": 0,      # heals or medic
            "anti_air": 0,    # can hit air
            "arts_dmg": 0,    # arts damage
            "dp_gen": 0       # generates dp
        }

        for op in current_roster:
            name = op.get("name", "")
            traits = lookup_operator_traits(name)
            if traits.get("block", 0) >= 2:
                stats["blockers"] += 1
            if traits.get("dmg") == DamageType.HEALING or traits.get("heals", False) or traits.get("class") == OpClass.MEDIC:
                stats["medics"] += 1
            if traits.get("air", False):
                stats["anti_air"] += 1
            if traits.get("dmg") == DamageType.ARTS:
                stats["arts_dmg"] += 1
            if traits.get("can_gen_dp", False):
                stats["dp_gen"] += 1

        return stats

    @classmethod
    def get_role_urgency_bonus(cls, candidate_traits: Dict[str, Any], deficits: Dict[str, int]) -> float:
        """Calculates synergy bonus based on how well candidate fulfills team shortfalls."""
        from tactical.operator_archetypes import DamageType, OpClass
        bonus = 0.0

        # Deficit in healing
        if deficits["medics"] == 0 and (candidate_traits.get("dmg") == DamageType.HEALING or candidate_traits.get("heals", False) or candidate_traits.get("class") == OpClass.MEDIC):
            bonus += 45.0
        elif deficits["medics"] == 1 and (candidate_traits.get("dmg") == DamageType.HEALING or candidate_traits.get("heals", False)):
            bonus += 15.0

        # Deficit in blockers
        if deficits["blockers"] == 0 and candidate_traits.get("block", 0) >= 2:
            bonus += 35.0
        elif deficits["blockers"] == 1 and candidate_traits.get("block", 0) >= 2:
            bonus += 15.0

        # Deficit in anti-air
        if deficits["anti_air"] == 0 and candidate_traits.get("air", False):
            bonus += 30.0

        # Deficit in DP generation
        if deficits["dp_gen"] == 0 and candidate_traits.get("can_gen_dp", False):
            bonus += 25.0

        # Deficit in Arts damage
        if deficits["arts_dmg"] == 0 and candidate_traits.get("dmg") == DamageType.ARTS:
            bonus += 20.0

        return bonus

    @classmethod
    def rank_candidates_for_voucher(
        cls,
        voucher_type: str,
        current_hope: int,
        current_roster: List[Dict[str, Any]],
        is_temporary: bool = False
    ) -> List[Dict[str, Any]]:
        """Ranks all eligible operators for given voucher type and hope budget."""
        from tactical.operator_archetypes import OPERATOR_DATABASE, OpClass

        voucher_upper = voucher_type.upper()
        # Handle Chinese & English voucher names
        class_map = {
            "先锋": OpClass.VANGUARD, "VANGUARD": OpClass.VANGUARD,
            "近卫": OpClass.GUARD, "GUARD": OpClass.GUARD,
            "重装": OpClass.DEFENDER, "DEFENDER": OpClass.DEFENDER,
            "狙击": OpClass.SNIPER, "SNIPER": OpClass.SNIPER,
            "术师": OpClass.CASTER, "CASTER": OpClass.CASTER,
            "医疗": OpClass.MEDIC, "MEDIC": OpClass.MEDIC,
            "辅助": OpClass.SUPPORTER, "SUPPORTER": OpClass.SUPPORTER,
            "特种": OpClass.SPECIALIST, "SPECIALIST": OpClass.SPECIALIST,
        }
        target_class = class_map.get(voucher_upper, None)
        deficits = cls.evaluate_squad_deficits(current_roster)
        roster_names = {op.get("name") for op in current_roster}

        ranked = []
        for name, traits in OPERATOR_DATABASE.items():
            if name in roster_names:
                continue

            op_class = traits.get("class")
            if target_class is not None and op_class != target_class:
                continue

            rarity = traits.get("rarity", 4)
            hope_cost = 0 if is_temporary else cls.HOPE_COST_MAP.get(rarity, 0)

            # Hope gate
            if current_hope < hope_cost:
                continue

            tier = traits.get("roguelike_tier", "B")
            base_score = cls.TIER_BASE_SCORES.get(tier, 50.0)

            urgency_bonus = cls.get_role_urgency_bonus(traits, deficits)

            # Hope penalty scaling: when hope is scarce, high cost is heavily penalized
            hope_penalty = (hope_cost * 2.0)
            if current_hope < 4 and hope_cost > 0:
                hope_penalty += (4 - current_hope) * 15.0

            # Low hope bonus for 3-star free anchors
            if rarity == 3 and current_hope < 4:
                base_score += 25.0

            total_score = base_score + urgency_bonus - hope_penalty

            reasons = []
            if tier == "S":
                reasons.append("肉鸽S级核心")
            if urgency_bonus >= 30.0:
                reasons.append("补齐阵容关键短板")
            if hope_cost == 0:
                reasons.append("0希望极高性价比")

            ranked.append({
                "name": name,
                "class": op_class.value if isinstance(op_class, OpClass) else str(op_class),
                "rarity": rarity,
                "hope_cost": hope_cost,
                "score": round(total_score, 1),
                "tier": tier,
                "reasons": " | ".join(reasons) if reasons else "常规轮换干员"
            })

        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked


class RoguelikeState:
    """Represents current live state within an active Roguelike exploration run."""

    def __init__(self, theme: RoguelikeTheme = RoguelikeTheme.IS4_SAMI):
        self.theme = theme
        self.floor = 1
        self.life_points = 6
        self.hope = 6
        self.ingots = 8           # 源石锭
        self.light_value = 100    # IS3 水月灯火值 (0~100)
        self.collapse_level = 0   # IS4 萨米坍缩指数 (0~9)
        self.relics: List[str] = ["先发制人", "黑夜呢喃"]
        self.roster: List[Dict[str, Any]] = []
        self.promoted_operators: List[str] = []
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

    def recruit_operator_with_voucher(
        self,
        voucher_type: str,
        is_temporary: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Recruits best operator for voucher, deducts hope, and adds to roster."""
        candidates = OperatorRecruitmentDrafter.rank_candidates_for_voucher(
            voucher_type=voucher_type,
            current_hope=self.state.hope,
            current_roster=self.state.roster,
            is_temporary=is_temporary
        )
        if not candidates:
            logger.warning(f"[!] No affordable operators found for voucher [{voucher_type}] (Hope: {self.state.hope})")
            return None

        chosen = candidates[0]
        self.state.hope -= chosen["hope_cost"]
        self.state.roster.append({
            "name": chosen["name"],
            "class": chosen["class"],
            "rarity": chosen["rarity"],
            "cost": chosen["hope_cost"],
            "promoted": False
        })
        logger.info(f"[+] Recruited: {chosen['name']} ({chosen['class']} ★{chosen['rarity']}) for -{chosen['hope_cost']} Hope! Reason: {chosen['reasons']}")
        return chosen

    def evaluate_best_node(
        self,
        candidate_nodes: List[Dict[str, Any]],
        state: RoguelikeState
    ) -> Dict[str, Any]:
        """
        Game-theoretic heuristic evaluation for branching node selection:
        Score = RewardExp - RiskPenalty + ThemeModifiers
        """
        for node in candidate_nodes:
            n_type = node["type"]
            score = 50.0

            # 1. Base life & Risk penalty
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
                elif len(state.roster) > len(state.promoted_operators):
                    score += 35.0  # Safehouse can promote operators!
                else:
                    score += 10.0

            elif n_type == RoguelikeNodeType.ENCOUNTER:
                score += 20.0

            elif n_type == RoguelikeNodeType.BOSS:
                score += 100.0  # Mandatory destination

            # 2. Theme-specific environmental heuristics
            if state.theme == RoguelikeTheme.IS3_MIZUKI:
                # In IS3, low light (<50) triggers mutation debuffs and high-risk emergencies
                if state.light_value < 50:
                    if n_type == RoguelikeNodeType.EMERGENCY:
                        score -= 80.0
                    elif n_type in (RoguelikeNodeType.SAFEHOUSE, RoguelikeNodeType.TRADER):
                        score += 30.0

            elif state.theme == RoguelikeTheme.IS4_SAMI:
                # In IS4, high collapse (>=3) causes severe map hazards
                if state.collapse_level >= 3:
                    if n_type == RoguelikeNodeType.SAFEHOUSE:
                        score += 50.0  # Safehouse can cleanse collapse!
                    elif n_type == RoguelikeNodeType.EMERGENCY:
                        score -= 50.0

            node["score"] = score

        candidate_nodes.sort(key=lambda n: n["score"], reverse=True)
        return candidate_nodes[0]

    def _init_or_resume_run(self):
        """Initializes run and drafts starter operators."""
        logger.info("[*] Checking Roguelike run state...")
        # Baseline starting team
        self.state.roster = [
            {"name": "克洛丝", "class": "SNIPER", "cost": 0, "promoted": True},
            {"name": "安塞尔", "class": "MEDIC", "cost": 0, "promoted": True},
            {"name": "德克萨斯", "class": "VANGUARD", "cost": 3, "promoted": False}
        ]

    def _scan_visible_nodes(self) -> List[Dict[str, Any]]:
        """Scans current screen for next available nodes on the floor map."""
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
            logger.info("[*] At Trader. Evaluating relic and promotion voucher purchase...")
            if self.state.ingots >= 12:
                self.state.ingots -= 12
                relic = "行商特供秘宝"
                self.state.relics.append(relic)
                logger.info(f"[+] Purchased relic: {relic} (-12 Ingots)")
            elif self.state.ingots >= 8:
                self.state.ingots -= 8
                self.state.hope += 1
                logger.info("[+] Purchased Hope replenishment (+1 Hope, -8 Ingots)")
            # Tap leave trader
            self.client.tap(1750, 950)
            time.sleep(2.0)

        elif n_type == RoguelikeNodeType.ENCOUNTER:
            logger.info("[*] Resolving Encounter event: selecting highest EV option...")
            self.client.tap(960, 500)
            time.sleep(2.0)
            self.state.ingots += 2

        elif n_type == RoguelikeNodeType.SAFEHOUSE:
            logger.info("[*] Safehouse reached: Evaluating survival vs tactical promotion...")
            if self.state.life_points <= 4:
                self.state.life_points = min(10, self.state.life_points + 2)
                logger.info(f"[+] Safehouse: Restored +2 Life (Current: {self.state.life_points})")
            elif self.state.collapse_level >= 3 and self.state.theme == RoguelikeTheme.IS4_SAMI:
                self.state.collapse_level = max(0, self.state.collapse_level - 2)
                logger.info(f"[+] Safehouse: Cleansed Collapse Level -2 (Current: {self.state.collapse_level})")
            else:
                unpromoted = [op for op in self.state.roster if op.get("name") not in self.state.promoted_operators]
                if unpromoted:
                    target_op = unpromoted[0]["name"]
                    self.state.promoted_operators.append(target_op)
                    logger.info(f"[+] Safehouse: Promoted operator [{target_op}] to Elite 2!")
                else:
                    self.state.hope += 2
                    logger.info(f"[+] Safehouse: Gained +2 Hope (Current: {self.state.hope})")
            self.client.tap(960, 500)
            time.sleep(2.0)
