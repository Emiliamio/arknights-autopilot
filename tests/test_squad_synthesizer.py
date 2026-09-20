# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Unit Tests for SquadSynthesizer & StageTacticalProfile
Author: Emiliamio <mio2110767128@163.com>
"""

import pytest
from tactical.squad_synthesizer import SquadSynthesizer
from tactical.stage_analyzer import analyze_stage_requirements, StageTacticalProfile


def test_stage_tactical_profile_quotas():
    # Standard balanced profile
    p_norm = StageTacticalProfile(stage_id="NORM", air_threat="MEDIUM", armor_threat="MEDIUM")
    q_norm = p_norm.compute_role_quotas()
    assert sum(q_norm.values()) == 12
    assert q_norm["VANGUARD"] == 2
    assert q_norm["SNIPER"] == 2

    # High Air threat
    p_air = StageTacticalProfile(stage_id="AIR_HIGH", air_threat="HIGH")
    q_air = p_air.compute_role_quotas()
    assert sum(q_air.values()) == 12
    assert q_air["SNIPER"] == 3


def test_squad_synthesizer_12_operator_guarantee(tmp_path):
    syn = SquadSynthesizer()
    res = syn.synthesize_squad(account_id="EMILIAMIO_MAIN", stage_id="1-7")

    assert res["total_operators"] == 12
    assert len(res["squad"]) == 12

    # Verify unique operators in lineup
    names = [op["name"] for op in res["squad"]]
    assert len(set(names)) == 12

    # Check presence of vital roles
    classes = [op["class"] for op in res["squad"]]
    assert "VANGUARD" in classes
    assert "SNIPER" in classes
    assert "DEFENDER" in classes
    assert "MEDIC" in classes


def test_squad_synthesizer_air_counter_behavior():
    syn = SquadSynthesizer()
    res = syn.synthesize_squad(account_id="EMILIAMIO_MAIN", stage_id="0-4")

    # High air threat stage 0-4 should include top anti-air snipers
    sniper_names = [op["name"] for op in res["squad"] if op["class"] == "SNIPER"]
    assert "能天使" in sniper_names
