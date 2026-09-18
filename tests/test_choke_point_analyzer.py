# -*- coding: utf-8 -*-
"""
Unit tests for TacticalMap, A* Pathfinder, DAG Flow & ChokePointAnalyzer
Author: Emiliamio <mio2110767128@163.com>
"""

import pytest
from tactical.map_deconstructor import TacticalMap, TileType
from tactical.choke_point_analyzer import AStarPathfinder, ChokePointAnalyzer, HighGroundScorer


@pytest.fixture
def map_1_7():
    return TacticalMap.create_1_7()


def test_map_1_7_structure(map_1_7):
    assert map_1_7.rows == 6
    assert map_1_7.cols == 11
    assert len(map_1_7.spawns) == 2, f"1-7 has 2 red spawns, found {len(map_1_7.spawns)}"
    assert len(map_1_7.goals) == 1, f"1-7 has 1 blue goal, found {len(map_1_7.goals)}"
    assert map_1_7.is_walkable(map_1_7.spawns[0][0], map_1_7.spawns[0][1])
    assert map_1_7.is_walkable(map_1_7.goals[0][0], map_1_7.goals[0][1])


def test_astar_pathfinding(map_1_7):
    pathfinder = AStarPathfinder(map_1_7)
    paths = pathfinder.find_all_spawn_goal_paths()
    assert len(paths) == 2, f"Expected 2 paths (one per spawn to goal), got {len(paths)}"
    for p in paths:
        assert p["length"] > 0
        assert p["path"][0] == p["spawn"]
        assert p["path"][-1] == p["goal"]


def test_bifurcation_dag_flow_detection():
    # Symmetrical bifurcation map:
    # S . # . G
    # with top and bottom corridors
    m = TacticalMap.from_ascii_art("Bifurcation", [
        ".....",
        "S.#.G",
        "....."
    ])
    pathfinder = AStarPathfinder(m)
    flow = pathfinder.compute_shortest_path_dag_flow((1, 0), (1, 4))
    assert len(flow) > 0

    # Start and Goal must have 100% flow
    assert flow[(1, 0)] == 1.0
    assert flow[(1, 4)] == 1.0

    # Obstacle in center has 0 flow
    assert (1, 2) not in flow or flow[(1, 2)] == 0.0

    # Both top and bottom bypass corridors must be detected with 50% flow
    top_flow = flow.get((0, 2), 0.0)
    bottom_flow = flow.get((2, 2), 0.0)
    assert top_flow == 0.5, f"Expected top branch flow 0.5, got {top_flow}"
    assert bottom_flow == 0.5, f"Expected bottom branch flow 0.5, got {bottom_flow}"


def test_choke_point_extraction(map_1_7):
    analyzer = ChokePointAnalyzer(map_1_7)
    res = analyzer.analyze_choke_points()

    assert res["routes_count"] == 2
    assert res["primary_choke"] is not None
    pr, pc = res["primary_choke"]["coord"]

    assert map_1_7.is_deployable_ground(pr, pc), "Choke point must be a deployable ground tile"
    assert res["primary_choke"]["flow"] > 0.0


def test_high_ground_sniper_scoring(map_1_7):
    analyzer = ChokePointAnalyzer(map_1_7)
    choke_res = analyzer.analyze_choke_points()

    scorer = HighGroundScorer(map_1_7)
    high_ground_ranks = scorer.score_high_grounds(choke_res)

    assert len(high_ground_ranks) > 0, "Must find valuable high ground tiles"
    top_pos = high_ground_ranks[0]
    assert "coord" in top_pos
    assert "optimal_orientation" in top_pos
    assert top_pos["optimal_orientation"] in ["up", "down", "left", "right"]
    assert top_pos["tactical_score"] > 0.0


def test_high_ground_medic_scoring(map_1_7):
    analyzer = ChokePointAnalyzer(map_1_7)
    choke_res = analyzer.analyze_choke_points()

    scorer = HighGroundScorer(map_1_7)
    medic_ranks = scorer.score_medic_positions(choke_res)

    assert len(medic_ranks) > 0, "Must find high ground tiles capable of healing choke points"
    top_medic = medic_ranks[0]
    assert top_medic["medic_score"] >= 10.0
    assert top_medic["healed_chokes_count"] >= 1