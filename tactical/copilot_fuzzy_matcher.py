# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Copilot Fuzzy Matcher & Operator Substitute Drafter
Author: Emiliamio <mio2110767128@163.com>
"""

import copy
import logging
from typing import Dict, List, Tuple, Any, Optional

from tactical.operator_archetypes import (
    OpClass,
    DamageType,
    OPERATOR_DATABASE,
    lookup_operator_traits
)
from tactical.copilot_adapter import CopilotPlan, CopilotAction, CopilotActionType

logger = logging.getLogger("ASTA.CopilotFuzzyMatcher")


class CopilotFuzzyMatcher:
    """
    Intelligent Operator Substitution Engine for MAA Copilot Plans.
    Resolves missing operators in customer rosters by matching equivalent
    lower-tier or side-grade operators and automatically offsets deployment cost (ΔCost).
    """

    # Explicit hierarchical substitution priority chains
    EXPLICIT_CHAINS: Dict[str, List[str]] = {
        # 决战近卫 (Guards)
        "玛恩纳": ["银灰", "拉普兰德", "月见夜"],
        "银灰": ["玛恩纳", "拉普兰德", "月见夜"],
        "史尔特尔": ["耀骑士临光", "宴", "玫兰莎"],
        "棘刺": ["拉普兰德", "月见夜", "芳汀"],
        "煌": ["幽灵鲨", "泡普卡", "刻刀"],
        "幽灵鲨": ["煌", "泡普卡"],
        "玫兰莎": ["月见夜", "宴"],

        # 守护重装 (Defenders)
        "塞雷娅": ["临光", "古米", "斑点"],
        "临光": ["古米", "斑点", "塞雷娅"],
        "古米": ["斑点", "临光"],
        "星熊": ["蛇屠箱", "米戈", "黑角"],
        "蛇屠箱": ["米戈", "黑角", "星熊"],

        # 战术先锋 (Vanguards)
        "德克萨斯": ["极境", "讯使", "芬", "夜刀"],
        "桃金娘": ["极境", "讯使", "芬"],
        "极境": ["桃金娘", "讯使", "芬"],
        "风笛": ["红豆", "翎羽"],
        "讯使": ["芬", "夜刀"],
        "芬": ["讯使", "夜刀"],

        # 狙击输出 (Snipers)
        "能天使": ["鸿雪", "蓝毒", "白金", "克洛丝"],
        "鸿雪": ["能天使", "蓝毒", "白金", "克洛丝"],
        "蓝毒": ["白金", "克洛丝"],
        "白金": ["蓝毒", "克洛丝"],
        "陨星": ["白雪", "空爆"],
        "白雪": ["陨星", "空爆"],

        # 术师高台 (Casters)
        "艾雅法拉": ["澄闪", "阿米娅", "远山", "史都华德"],
        "澄闪": ["艾雅法拉", "阿米娅", "远山", "史都华德"],
        "阿米娅": ["远山", "史都华德"],
        "伊芙利特": ["远山", "炎熔"],

        # 医疗保障 (Medics)
        "纯烬艾雅法拉": ["夜莺", "白面鸮", "调香师"],
        "夜莺": ["纯烬艾雅法拉", "白面鸮", "调香师"],
        "闪灵": ["赫默", "苏苏洛", "安塞尔", "芙蓉"],
        "赫默": ["闪灵", "苏苏洛", "安塞尔", "芙蓉"],
        "白面鸮": ["调香师", "安塞尔"],
        "调香师": ["白面鸮", "安塞尔", "芙蓉"],
        "安塞尔": ["芙蓉"],
        "芙蓉": ["安塞尔"],

        # 特种/快活 (Specialists)
        "麒麟R夜刀": ["德克萨斯(异格)", "傀影", "红", "砾"],
        "德克萨斯(异格)": ["麒麟R夜刀", "傀影", "红", "砾"],
        "红": ["砾", "夜刀"],
        "傀影": ["红", "砾"],
        "砾": ["红", "夜刀"]
    }

    def __init__(self, owned_roster: Optional[List[str]] = None):
        """
        :param owned_roster: List of operator names owned by current account.
        """
        self.owned_roster: List[str] = owned_roster or []
        self._owned_set = set(self.owned_roster)

    def set_owned_roster(self, roster: List[str]) -> None:
        self.owned_roster = roster
        self._owned_set = set(roster)

    def match_substitute(self, target_op: str) -> Tuple[str, int, str]:
        """
        Finds best available substitute for target_op.
        Returns: (substitute_name, delta_cost, reason)
        - If target_op is owned, returns (target_op, 0, "EXACT_MATCH").
        - If substituted, returns (substitute_name, delta_cost, "SUBSTITUTE").
        - If no substitute available, returns (target_op, 0, "UNRESOLVED").
        """
        # 1. Exact match check
        if not self._owned_set or target_op in self._owned_set:
            return target_op, 0, "EXACT_MATCH"

        target_traits = lookup_operator_traits(target_op)
        target_cost = target_traits.get("cost", 12)

        # 2. Check explicit priority chain
        chain = self.EXPLICIT_CHAINS.get(target_op, [])
        for candidate in chain:
            if candidate in self._owned_set:
                cand_traits = lookup_operator_traits(candidate)
                cand_cost = cand_traits.get("cost", 12)
                delta_cost = cand_cost - target_cost
                logger.info(
                    f"[*] Operator substitution found via explicit chain: "
                    f"[{target_op}] ➔ [{candidate}] (Cost: {target_cost} ➔ {cand_cost}, Δ={delta_cost:+d})"
                )
                return candidate, delta_cost, "EXPLICIT_CHAIN"

        # 3. Heuristic fallback: Same Class & Role traits
        target_class = target_traits.get("class", OpClass.GUARD)
        target_air = target_traits.get("air", False)
        target_dmg = target_traits.get("dmg", DamageType.PHYSICAL)

        candidates = []
        for op_name in self.owned_roster:
            traits = lookup_operator_traits(op_name)
            if traits.get("class") == target_class:
                score = 100
                if traits.get("air") == target_air:
                    score += 40
                if traits.get("dmg") == target_dmg:
                    score += 30
                cost_diff = abs(traits.get("cost", 12) - target_cost)
                score -= cost_diff * 2
                score += traits.get("rarity", 3) * 5
                candidates.append((score, op_name, traits.get("cost", 12)))

        if candidates:
            candidates.sort(key=lambda x: -x[0])
            best_cand = candidates[0][1]
            best_cost = candidates[0][2]
            delta_cost = best_cost - target_cost
            logger.info(
                f"[*] Operator substitution found via heuristic scoring: "
                f"[{target_op}] ➔ [{best_cand}] (Cost: {target_cost} ➔ {best_cost}, Δ={delta_cost:+d})"
            )
            return best_cand, delta_cost, "HEURISTIC_MATCH"

        # 4. Unable to substitute
        logger.warning(f"[!] No suitable substitute found in roster for [{target_op}]. Retaining original.")
        return target_op, 0, "UNRESOLVED"

    def adapt_plan(
        self,
        copilot_plan: CopilotPlan,
        owned_roster: Optional[List[str]] = None
    ) -> Tuple[CopilotPlan, Dict[str, Dict[str, Any]]]:
        """
        Clones and adapts a CopilotPlan:
        - Replaces missing operators with substitutes.
        - Automatically offsets min_costs thresholds based on ΔCost.
        - Synchronizes operator names across DEPLOY, SKILL, RETREAT actions and OPERS roster.

        Returns: (adapted_plan, substitutions_applied)
        """
        if owned_roster is not None:
            self.set_owned_roster(owned_roster)

        adapted = copy.deepcopy(copilot_plan)
        substitutions: Dict[str, Dict[str, Any]] = {}

        # Pass 1: Resolve DEPLOY substitutions
        for action in adapted.actions:
            if action.action_type == CopilotActionType.DEPLOY:
                orig_name = action.name
                sub_name, delta_cost, reason = self.match_substitute(orig_name)
                if sub_name != orig_name:
                    action.name = sub_name
                    # Offset min_costs threshold so operator drops when required DP is reached
                    action.min_costs = max(0, action.min_costs + delta_cost)
                    substitutions[orig_name] = {
                        "substitute": sub_name,
                        "delta_cost": delta_cost,
                        "reason": reason
                    }

        # Pass 2: Synchronize SKILL & RETREAT references to renamed operators
        for action in adapted.actions:
            if action.action_type in (CopilotActionType.SKILL, CopilotActionType.RETREAT):
                if action.name in substitutions:
                    action.name = substitutions[action.name]["substitute"]

        # Pass 3: Synchronize adapted.opers
        for op in adapted.opers:
            if op.get("name") in substitutions:
                op["name"] = substitutions[op["name"]]["substitute"]

        if substitutions:
            logger.info(
                f"🎉 [CopilotFuzzyMatcher] Successfully adapted plan [{copilot_plan.title}]: "
                f"{len(substitutions)} substitutions applied."
            )

        return adapted, substitutions
