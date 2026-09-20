# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Arknights Operator Archetypes & Class Capability Knowledge Base
Author: Emiliamio <mio2110767128@163.com>
"""

from enum import Enum
from typing import Dict, Any, List, Optional


class OpClass(Enum):
    VANGUARD = "VANGUARD"      # 先锋
    GUARD = "GUARD"            # 近卫
    DEFENDER = "DEFENDER"      # 重装
    SNIPER = "SNIPER"          # 狙击
    CASTER = "CASTER"          # 术师
    MEDIC = "MEDIC"            # 医疗
    SUPPORTER = "SUPPORTER"    # 辅助
    SPECIALIST = "SPECIALIST"  # 特种


class DamageType(Enum):
    PHYSICAL = "PHYSICAL"
    ARTS = "ARTS"
    TRUE = "TRUE"
    HEALING = "HEALING"
    NONE = "NONE"


# Comprehensive Operator Knowledge Base mapping common Chinese names to traits
OPERATOR_DATABASE: Dict[str, Dict[str, Any]] = {
    # Vanguards (先锋)
    "德克萨斯": {"class": OpClass.VANGUARD, "rarity": 5, "dmg": DamageType.PHYSICAL, "air": False, "block": 2, "cost": 11, "can_gen_dp": True},
    "桃金娘": {"class": OpClass.VANGUARD, "rarity": 4, "dmg": DamageType.NONE, "air": False, "block": 1, "cost": 8, "can_gen_dp": True},
    "极境": {"class": OpClass.VANGUARD, "rarity": 5, "dmg": DamageType.PHYSICAL, "air": False, "block": 1, "cost": 9, "can_gen_dp": True},
    "推进之王": {"class": OpClass.VANGUARD, "rarity": 6, "dmg": DamageType.PHYSICAL, "air": False, "block": 2, "cost": 12, "can_gen_dp": True},
    "风笛": {"class": OpClass.VANGUARD, "rarity": 6, "dmg": DamageType.PHYSICAL, "air": False, "block": 1, "cost": 13, "can_gen_dp": True},
    "讯使": {"class": OpClass.VANGUARD, "rarity": 4, "dmg": DamageType.PHYSICAL, "air": False, "block": 2, "cost": 10, "can_gen_dp": True},
    "红豆": {"class": OpClass.VANGUARD, "rarity": 4, "dmg": DamageType.PHYSICAL, "air": False, "block": 1, "cost": 9, "can_gen_dp": True},
    "芬": {"class": OpClass.VANGUARD, "rarity": 3, "dmg": DamageType.PHYSICAL, "air": False, "block": 2, "cost": 8, "can_gen_dp": True},
    "夜刀": {"class": OpClass.VANGUARD, "rarity": 2, "dmg": DamageType.PHYSICAL, "air": False, "block": 2, "cost": 7, "can_gen_dp": False},

    "伊内丝": {"class": OpClass.VANGUARD, "rarity": 6, "dmg": DamageType.PHYSICAL, "air": True, "block": 1, "cost": 11, "can_gen_dp": True, "roguelike_tier": "S"},

    # Snipers (狙击)
    "能天使": {"class": OpClass.SNIPER, "rarity": 6, "dmg": DamageType.PHYSICAL, "air": True, "block": 1, "cost": 12, "burst": True, "roguelike_tier": "A"},
    "克洛丝": {"class": OpClass.SNIPER, "rarity": 3, "dmg": DamageType.PHYSICAL, "air": True, "block": 1, "cost": 9, "burst": False, "roguelike_tier": "S"},
    "蓝毒": {"class": OpClass.SNIPER, "rarity": 5, "dmg": DamageType.PHYSICAL, "air": True, "block": 1, "cost": 11, "burst": True, "roguelike_tier": "B"},
    "白金": {"class": OpClass.SNIPER, "rarity": 5, "dmg": DamageType.PHYSICAL, "air": True, "block": 1, "cost": 11, "burst": False, "roguelike_tier": "B"},
    "白雪": {"class": OpClass.SNIPER, "rarity": 4, "dmg": DamageType.PHYSICAL, "air": True, "block": 1, "cost": 21, "aoe": True, "roguelike_tier": "B"},
    "鸿雪": {"class": OpClass.SNIPER, "rarity": 6, "dmg": DamageType.PHYSICAL, "air": True, "block": 1, "cost": 20, "burst": True, "roguelike_tier": "S"},
    "陨星": {"class": OpClass.SNIPER, "rarity": 5, "dmg": DamageType.PHYSICAL, "air": True, "block": 1, "cost": 25, "aoe": True, "roguelike_tier": "B"},

    # Casters (术师)
    "艾雅法拉": {"class": OpClass.CASTER, "rarity": 6, "dmg": DamageType.ARTS, "air": True, "block": 1, "cost": 19, "aoe": True, "burst": True, "roguelike_tier": "S"},
    "澄闪": {"class": OpClass.CASTER, "rarity": 6, "dmg": DamageType.ARTS, "air": True, "block": 1, "cost": 21, "aoe": False, "burst": True, "global": True, "roguelike_tier": "S"},
    "阿米娅": {"class": OpClass.CASTER, "rarity": 5, "dmg": DamageType.ARTS, "air": True, "block": 1, "cost": 18, "burst": True, "roguelike_tier": "A"},
    "伊芙利特": {"class": OpClass.CASTER, "rarity": 6, "dmg": DamageType.ARTS, "air": True, "block": 1, "cost": 31, "aoe": True, "roguelike_tier": "A"},
    "天火": {"class": OpClass.CASTER, "rarity": 5, "dmg": DamageType.ARTS, "air": True, "block": 1, "cost": 30, "aoe": True, "roguelike_tier": "C"},
    "远山": {"class": OpClass.CASTER, "rarity": 4, "dmg": DamageType.ARTS, "air": True, "block": 1, "cost": 28, "aoe": True, "roguelike_tier": "B"},
    "史都华德": {"class": OpClass.CASTER, "rarity": 3, "dmg": DamageType.ARTS, "air": True, "block": 1, "cost": 17, "burst": False, "roguelike_tier": "A"},

    # Defenders (重装)
    "塞雷娅": {"class": OpClass.DEFENDER, "rarity": 6, "dmg": DamageType.PHYSICAL, "air": False, "block": 3, "cost": 18, "heals": True, "roguelike_tier": "S"},
    "斑点": {"class": OpClass.DEFENDER, "rarity": 3, "dmg": DamageType.PHYSICAL, "air": False, "block": 3, "cost": 15, "heals": True, "roguelike_tier": "S"},
    "蛇屠箱": {"class": OpClass.DEFENDER, "rarity": 4, "dmg": DamageType.PHYSICAL, "air": False, "block": 4, "cost": 16, "heals": False, "roguelike_tier": "B"},
    "星熊": {"class": OpClass.DEFENDER, "rarity": 6, "dmg": DamageType.PHYSICAL, "air": False, "block": 3, "cost": 21, "heals": False, "roguelike_tier": "A"},
    "临光": {"class": OpClass.DEFENDER, "rarity": 5, "dmg": DamageType.PHYSICAL, "air": False, "block": 3, "cost": 17, "heals": True, "roguelike_tier": "A"},
    "古米": {"class": OpClass.DEFENDER, "rarity": 4, "dmg": DamageType.PHYSICAL, "air": False, "block": 3, "cost": 15, "heals": True, "roguelike_tier": "A"},
    "米戈": {"class": OpClass.DEFENDER, "rarity": 3, "dmg": DamageType.PHYSICAL, "air": False, "block": 3, "cost": 13, "heals": False, "roguelike_tier": "C"},
    "黑角": {"class": OpClass.DEFENDER, "rarity": 2, "dmg": DamageType.PHYSICAL, "air": False, "block": 2, "cost": 12, "heals": False, "roguelike_tier": "C"},

    # Medics (医疗)
    "纯烬艾雅法拉": {"class": OpClass.MEDIC, "rarity": 6, "dmg": DamageType.HEALING, "air": False, "block": 1, "cost": 17, "aoe": True, "roguelike_tier": "S"},
    "闪灵": {"class": OpClass.MEDIC, "rarity": 6, "dmg": DamageType.HEALING, "air": False, "block": 1, "cost": 17, "aoe": False, "roguelike_tier": "B"},
    "夜莺": {"class": OpClass.MEDIC, "rarity": 6, "dmg": DamageType.HEALING, "air": False, "block": 1, "cost": 16, "aoe": True, "roguelike_tier": "A"},
    "白面鸮": {"class": OpClass.MEDIC, "rarity": 5, "dmg": DamageType.HEALING, "air": False, "block": 1, "cost": 15, "aoe": True, "roguelike_tier": "A"},
    "苏苏洛": {"class": OpClass.MEDIC, "rarity": 4, "dmg": DamageType.HEALING, "air": False, "block": 1, "cost": 15, "aoe": False, "burst": True, "roguelike_tier": "A"},
    "赫默": {"class": OpClass.MEDIC, "rarity": 5, "dmg": DamageType.HEALING, "air": False, "block": 1, "cost": 16, "aoe": False, "roguelike_tier": "B"},
    "调香师": {"class": OpClass.MEDIC, "rarity": 4, "dmg": DamageType.HEALING, "air": False, "block": 1, "cost": 14, "aoe": True, "roguelike_tier": "B"},
    "安塞尔": {"class": OpClass.MEDIC, "rarity": 3, "dmg": DamageType.HEALING, "air": False, "block": 1, "cost": 14, "aoe": False, "roguelike_tier": "A"},
    "芙蓉": {"class": OpClass.MEDIC, "rarity": 3, "dmg": DamageType.HEALING, "air": False, "block": 1, "cost": 14, "aoe": False, "roguelike_tier": "B"},

    # Guards (近卫)
    "玛恩纳": {"class": OpClass.GUARD, "rarity": 6, "dmg": DamageType.TRUE, "air": True, "block": 3, "cost": 12, "burst": True, "roguelike_tier": "S"},
    "史尔特尔": {"class": OpClass.GUARD, "rarity": 6, "dmg": DamageType.ARTS, "air": False, "block": 2, "cost": 19, "burst": True, "roguelike_tier": "S"},
    "银灰": {"class": OpClass.GUARD, "rarity": 6, "dmg": DamageType.PHYSICAL, "air": True, "block": 2, "cost": 18, "burst": True, "roguelike_tier": "A"},
    "煌": {"class": OpClass.GUARD, "rarity": 6, "dmg": DamageType.PHYSICAL, "air": False, "block": 3, "cost": 22, "aoe": True, "roguelike_tier": "A"},
    "拉普兰德": {"class": OpClass.GUARD, "rarity": 5, "dmg": DamageType.ARTS, "air": True, "block": 2, "cost": 17, "silence": True, "roguelike_tier": "A"},
    "幽灵鲨": {"class": OpClass.GUARD, "rarity": 5, "dmg": DamageType.PHYSICAL, "air": False, "block": 3, "cost": 21, "aoe": True, "roguelike_tier": "A"},
    "玫兰莎": {"class": OpClass.GUARD, "rarity": 3, "dmg": DamageType.PHYSICAL, "air": False, "block": 1, "cost": 13, "burst": False, "roguelike_tier": "A"},
    "月见夜": {"class": OpClass.GUARD, "rarity": 3, "dmg": DamageType.ARTS, "air": True, "block": 2, "cost": 15, "burst": False, "roguelike_tier": "B"},

    # Supporters (辅助)
    "梓兰": {"class": OpClass.SUPPORTER, "rarity": 3, "dmg": DamageType.ARTS, "air": True, "block": 1, "cost": 11, "slow": True, "roguelike_tier": "A"},
    "铃兰": {"class": OpClass.SUPPORTER, "rarity": 6, "dmg": DamageType.ARTS, "air": True, "block": 1, "cost": 13, "slow": True, "fragile": True, "roguelike_tier": "S"},

    # Specialists / Fast-Redeploy (特种/快活)
    "麒麟R夜刀": {"class": OpClass.SPECIALIST, "rarity": 6, "dmg": DamageType.PHYSICAL, "air": True, "block": 1, "cost": 10, "fast_redeploy": True, "burst": True, "roguelike_tier": "S"},
    "德克萨斯(异格)": {"class": OpClass.SPECIALIST, "rarity": 6, "dmg": DamageType.ARTS, "air": True, "block": 1, "cost": 9, "fast_redeploy": True, "aoe": True, "roguelike_tier": "S"},
    "红": {"class": OpClass.SPECIALIST, "rarity": 5, "dmg": DamageType.PHYSICAL, "air": False, "block": 1, "cost": 8, "fast_redeploy": True, "roguelike_tier": "A"},
    "傀影": {"class": OpClass.SPECIALIST, "rarity": 6, "dmg": DamageType.PHYSICAL, "air": False, "block": 1, "cost": 9, "fast_redeploy": True, "roguelike_tier": "A"},
    "孑": {"class": OpClass.SPECIALIST, "rarity": 4, "dmg": DamageType.PHYSICAL, "air": False, "block": 1, "cost": 5, "fast_redeploy": False, "heals": True, "roguelike_tier": "S"},
    "砾": {"class": OpClass.SPECIALIST, "rarity": 4, "dmg": DamageType.PHYSICAL, "air": False, "block": 1, "cost": 5, "fast_redeploy": True, "roguelike_tier": "A"}
}


def lookup_operator_traits(name: str) -> Dict[str, Any]:
    """Look up operator specs or return generalized fallback traits."""
    # 1. Exact match takes strict priority
    if name in OPERATOR_DATABASE:
        t = dict(OPERATOR_DATABASE[name])
        t["resolved_name"] = name
        return t

    # 2. Substring matching (prefer longest matched name, e.g. 纯烬艾雅法拉 > 艾雅法拉)
    matches = []
    for known_name, traits in OPERATOR_DATABASE.items():
        if known_name in name or name in known_name:
            matches.append((len(known_name), known_name, traits))

    if matches:
        matches.sort(key=lambda x: -x[0])
        best = matches[0]
        t = dict(best[2])
        t["resolved_name"] = best[1]
        return t

    # Default fallback heuristics based on generic role guess
    return {
        "resolved_name": name,
        "class": OpClass.GUARD,
        "rarity": 4,
        "dmg": DamageType.PHYSICAL,
        "air": False,
        "block": 2,
        "cost": 15,
        "fast_redeploy": False
    }
