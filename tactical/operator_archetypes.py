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

    # Snipers (狙击)
    "能天使": {"class": OpClass.SNIPER, "rarity": 6, "dmg": DamageType.PHYSICAL, "air": True, "block": 1, "cost": 12, "burst": True},
    "克洛丝": {"class": OpClass.SNIPER, "rarity": 3, "dmg": DamageType.PHYSICAL, "air": True, "block": 1, "cost": 9, "burst": False},
    "蓝毒": {"class": OpClass.SNIPER, "rarity": 5, "dmg": DamageType.PHYSICAL, "air": True, "block": 1, "cost": 11, "burst": True},
    "白金": {"class": OpClass.SNIPER, "rarity": 5, "dmg": DamageType.PHYSICAL, "air": True, "block": 1, "cost": 11, "burst": False},
    "白雪": {"class": OpClass.SNIPER, "rarity": 4, "dmg": DamageType.PHYSICAL, "air": True, "block": 1, "cost": 21, "aoe": True},
    "鸿雪": {"class": OpClass.SNIPER, "rarity": 6, "dmg": DamageType.PHYSICAL, "air": True, "block": 1, "cost": 20, "burst": True},
    "陨星": {"class": OpClass.SNIPER, "rarity": 5, "dmg": DamageType.PHYSICAL, "air": True, "block": 1, "cost": 25, "aoe": True},

    # Casters (术师)
    "艾雅法拉": {"class": OpClass.CASTER, "rarity": 6, "dmg": DamageType.ARTS, "air": True, "block": 1, "cost": 19, "aoe": True, "burst": True},
    "阿米娅": {"class": OpClass.CASTER, "rarity": 5, "dmg": DamageType.ARTS, "air": True, "block": 1, "cost": 18, "burst": True},
    "伊芙利特": {"class": OpClass.CASTER, "rarity": 6, "dmg": DamageType.ARTS, "air": True, "block": 1, "cost": 31, "aoe": True},
    "天火": {"class": OpClass.CASTER, "rarity": 5, "dmg": DamageType.ARTS, "air": True, "block": 1, "cost": 30, "aoe": True},
    "远山": {"class": OpClass.CASTER, "rarity": 4, "dmg": DamageType.ARTS, "air": True, "block": 1, "cost": 28, "aoe": True},
    "史都华德": {"class": OpClass.CASTER, "rarity": 3, "dmg": DamageType.ARTS, "air": True, "block": 1, "cost": 17, "burst": False},

    # Defenders (重装)
    "塞雷娅": {"class": OpClass.DEFENDER, "rarity": 6, "dmg": DamageType.PHYSICAL, "air": False, "block": 3, "cost": 18, "heals": True},
    "蛇屠箱": {"class": OpClass.DEFENDER, "rarity": 4, "dmg": DamageType.PHYSICAL, "air": False, "block": 4, "cost": 16, "heals": False},
    "星熊": {"class": OpClass.DEFENDER, "rarity": 6, "dmg": DamageType.PHYSICAL, "air": False, "block": 3, "cost": 21, "heals": False},
    "临光": {"class": OpClass.DEFENDER, "rarity": 5, "dmg": DamageType.PHYSICAL, "air": False, "block": 3, "cost": 17, "heals": True},
    "古米": {"class": OpClass.DEFENDER, "rarity": 4, "dmg": DamageType.PHYSICAL, "air": False, "block": 3, "cost": 15, "heals": True},
    "米戈": {"class": OpClass.DEFENDER, "rarity": 3, "dmg": DamageType.PHYSICAL, "air": False, "block": 3, "cost": 13, "heals": False},
    "黑角": {"class": OpClass.DEFENDER, "rarity": 2, "dmg": DamageType.PHYSICAL, "air": False, "block": 2, "cost": 12, "heals": False},

    # Medics (医疗)
    "闪灵": {"class": OpClass.MEDIC, "rarity": 6, "dmg": DamageType.HEALING, "air": False, "block": 1, "cost": 17, "aoe": False},
    "夜莺": {"class": OpClass.MEDIC, "rarity": 6, "dmg": DamageType.HEALING, "air": False, "block": 1, "cost": 16, "aoe": True},
    "白面鸮": {"class": OpClass.MEDIC, "rarity": 5, "dmg": DamageType.HEALING, "air": False, "block": 1, "cost": 15, "aoe": True},
    "赫默": {"class": OpClass.MEDIC, "rarity": 5, "dmg": DamageType.HEALING, "air": False, "block": 1, "cost": 16, "aoe": False},
    "调香师": {"class": OpClass.MEDIC, "rarity": 4, "dmg": DamageType.HEALING, "air": False, "block": 1, "cost": 14, "aoe": True},
    "安塞尔": {"class": OpClass.MEDIC, "rarity": 3, "dmg": DamageType.HEALING, "air": False, "block": 1, "cost": 14, "aoe": False},
    "芙蓉": {"class": OpClass.MEDIC, "rarity": 3, "dmg": DamageType.HEALING, "air": False, "block": 1, "cost": 14, "aoe": False},

    # Guards (近卫)
    "银灰": {"class": OpClass.GUARD, "rarity": 6, "dmg": DamageType.PHYSICAL, "air": True, "block": 2, "cost": 18, "burst": True},
    "史尔特尔": {"class": OpClass.GUARD, "rarity": 6, "dmg": DamageType.ARTS, "air": False, "block": 2, "cost": 19, "burst": True},
    "煌": {"class": OpClass.GUARD, "rarity": 6, "dmg": DamageType.PHYSICAL, "air": False, "block": 3, "cost": 22, "aoe": True},
    "拉普兰德": {"class": OpClass.GUARD, "rarity": 5, "dmg": DamageType.ARTS, "air": True, "block": 2, "cost": 17, "silence": True},
    "幽灵鲨": {"class": OpClass.GUARD, "rarity": 5, "dmg": DamageType.PHYSICAL, "air": False, "block": 3, "cost": 21, "aoe": True},
    "玫兰莎": {"class": OpClass.GUARD, "rarity": 3, "dmg": DamageType.PHYSICAL, "air": False, "block": 1, "cost": 13, "burst": False},
    "月见夜": {"class": OpClass.GUARD, "rarity": 3, "dmg": DamageType.ARTS, "air": True, "block": 2, "cost": 15, "burst": False},

    # Specialists / Fast-Redeploy (特种/快活)
    "红": {"class": OpClass.SPECIALIST, "rarity": 5, "dmg": DamageType.PHYSICAL, "air": False, "block": 1, "cost": 8, "fast_redeploy": True},
    "傀影": {"class": OpClass.SPECIALIST, "rarity": 6, "dmg": DamageType.PHYSICAL, "air": False, "block": 1, "cost": 9, "fast_redeploy": True},
    "砾": {"class": OpClass.SPECIALIST, "rarity": 4, "dmg": DamageType.PHYSICAL, "air": False, "block": 1, "cost": 5, "fast_redeploy": True},
    "德克萨斯(异格)": {"class": OpClass.SPECIALIST, "rarity": 6, "dmg": DamageType.ARTS, "air": True, "block": 1, "cost": 9, "fast_redeploy": True, "aoe": True}
}


def lookup_operator_traits(name: str) -> Dict[str, Any]:
    """Look up operator specs or return generalized fallback traits."""
    for known_name, traits in OPERATOR_DATABASE.items():
        if known_name in name or name in known_name:
            t = dict(traits)
            t["resolved_name"] = known_name
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
