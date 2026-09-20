# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Universal Stage Knowledge Base (Main Theme Episodes 0~14, SideStories & Resources)
Author: Emiliamio <mio2110767128@163.com>
"""

from typing import Dict, Any, List, Optional


class StageDatabase:
    """
    Catalog of Arknights stages covering Episode 0 through Episode 14+,
    resource collection, and side-stories with tactical threat metadata.
    """

    # Structured index of all mainline chapters
    CHAPTER_INDEX: Dict[int, Dict[str, Any]] = {
        0: {"title": "黑暗时代 (序章)", "code_prefix": "0-", "stages_count": 11, "has_boss": True, "boss": "碎骨"},
        1: {"title": "黑暗时代·下", "code_prefix": "1-", "stages_count": 12, "has_boss": True, "boss": "W"},
        2: {"title": "异卵同生", "code_prefix": "2-", "stages_count": 10, "has_boss": True, "boss": "碎骨(强化)"},
        3: {"title": "二次呼吸", "code_prefix": "3-", "stages_count": 8, "has_boss": True, "boss": "弑君者"},
        4: {"title": "急性衰竭", "code_prefix": "4-", "stages_count": 10, "has_boss": True, "boss": "霜星"},
        5: {"title": "百炼成钢", "code_prefix": "5-", "stages_count": 11, "has_boss": True, "boss": "梅菲斯特/浮士德"},
        6: {"title": "局部坏死", "code_prefix": "6-", "stages_count": 18, "has_boss": True, "boss": "霜星·冬痕"},
        7: {"title": "苦难产生奇迹", "code_prefix": "7-", "stages_count": 20, "has_boss": True, "boss": "爱国者"},
        8: {"title": "怒号光明", "code_prefix": "8-", "stages_count": 20, "has_boss": True, "boss": "塔露拉/黑蛇"},
        9: {"title": "风暴瞭望", "code_prefix": "9-", "stages_count": 21, "has_boss": True, "boss": "蔓德拉"},
        10: {"title": "残阳沦落", "code_prefix": "10-", "stages_count": 23, "has_boss": True, "boss": "曼弗雷德"},
        11: {"title": "淬火尘霾", "code_prefix": "11-", "stages_count": 24, "has_boss": True, "boss": "变形者集群"},
        12: {"title": "惊霆无声", "code_prefix": "12-", "stages_count": 23, "has_boss": True, "boss": "血魔大君"},
        13: {"title": "恶兆窥视", "code_prefix": "13-", "stages_count": 24, "has_boss": True, "boss": "死魂灵之嗣"},
        14: {"title": "慈悲灯塔", "code_prefix": "14-", "stages_count": 23, "has_boss": True, "boss": "特蕾西娅/阿米娅"}
    }

    # Material & Resource Stages
    RESOURCE_STAGES: Dict[str, Dict[str, Any]] = {
        "1-7": {"title": "固源岩圣地", "type": "MATERIAL", "cost": 6, "air": False, "armor": "LOW"},
        "LS-1": {"title": "作战演习·初级", "type": "EXP", "cost": 10, "air": False, "armor": "LOW"},
        "LS-2": {"title": "作战演习·中级", "type": "EXP", "cost": 15, "air": False, "armor": "LOW"},
        "LS-3": {"title": "作战演习·高级", "type": "EXP", "cost": 20, "air": True, "armor": "MEDIUM"},
        "LS-4": {"title": "作战演习·特级", "type": "EXP", "cost": 25, "air": True, "armor": "MEDIUM"},
        "LS-5": {"title": "作战演习·极限", "type": "EXP", "cost": 30, "air": True, "armor": "HIGH"},
        "CE-5": {"title": "押运演习", "type": "LMD", "cost": 30, "air": False, "armor": "HIGH"},
        "AP-5": {"title": "红票演习", "type": "RED_CERT", "cost": 30, "air": True, "armor": "HIGH"},
        "PR-A-1": {"title": "重装/医疗芯片", "type": "CHIP", "cost": 18, "air": False, "armor": "LOW"},
        "PR-B-1": {"title": "狙击/术师芯片", "type": "CHIP", "cost": 18, "air": True, "armor": "LOW"},
        "PR-C-1": {"title": "先锋/辅助芯片", "type": "CHIP", "cost": 18, "air": False, "armor": "LOW"},
        "PR-D-1": {"title": "近卫/特种芯片", "type": "CHIP", "cost": 18, "air": False, "armor": "LOW"}
    }

    @classmethod
    def get_chapter_info(cls, chapter: int) -> Optional[Dict[str, Any]]:
        return cls.CHAPTER_INDEX.get(chapter)

    @classmethod
    def list_chapter_stages(cls, chapter: int) -> List[str]:
        """Generate full ordered list of stage codes in a chapter (e.g. 0-1 ... 0-11)."""
        info = cls.CHAPTER_INDEX.get(chapter)
        if not info:
            return []
        prefix = info["code_prefix"]
        count = info["stages_count"]
        return [f"{prefix}{i}" for i in range(1, count + 1)]

    @classmethod
    def get_stage_metadata(cls, stage_code: str) -> Dict[str, Any]:
        """Returns tactical profile and metadata for any mainline or resource stage."""
        code = stage_code.strip().upper()
        if code in cls.RESOURCE_STAGES:
            return dict(cls.RESOURCE_STAGES[code])

        # Infer mainline details
        if "-" in code:
            parts = code.split("-")
            try:
                ch = int(parts[0])
                st = int(parts[1])
                ch_info = cls.get_chapter_info(ch)
                return {
                    "stage_code": code,
                    "chapter": ch,
                    "chapter_title": ch_info["title"] if ch_info else f"第 {ch} 章",
                    "stage_index": st,
                    "is_boss_stage": st == ch_info["stages_count"] if ch_info else False,
                    "type": "MAIN_THEME"
                }
            except ValueError:
                pass

        return {"stage_code": code, "type": "UNKNOWN"}
