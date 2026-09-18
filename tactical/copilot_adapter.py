# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
MAA Copilot Protocol Adapter & Action Normalizer
Author: Emiliamio <mio2110767128@163.com>
"""

import json
import os
from enum import Enum
from typing import List, Tuple, Dict, Any, Optional


class CopilotActionType(Enum):
    """Standardized action types in MAA Copilot protocol."""
    DEPLOY = "DEPLOY"
    SKILL = "SKILL"
    RETREAT = "RETREAT"
    SPEED_UP = "SPEED_UP"
    WAIT = "WAIT"


class CopilotAction:
    """Represents a single standardized action inside an MAA Copilot plan."""

    def __init__(
        self,
        step_index: int,
        action_type: CopilotActionType,
        name: str = "",
        col: int = 0,
        row: int = 0,
        direction: str = "right",
        min_costs: int = 0,
        min_kills: int = 0,
        pre_delay_ms: int = 0,
        rear_delay_ms: int = 0,
        skill_index: int = 1
    ):
        self.step_index = step_index
        self.action_type = action_type
        self.name = name
        self.col = col
        self.row = row
        self.target_tile = (col, row)
        self.direction = direction
        self.min_costs = min_costs
        self.min_kills = min_kills
        self.pre_delay_ms = pre_delay_ms
        self.rear_delay_ms = rear_delay_ms
        self.skill_index = skill_index
        self.status = "PENDING"  # PENDING, EXECUTED, SKIPPED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_index": self.step_index,
            "action_type": self.action_type.value,
            "name": self.name,
            "col": self.col,
            "row": self.row,
            "direction": self.direction,
            "min_costs": self.min_costs,
            "min_kills": self.min_kills,
            "status": self.status
        }


class CopilotPlan:
    """Represents a full parsed and validated MAA Copilot execution plan."""

    def __init__(
        self,
        stage_name: str,
        title: str = "",
        details: str = "",
        opers: Optional[List[Dict[str, Any]]] = None,
        actions: Optional[List[CopilotAction]] = None
    ):
        self.stage_name = stage_name
        self.title = title
        self.details = details
        self.opers = opers or []
        self.actions = actions or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_name": self.stage_name,
            "title": self.title,
            "details": self.details,
            "opers": self.opers,
            "actions": [a.to_dict() for a in self.actions]
        }


class CopilotAdapter:
    """
    Parses, validates, and normalizes standard MAA Copilot JSON protocol files.
    Translates community dialects (Chinese/English keywords) into standardized CopilotPlan.
    """

    TYPE_MAPPING = {
        "部署": CopilotActionType.DEPLOY,
        "deploy": CopilotActionType.DEPLOY,
        "技能": CopilotActionType.SKILL,
        "skill": CopilotActionType.SKILL,
        "技能用法": CopilotActionType.SKILL,
        "撤退": CopilotActionType.RETREAT,
        "retreat": CopilotActionType.RETREAT,
        "二倍速": CopilotActionType.SPEED_UP,
        "speedup": CopilotActionType.SPEED_UP,
        "等待": CopilotActionType.WAIT,
        "wait": CopilotActionType.WAIT
    }

    DIRECTION_MAPPING = {
        "右": "right",
        "right": "right",
        "下": "down",
        "down": "down",
        "左": "left",
        "left": "left",
        "上": "up",
        "up": "up"
    }

    @classmethod
    def parse_json_dict(cls, data: Dict[str, Any]) -> CopilotPlan:
        """Parses a raw JSON dictionary adhering to MAA Copilot schema."""
        stage_name = data.get("stage_name", "Unknown_Stage")
        doc = data.get("doc", {})
        title = doc.get("title", "")
        details = doc.get("details", "")
        opers = data.get("opers", [])

        actions = []
        raw_actions = data.get("actions", [])

        for idx, item in enumerate(raw_actions):
            raw_type = str(item.get("type", "")).strip().lower()
            action_type = cls.TYPE_MAPPING.get(raw_type, CopilotActionType.WAIT)

            name = item.get("name", "")
            location = item.get("location", [0, 0])
            col = int(location[0]) if len(location) > 0 else 0
            row = int(location[1]) if len(location) > 1 else 0

            raw_dir = str(item.get("direction", "右")).strip().lower()
            direction = cls.DIRECTION_MAPPING.get(raw_dir, "right")

            min_costs = int(item.get("costs", 0) or item.get("cost", 0) or 0)
            min_kills = int(item.get("kills", 0) or item.get("kill", 0) or 0)
            pre_delay = int(item.get("pre_delay", 0))
            rear_delay = int(item.get("rear_delay", 0))
            skill_idx = int(item.get("skill_index", 1))

            actions.append(CopilotAction(
                step_index=idx + 1,
                action_type=action_type,
                name=name,
                col=col,
                row=row,
                direction=direction,
                min_costs=min_costs,
                min_kills=min_kills,
                pre_delay_ms=pre_delay,
                rear_delay_ms=rear_delay,
                skill_index=skill_idx
            ))

        return CopilotPlan(
            stage_name=stage_name,
            title=title,
            details=details,
            opers=opers,
            actions=actions
        )

    @classmethod
    def load_file(cls, filepath: str) -> CopilotPlan:
        """Loads and parses an MAA Copilot JSON file from disk."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Copilot file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        return cls.parse_json_dict(data)

    @classmethod
    def save_file(cls, plan: CopilotPlan, filepath: str) -> None:
        """Serializes CopilotPlan back to standard MAA JSON format."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        raw = {
            "stage_name": plan.stage_name,
            "minimum_required": "v4.0.0",
            "doc": {
                "title": plan.title,
                "details": plan.details
            },
            "opers": plan.opers,
            "actions": []
        }

        dir_reverse = {"right": "右", "down": "下", "left": "左", "up": "上"}
        type_reverse = {
            CopilotActionType.DEPLOY: "部署",
            CopilotActionType.SKILL: "技能",
            CopilotActionType.RETREAT: "撤退",
            CopilotActionType.SPEED_UP: "二倍速",
            CopilotActionType.WAIT: "等待"
        }

        for a in plan.actions:
            entry = {
                "type": type_reverse.get(a.action_type, "部署"),
                "name": a.name,
                "location": [a.col, a.row],
                "direction": dir_reverse.get(a.direction, "右")
            }
            if a.min_costs > 0:
                entry["costs"] = a.min_costs
            if a.min_kills > 0:
                entry["kills"] = a.min_kills
            raw["actions"].append(entry)

        with open(filepath, "w", encoding="utf-8-sig") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)