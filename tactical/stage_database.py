# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Universal Stage Knowledge Base (Main Theme Episodes 0~17, All SideStories & Resources)
Author: Emiliamio <mio2110767128@163.com>
"""

from typing import Dict, Any, List, Optional


class StageDatabase:
    """
    Comprehensive Catalog of Arknights stages covering Episode 0 through Episode 17,
    all historical and active Side Stories, Intermezzi, Resource collection, and Chips.
    """

    # Structured index of all mainline chapters from Episode 00 up to Episode 17
    CHAPTER_INDEX: Dict[int, Dict[str, Any]] = {
        0: {"title": "黑暗时代 (序章)", "code_prefix": "0-", "stages_count": 11, "has_boss": True, "boss": "碎骨", "h_stages": []},
        1: {"title": "黑暗时代·下", "code_prefix": "1-", "stages_count": 12, "has_boss": True, "boss": "W", "h_stages": []},
        2: {"title": "异卵同生", "code_prefix": "2-", "stages_count": 10, "has_boss": True, "boss": "碎骨(强化)", "h_stages": []},
        3: {"title": "二次呼吸", "code_prefix": "3-", "stages_count": 8, "has_boss": True, "boss": "弑君者", "h_stages": []},
        4: {"title": "急性衰竭", "code_prefix": "4-", "stages_count": 10, "has_boss": True, "boss": "霜星", "h_stages": []},
        5: {"title": "百炼成钢", "code_prefix": "5-", "stages_count": 11, "has_boss": True, "boss": "梅菲斯特/浮士德", "h_stages": ["H5-1", "H5-2", "H5-3", "H5-4"]},
        6: {"title": "局部坏死", "code_prefix": "6-", "stages_count": 18, "has_boss": True, "boss": "霜星·冬痕", "h_stages": ["H6-1", "H6-2", "H6-3", "H6-4"]},
        7: {"title": "苦难产生奇迹", "code_prefix": "7-", "stages_count": 20, "has_boss": True, "boss": "爱国者", "h_stages": ["H7-1", "H7-2", "H7-3", "H7-4"]},
        8: {"title": "怒号光明", "code_prefix": "8-", "stages_count": 20, "has_boss": True, "boss": "塔露拉/黑蛇", "h_stages": ["H8-1", "H8-2", "H8-3", "H8-4"]},
        9: {"title": "风暴瞭望", "code_prefix": "9-", "stages_count": 21, "has_boss": True, "boss": "蔓德拉", "h_stages": ["H9-1", "H9-2", "H9-3", "H9-4", "H9-5", "H9-6"]},
        10: {"title": "残阳沦落", "code_prefix": "10-", "stages_count": 23, "has_boss": True, "boss": "曼弗雷德", "h_stages": ["H10-1", "H10-2", "H10-3"]},
        11: {"title": "淬火尘霾", "code_prefix": "11-", "stages_count": 24, "has_boss": True, "boss": "变形者集群", "h_stages": ["H11-1", "H11-2", "H11-3", "H11-4"]},
        12: {"title": "惊霆无声", "code_prefix": "12-", "stages_count": 23, "has_boss": True, "boss": "血魔大君", "h_stages": ["H12-1", "H12-2", "H12-3", "H12-4"]},
        13: {"title": "恶兆窥视", "code_prefix": "13-", "stages_count": 24, "has_boss": True, "boss": "死魂灵之嗣", "h_stages": ["H13-1", "H13-2", "H13-3", "H13-4"]},
        14: {"title": "慈悲灯塔", "code_prefix": "14-", "stages_count": 23, "has_boss": True, "boss": "特蕾西娅/阿米娅", "h_stages": ["H14-1", "H14-2", "H14-3", "H14-4"]},
        15: {"title": "重整未来 (主线第15章)", "code_prefix": "15-", "stages_count": 22, "has_boss": True, "boss": "终末机兵", "h_stages": ["H15-1", "H15-2", "H15-3", "H15-4"]},
        16: {"title": "文明存续 (主线第16章)", "code_prefix": "16-", "stages_count": 22, "has_boss": True, "boss": "源石枢纽", "h_stages": ["H16-1", "H16-2", "H16-3", "H16-4"]},
        17: {"title": "极星归途 (最新主线第17章)", "code_prefix": "17-", "stages_count": 22, "has_boss": True, "boss": "泰拉深空先驱", "h_stages": ["H17-1", "H17-2", "H17-3", "H17-4"]}
    }

    # Side Story and Intermezzo Events
    EVENTS_INDEX: List[Dict[str, Any]] = [
        {"name": "怀黍离", "prefix": "HS-", "stages": [f"HS-{i}" for i in range(1, 10)] + [f"HS-EX-{i}" for i in range(1, 9)]},
        {"name": "巴别塔", "prefix": "BB-", "stages": [f"BB-{i}" for i in range(1, 11)] + [f"BB-EX-{i}" for i in range(1, 9)]},
        {"name": "孤星", "prefix": "CW-", "stages": [f"CW-{i}" for i in range(1, 11)] + [f"CW-EX-{i}" for i in range(1, 9)]},
        {"name": "崔林特尔梅之金", "prefix": "ZT-", "stages": [f"ZT-{i}" for i in range(1, 11)] + [f"ZT-EX-{i}" for i in range(1, 9)]},
        {"name": "银心湖铁道", "prefix": "RS-", "stages": [f"RS-{i}" for i in range(1, 9)] + [f"RS-EX-{i}" for i in range(1, 9)]},
        {"name": "火山旅梦", "prefix": "SL-", "stages": [f"SL-{i}" for i in range(1, 9)] + [f"SL-EX-{i}" for i in range(1, 9)]},
        {"name": "空想花庭", "prefix": "HE-", "stages": [f"HE-{i}" for i in range(1, 9)] + [f"HE-EX-{i}" for i in range(1, 9)]},
        {"name": "照我以火", "prefix": "FC-", "stages": [f"FC-{i}" for i in range(1, 9)] + [f"FC-EX-{i}" for i in range(1, 9)]},
        {"name": "叙拉古人", "prefix": "IS-", "stages": [f"IS-{i}" for i in range(1, 11)] + [f"IS-EX-{i}" for i in range(1, 9)]},
        {"name": "绿野幻梦", "prefix": "DV-", "stages": [f"DV-{i}" for i in range(1, 9)] + [f"DV-EX-{i}" for i in range(1, 9)]},
        {"name": "尘影余音", "prefix": "LE-", "stages": [f"LE-{i}" for i in range(1, 9)] + [f"LE-EX-{i}" for i in range(1, 9)]},
        {"name": "覆潮之下", "prefix": "SV-", "stages": [f"SV-{i}" for i in range(1, 10)] + [f"SV-EX-{i}" for i in range(1, 9)]},
        {"name": "遗尘漫步", "prefix": "WD-", "stages": [f"WD-{i}" for i in range(1, 9)] + [f"WD-EX-{i}" for i in range(1, 9)]},
        {"name": "画中人", "prefix": "WR-", "stages": [f"WR-{i}" for i in range(1, 11)] + [f"WR-EX-{i}" for i in range(1, 9)]},
        {"name": "骑兵与猎人", "prefix": "GT-", "stages": [f"GT-{i}" for i in range(1, 7)] + [f"GT-EX-{i}" for i in range(1, 7)]}
    ]

    # Material & Resource Stages
    RESOURCE_STAGES: Dict[str, Dict[str, Any]] = {
        # 固源岩 / 物资
        "1-7": {"title": "固源岩圣地", "type": "MATERIAL", "cost": 6, "air": False, "armor": "LOW"},
        # 龙门币
        "CE-1": {"title": "货物运送·初级", "type": "LMD", "cost": 10},
        "CE-2": {"title": "货物运送·中级", "type": "LMD", "cost": 15},
        "CE-3": {"title": "货物运送·高级", "type": "LMD", "cost": 20},
        "CE-4": {"title": "货物运送·特级", "type": "LMD", "cost": 25},
        "CE-5": {"title": "货物运送·极限", "type": "LMD", "cost": 30},
        "CE-6": {"title": "货物运送·绝境", "type": "LMD", "cost": 36},
        # 作战演习 (经验书)
        "LS-1": {"title": "作战演习·初级", "type": "EXP", "cost": 10},
        "LS-2": {"title": "作战演习·中级", "type": "EXP", "cost": 15},
        "LS-3": {"title": "作战演习·高级", "type": "EXP", "cost": 20},
        "LS-4": {"title": "作战演习·特级", "type": "EXP", "cost": 25},
        "LS-5": {"title": "作战演习·极限", "type": "EXP", "cost": 30},
        "LS-6": {"title": "作战演习·绝境", "type": "EXP", "cost": 36},
        # 红票 / 碳素 / 技巧
        "AP-5": {"title": "红票演习·绝境", "type": "RED_CERT", "cost": 30},
        "SK-5": {"title": "碳素搜集·绝境", "type": "CARBON", "cost": 30},
        "CA-5": {"title": "技巧演练·绝境", "type": "SKILL_BOOK", "cost": 30},
        # 职业芯片
        "PR-A-1": {"title": "重装/医疗芯片·初级", "type": "CHIP", "cost": 18},
        "PR-A-2": {"title": "重装/医疗芯片·高级", "type": "CHIP", "cost": 36},
        "PR-B-1": {"title": "狙击/术师芯片·初级", "type": "CHIP", "cost": 18},
        "PR-B-2": {"title": "狙击/术师芯片·高级", "type": "CHIP", "cost": 36},
        "PR-C-1": {"title": "先锋/辅助芯片·初级", "type": "CHIP", "cost": 18},
        "PR-C-2": {"title": "先锋/辅助芯片·高级", "type": "CHIP", "cost": 36},
        "PR-D-1": {"title": "近卫/特种芯片·初级", "type": "CHIP", "cost": 18},
        "PR-D-2": {"title": "近卫/特种芯片·高级", "type": "CHIP", "cost": 36}
    }

    @classmethod
    def get_chapter_info(cls, chapter: int) -> Optional[Dict[str, Any]]:
        return cls.CHAPTER_INDEX.get(chapter)

    @classmethod
    def list_chapter_stages(cls, chapter: int, include_h_stages: bool = False) -> List[str]:
        """Generate full ordered list of stage codes in a chapter (e.g. 0-1 ... 0-11, plus optional H-stages)."""
        info = cls.CHAPTER_INDEX.get(chapter)
        if not info:
            return []
        prefix = info["code_prefix"]
        count = info["stages_count"]
        normal_stages = [f"{prefix}{i}" for i in range(1, count + 1)]
        if include_h_stages:
            normal_stages.extend(info.get("h_stages", []))
        return normal_stages

    @classmethod
    def get_stage_catalog(cls) -> Dict[str, Any]:
        """
        Returns full structured stage catalog hierarchy for Web HUD cascading dropdowns:
        - Main Theme (Episode 00 to Episode 17)
        - Side Stories & Intermezzi
        - Resources & Chips
        """
        # 1. Main Chapters
        mainline_chapters = []
        for ch_num, ch_data in sorted(cls.CHAPTER_INDEX.items(), key=lambda x: x[0]):
            stages = cls.list_chapter_stages(ch_num, include_h_stages=True)
            mainline_chapters.append({
                "id": f"CHAPTER_{ch_num}",
                "chapter": ch_num,
                "chapter_num": ch_num,
                "title": f"第 {ch_num} 章 · {ch_data['title']} (EP{ch_num:02d})",
                "stages_count": ch_data["stages_count"],
                "boss": ch_data.get("boss", "无"),
                "stages": stages
            })

        # 2. Events & Side Stories
        events_list = []
        for idx, ev in enumerate(cls.EVENTS_INDEX):
            events_list.append({
                "id": f"EVENT_{idx}_{ev['prefix']}",
                "name": ev["name"],
                "prefix": ev["prefix"],
                "title": f"{ev['name']} ({ev['prefix'].rstrip('-')})",
                "stages": ev["stages"]
            })

        # 3. Resources & Chips
        resource_groups = [
            {"name": "常规素材刷取", "category": "常规素材", "stages": ["1-7", "CE-6", "LS-6", "AP-5", "CA-5", "SK-5"]},
            {"name": "龙门币筹备 (CE系列)", "category": "龙门币", "stages": [f"CE-{i}" for i in range(1, 7)]},
            {"name": "作战演习经验 (LS系列)", "category": "作战记录", "stages": [f"LS-{i}" for i in range(1, 7)]},
            {"name": "职业双极芯片 (PR系列)", "category": "职业芯片", "stages": ["PR-A-1", "PR-A-2", "PR-B-1", "PR-B-2", "PR-C-1", "PR-C-2", "PR-D-1", "PR-D-2"]}
        ]

        return {
            "categories": [
                {
                    "id": "MAIN_THEME",
                    "label": "主线战役 (EPISODE 00 ~ 17)",
                    "groups": mainline_chapters
                },
                {
                    "id": "EVENTS",
                    "label": "插曲与别传活动 (SIDE STORIES)",
                    "groups": events_list
                },
                {
                    "id": "RESOURCES",
                    "label": "日常物资与芯片搜索 (RESOURCES)",
                    "groups": resource_groups
                }
            ],
            "main_theme": mainline_chapters,
            "events": events_list,
            "resources": resource_groups
        }

    @classmethod
    def get_stage_metadata(cls, stage_code: str) -> Dict[str, Any]:
        """Returns tactical profile and metadata for any mainline, event, or resource stage."""
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

        # Check event prefix
        for ev in cls.EVENTS_INDEX:
            if code.startswith(ev["prefix"].upper()):
                return {
                    "stage_code": code,
                    "event_name": ev["name"],
                    "type": "SIDE_STORY"
                }

        return {"stage_code": code, "type": "CUSTOM_OR_NEW_EVENT"}
