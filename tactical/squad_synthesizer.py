# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Optimal Squad Synthesizer & Dynamic Roster Formulator
Author: Emiliamio <mio2110767128@163.com>
"""

import logging
from typing import List, Dict, Any, Optional

from tactical.roster_inspector import RosterInspector
from tactical.stage_analyzer import analyze_stage_requirements, StageTacticalProfile
from tactical.operator_archetypes import lookup_operator_traits

logger = logging.getLogger("ASTA.SquadSynthesizer")


class SquadSynthesizer:
    """
    Intelligently compiles the optimal 12-operator battle lineup for any target stage,
    custom-tailored to the specific account's owned operator box and masteries.
    """

    def __init__(self, roster_inspector: Optional[RosterInspector] = None):
        self.inspector = roster_inspector or RosterInspector()

    def synthesize_squad(self, account_id: str, stage_id: str) -> Dict[str, Any]:
        """Synthesizes the optimal 12-operator formation for a stage."""
        logger.info(f"[*] Synthesizing optimal squad for Account [{account_id}] on Stage [{stage_id}]...")

        # 1. Load account's owned operators
        roster = self.inspector.load_roster(account_id)
        if not roster:
            logger.warning(f"[!] Roster empty for {account_id}. Loading fallback baseline...")
            roster = list(self.inspector._generate_default_roster().values())

        # 2. Analyze stage requirements
        profile = analyze_stage_requirements(stage_id)
        quotas = profile.compute_role_quotas()
        logger.info(f"[+] Stage [{stage_id}] Role Quotas: {quotas}")

        # 3. Categorize owned operators by class
        by_class: Dict[str, List[Dict[str, Any]]] = {}
        for op in roster:
            cls = op.get("class", "GUARD")
            by_class.setdefault(cls, []).append(op)

        # 4. Score operators within each class
        def score_operator(op: Dict[str, Any]) -> float:
            rarity = op.get("rarity", 4)
            level = op.get("level", 40)
            elite = op.get("elite", 1)
            name = op.get("name", "")
            traits = lookup_operator_traits(name)

            score = rarity * 20.0 + level * 0.5 + elite * 30.0

            # Situational bonuses
            if profile.air_threat == "HIGH" and traits.get("air"):
                score += 25.0
            if profile.armor_threat == "HIGH" and traits.get("dmg") == "ARTS":
                score += 25.0
            if profile.rush_threat == "HIGH" and traits.get("can_gen_dp"):
                score += 20.0
            if traits.get("fast_redeploy"):
                score += 15.0

            return score

        for cls in by_class:
            by_class[cls].sort(key=score_operator, reverse=True)

        # 5. Fill squad according to quotas
        selected_squad: List[Dict[str, Any]] = []
        selected_names = set()

        for cls, count in quotas.items():
            candidates = by_class.get(cls, [])
            picked = 0
            for op in candidates:
                if op["name"] not in selected_names and picked < count:
                    selected_squad.append(op)
                    selected_names.add(op["name"])
                    picked += 1

        # 6. Backfill if any class was short of quota
        if len(selected_squad) < 12:
            remaining_pool = [op for op in roster if op["name"] not in selected_names]
            remaining_pool.sort(key=score_operator, reverse=True)
            while len(selected_squad) < 12 and remaining_pool:
                op = remaining_pool.pop(0)
                selected_squad.append(op)
                selected_names.add(op["name"])

        # Format output
        formatted_squad = []
        for i, op in enumerate(selected_squad[:12]):
            formatted_squad.append({
                "slot": i + 1,
                "name": op["name"],
                "class": op.get("class", "GUARD"),
                "rarity": op.get("rarity", 4),
                "damage_type": op.get("damage_type", "PHYSICAL"),
                "cost": op.get("cost", 12),
                "score": round(score_operator(op), 1)
            })

        summary = (
            f"针对关卡 {stage_id} (对空: {profile.air_threat}, 破甲: {profile.armor_threat}): "
            f"已自适应合成 12 人黄金阵容，核心干员: {', '.join(s['name'] for s in formatted_squad[:4])}等。"
        )
        logger.info(f"[+] Squad Synthesis complete: {summary}")

        return {
            "account_id": account_id,
            "stage_id": stage_id,
            "total_operators": len(formatted_squad),
            "squad": formatted_squad,
            "summary": summary
        }
