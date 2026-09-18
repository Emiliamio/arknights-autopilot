# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Phase 2 Probe: Spatial Geometry, Homography Mapping & Tactical Brain
Author: Emiliamio <mio2110767128@163.com>
"""

import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np
import cv2

from core.homography_mapper import HomographyMapper
from tactical.map_deconstructor import TacticalMap, TileType
from tactical.choke_point_analyzer import AStarPathfinder, ChokePointAnalyzer, HighGroundScorer


def run_phase2_probe():
    print("======================================================================")
    print("  [*] ASTA Phase 2: Spatial Homography & Tactical Choke Point Deduction")
    print("  Author: Emiliamio <mio2110767128@163.com>")
    print("======================================================================")

    # 1. Load canonical 1-7 level
    map_path = "data/maps/1-7.yaml"
    if os.path.exists(map_path):
        tactical_map = TacticalMap.load_yaml(map_path)
    else:
        tactical_map = TacticalMap.create_1_7()

    print(f"[*] Loaded Map: {tactical_map.name} ({tactical_map.rows} rows x {tactical_map.cols} cols)")
    print(f"[*] Spawns (Red Gates): {tactical_map.spawns}")
    print(f"[*] Goals (Blue Bases): {tactical_map.goals}")
    print("[*] Map ASCII Topology:")
    for line in tactical_map.to_ascii_art().splitlines():
        print(f"    {line}")

    # 2. Execute A* path deduction and choke point extraction
    analyzer = ChokePointAnalyzer(tactical_map)
    analysis = analyzer.analyze_choke_points()
    routes = analysis["routes"]
    print(f"[+] Total Enemy Pathways Deduced: {len(routes)}")
    for i, r in enumerate(routes):
        path_str = " -> ".join([f"({nr},{nc})" for nr, nc in r["path"]])
        print(f"    Route #{i+1} [Spawn {r['spawn']} -> Goal {r['goal']}]: len={r['length']} | {path_str}")

    primary = analysis["primary_choke"]
    secondaries = analysis["secondary_chokes"]
    print(f"[+] Primary Choke Point (Gold Gate): {primary['coord']} | Heat: {primary['heat']} | Criticality: {primary['criticality']*100:.1f}%")
    for i, sc in enumerate(secondaries):
        print(f"    Secondary Choke #{i+1}: {sc['coord']} | Heat: {sc['heat']} | Criticality: {sc['criticality']*100:.1f}%")

    # 3. High ground tactical coverage scoring
    scorer = HighGroundScorer(tactical_map)
    high_grounds = scorer.score_high_grounds(analysis)
    print(f"[+] Scored High Ground Positions: {len(high_grounds)}")
    for i, hg in enumerate(high_grounds[:3]):
        print(f"    Top #{i+1} High Ground: {hg['coord']} | Facing: {hg['optimal_orientation'].upper()} | Score: {hg['tactical_score']} (Chokes: {hg['covered_chokes_count']}, Paths: {hg['covered_paths_count']})")

    # 4. Calibrate 2.5D Homography Mapper
    print("[*] Generating 2.5D Perspective Homography Matrix for 1920x1080 screen...")
    mapper = HomographyMapper.create_synthetic_arknights_mapper(
        cols=tactical_map.cols,
        rows=tactical_map.rows,
        screen_resolution=(1920, 1080)
    )

    # 5. Render Tactical Synthesis Visualizer
    print("[*] Rendering 1080P Tactical Heat & Trajectory Synthesis Map...")
    canvas = np.zeros((1080, 1920, 3), dtype=np.uint8)
    canvas[:] = (24, 28, 35)  # Dark Tactical Background

    # Draw grid tiles
    for r in range(tactical_map.rows):
        for c in range(tactical_map.cols):
            tile = tactical_map.get_tile(r, c)
            poly = np.array(mapper.get_tile_polygon(c, r), dtype=np.int32)

            if tile == TileType.GROUND:
                cv2.fillPoly(canvas, [poly], (45, 52, 60))
                cv2.polylines(canvas, [poly], True, (65, 75, 88), 1)
            elif tile == TileType.HIGH_GROUND:
                cv2.fillPoly(canvas, [poly], (70, 65, 50))
                cv2.polylines(canvas, [poly], True, (110, 100, 80), 1)
            elif tile == TileType.SPAWN:
                cv2.fillPoly(canvas, [poly], (40, 40, 130))
                cv2.polylines(canvas, [poly], True, (60, 60, 220), 2)
            elif tile == TileType.GOAL:
                cv2.fillPoly(canvas, [poly], (130, 80, 30))
                cv2.polylines(canvas, [poly], True, (220, 140, 50), 2)
            elif tile == TileType.EMPTY:
                cv2.polylines(canvas, [poly], True, (35, 40, 48), 1)

    # Draw enemy path trajectories (Red vectors)
    for route in routes:
        pts = [mapper.get_tile_center(nc, nr) for nr, nc in route["path"]]
        for i in range(len(pts) - 1):
            cv2.arrowedLine(canvas, pts[i], pts[i+1], (0, 0, 255), 2, tipLength=0.2)

    # Highlight Primary Choke Point (Gold)
    if primary:
        pr, pc = primary["coord"]
        choke_center = mapper.get_tile_center(pc, pr)
        cv2.circle(canvas, choke_center, 22, (0, 215, 255), 3)
        cv2.putText(canvas, "CHOKE", (choke_center[0] - 30, choke_center[1] - 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 215, 255), 2)

    # Highlight Top High Grounds (Cyan)
    for hg in high_grounds[:2]:
        hr, hc = hg["coord"]
        hg_center = mapper.get_tile_center(hc, hr)
        cv2.circle(canvas, hg_center, 18, (255, 220, 0), 2)
        orient = hg["optimal_orientation"]
        dv = HighGroundScorer.ORIENTATION_VECTORS.get(orient, (0, 1))
        arrow_end = (hg_center[0] + dv[1] * 40, hg_center[1] + dv[0] * 40)
        cv2.arrowedLine(canvas, hg_center, arrow_end, (255, 220, 0), 2, tipLength=0.3)
        cv2.putText(canvas, f"SNIPER [{orient.upper()}]", (hg_center[0] - 45, hg_center[1] - 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 220, 0), 1)

    # Title & Legend
    cv2.putText(canvas, "ASTA Tactical Autopilot - Phase 2 Spatial & Choke Deduction",
                (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(canvas, f"Map: {tactical_map.name} (6x11) | Primary Choke: {primary['coord']} | Paths: {len(routes)}",
                (40, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1)

    os.makedirs("data", exist_ok=True)
    out_img_path = os.path.abspath("data/tactical_overlay_sample.png")
    cv2.imwrite(out_img_path, canvas)
    print(f"[+] Tactical Visualization rendered & saved to: {out_img_path} ({os.path.getsize(out_img_path):,} bytes)")

    print("======================================================================")
    print("  [SUCCESS] PHASE 2 PROBE 100% COMPLETE: TACTICAL DEDUCTION OPERATIONAL!")
    print("======================================================================")
    return {
        "analysis": analysis,
        "high_grounds": high_grounds,
        "visual_path": out_img_path
    }


if __name__ == "__main__":
    run_phase2_probe()