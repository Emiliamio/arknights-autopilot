# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Stage Topological & Tactical Requirement Analyzer
Author: Emiliamio <mio2110767128@163.com>
"""

from typing import Dict, Any


class StageTacticalProfile:
    """Represents environmental, topological, and enemy composition demands of a stage."""

    def __init__(
        self,
        stage_id: str,
        air_threat: str = "MEDIUM",       # HIGH, MEDIUM, NONE
        armor_threat: str = "MEDIUM",     # HIGH, MEDIUM, LOW
        swarm_threat: str = "MEDIUM",     # HIGH, MEDIUM, LOW
        rush_threat: str = "MEDIUM",      # HIGH, LOW
        sustain_threat: str = "MEDIUM"    # HIGH (Poison mist), MEDIUM
    ):
        self.stage_id = stage_id
        self.air_threat = air_threat
        self.armor_threat = armor_threat
        self.swarm_threat = swarm_threat
        self.rush_threat = rush_threat
        self.sustain_threat = sustain_threat

    def compute_role_quotas(self) -> Dict[str, int]:
        """Calculates optimal distribution of 12 squad slots across 8 classes."""
        # Baseline balanced archetype:
        # Vanguard: 2, Sniper: 2, Defender: 2, Medic: 2, Caster: 2, Guard: 1, Specialist: 1
        quotas = {
            "VANGUARD": 2,
            "SNIPER": 2,
            "DEFENDER": 2,
            "MEDIC": 2,
            "CASTER": 2,
            "GUARD": 1,
            "SPECIALIST": 1
        }

        # Dynamic adjustments based on stage threats:
        if self.air_threat == "HIGH":
            quotas["SNIPER"] += 1
            quotas["GUARD"] = max(0, quotas["GUARD"] - 1)

        if self.armor_threat == "HIGH":
            quotas["CASTER"] += 1
            quotas["DEFENDER"] = max(1, quotas["DEFENDER"] - 1)

        if self.sustain_threat == "HIGH":
            quotas["MEDIC"] += 1
            quotas["SPECIALIST"] = max(0, quotas["SPECIALIST"] - 1)

        # Normalize sum to exactly 12
        total = sum(quotas.values())
        if total < 12:
            quotas["GUARD"] += (12 - total)
        elif total > 12:
            quotas["SPECIALIST"] = max(0, quotas["SPECIALIST"] - (total - 12))

        return quotas


# Stage Knowledge Base
STAGE_DATABASE: Dict[str, Dict[str, str]] = {
    # Episode 0
    "0-1": {"air": "NONE", "armor": "LOW", "swarm": "LOW", "rush": "LOW", "sustain": "LOW"},
    "0-2": {"air": "NONE", "armor": "LOW", "swarm": "LOW", "rush": "LOW", "sustain": "LOW"},
    "0-3": {"air": "MEDIUM", "armor": "LOW", "swarm": "LOW", "rush": "LOW", "sustain": "LOW"},
    "0-4": {"air": "HIGH", "armor": "LOW", "swarm": "LOW", "rush": "LOW", "sustain": "LOW"},
    "0-5": {"air": "HIGH", "armor": "LOW", "swarm": "LOW", "rush": "LOW", "sustain": "LOW"},
    "0-6": {"air": "MEDIUM", "armor": "MEDIUM", "swarm": "LOW", "rush": "LOW", "sustain": "LOW"},
    "0-7": {"air": "LOW", "armor": "HIGH", "swarm": "MEDIUM", "rush": "MEDIUM", "sustain": "LOW"},
    "0-8": {"air": "LOW", "armor": "HIGH", "swarm": "HIGH", "rush": "MEDIUM", "sustain": "LOW"},
    "0-9": {"air": "MEDIUM", "armor": "HIGH", "swarm": "HIGH", "rush": "HIGH", "sustain": "MEDIUM"},
    "0-10": {"air": "LOW", "armor": "HIGH", "swarm": "HIGH", "rush": "HIGH", "sustain": "HIGH"},
    "0-11": {"air": "LOW", "armor": "HIGH", "swarm": "HIGH", "rush": "HIGH", "sustain": "HIGH"},

    # Material & Resource Stages
    "1-7": {"air": "LOW", "armor": "LOW", "swarm": "HIGH", "rush": "MEDIUM", "sustain": "LOW"},
    "LS-1": {"air": "LOW", "armor": "LOW", "swarm": "HIGH", "rush": "HIGH", "sustain": "LOW"},
    "LS-2": {"air": "MEDIUM", "armor": "LOW", "swarm": "HIGH", "rush": "HIGH", "sustain": "LOW"},
    "LS-3": {"air": "MEDIUM", "armor": "MEDIUM", "swarm": "HIGH", "rush": "HIGH", "sustain": "LOW"},
    "LS-4": {"air": "HIGH", "armor": "MEDIUM", "swarm": "HIGH", "rush": "HIGH", "sustain": "LOW"},
    "LS-5": {"air": "HIGH", "armor": "HIGH", "swarm": "HIGH", "rush": "HIGH", "sustain": "LOW"},
    "CE-5": {"air": "NONE", "armor": "HIGH", "swarm": "HIGH", "rush": "HIGH", "sustain": "LOW"},
    "AP-5": {"air": "HIGH", "armor": "HIGH", "swarm": "MEDIUM", "rush": "MEDIUM", "sustain": "HIGH"}
}


def analyze_stage_requirements(stage_id: str) -> StageTacticalProfile:
    """Look up stage tactical profile or heuristically deduce requirements."""
    clean_id = stage_id.strip().upper()
    if clean_id in STAGE_DATABASE:
        spec = STAGE_DATABASE[clean_id]
        return StageTacticalProfile(
            stage_id=clean_id,
            air_threat=spec["air"],
            armor_threat=spec["armor"],
            swarm_threat=spec["swarm"],
            rush_threat=spec["rush"],
            sustain_threat=spec["sustain"]
        )

    # Heuristic fallback: if stage has 'drone' or high number
    return StageTacticalProfile(
        stage_id=clean_id,
        air_threat="MEDIUM",
        armor_threat="MEDIUM",
        swarm_threat="MEDIUM"
    )
