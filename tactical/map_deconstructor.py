# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Tactical Map Topology & Grid Deconstructor
Author: Emiliamio <mio2110767128@163.com>
"""

from enum import IntEnum
from typing import List, Tuple, Dict, Any, Optional
import os
import yaml


class TileType(IntEnum):
    """Enumeration of standard Arknights tile capabilities."""
    EMPTY = 0         # Unwalkable, undeployable void
    GROUND = 1        # Walkable, deployable for melee/guards/vanguard/defenders
    HIGH_GROUND = 2   # Unwalkable, deployable for ranged/snipers/medics/casters
    SPAWN = 3         # Red Box (Enemy spawn point, walkable)
    GOAL = 4          # Blue Box (Player base, protection goal, walkable)
    FORBIDDEN = 5     # Ground walkable by enemies, but undeployable for operators
    HOLE = 6          # Pitfall hazard


class TacticalMap:
    """
    Represents the logical grid topology of an Arknights combat zone.
    Provides connectivity querying, walkability checks, and tactical spatial reasoning.
    """

    def __init__(
        self,
        name: str,
        rows: int,
        cols: int,
        grid: Optional[List[List[TileType]]] = None,
        spawns: Optional[List[Tuple[int, int]]] = None,
        goals: Optional[List[Tuple[int, int]]] = None
    ):
        self.name = name
        self.rows = rows
        self.cols = cols
        self.grid = grid or [[TileType.EMPTY for _ in range(cols)] for _ in range(rows)]
        self.spawns = spawns or []
        self.goals = goals or []

        # Auto-detect spawns and goals if not explicitly passed
        if not self.spawns or not self.goals:
            self._reindex_special_tiles()

    def _reindex_special_tiles(self) -> None:
        """Finds all SPAWN and GOAL coordinates inside the grid."""
        found_spawns = []
        found_goals = []
        for r in range(self.rows):
            for c in range(self.cols):
                tile = self.grid[r][c]
                if tile == TileType.SPAWN:
                    found_spawns.append((r, c))
                elif tile == TileType.GOAL:
                    found_goals.append((r, c))

        if found_spawns:
            self.spawns = found_spawns
        if found_goals:
            self.goals = found_goals

    def in_bounds(self, r: int, c: int) -> bool:
        """Checks if (r, c) is within map bounds."""
        return 0 <= r < self.rows and 0 <= c < self.cols

    def get_tile(self, r: int, c: int) -> TileType:
        """Retrieves tile type at (r, c). Returns EMPTY if out of bounds."""
        if not self.in_bounds(r, c):
            return TileType.EMPTY
        return self.grid[r][c]

    def set_tile(self, r: int, c: int, tile_type: TileType) -> None:
        """Sets tile type at (r, c)."""
        if not self.in_bounds(r, c):
            raise IndexError(f"Coordinate ({r}, {c}) is out of bounds for map {self.rows}x{self.cols}")
        self.grid[r][c] = tile_type
        if tile_type == TileType.SPAWN and (r, c) not in self.spawns:
            self.spawns.append((r, c))
        elif tile_type == TileType.GOAL and (r, c) not in self.goals:
            self.goals.append((r, c))

    def is_walkable(self, r: int, c: int) -> bool:
        """Checks if enemies can traverse this tile."""
        tile = self.get_tile(r, c)
        return tile in (TileType.GROUND, TileType.FORBIDDEN, TileType.SPAWN, TileType.GOAL)

    def is_deployable_ground(self, r: int, c: int) -> bool:
        """Checks if player can deploy melee/ground operators on this tile."""
        return self.get_tile(r, c) == TileType.GROUND

    def is_deployable_high(self, r: int, c: int) -> bool:
        """Checks if player can deploy ranged/high ground operators on this tile."""
        return self.get_tile(r, c) == TileType.HIGH_GROUND

    def get_walkable_neighbors(self, r: int, c: int) -> List[Tuple[int, int]]:
        """Returns valid 4-directional adjacent tiles that enemies can walk onto."""
        neighbors = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if self.in_bounds(nr, nc) and self.is_walkable(nr, nc):
                neighbors.append((nr, nc))
        return neighbors

    @classmethod
    def from_ascii_art(
        cls,
        name: str,
        lines: List[str],
        legend: Optional[Dict[str, TileType]] = None
    ) -> "TacticalMap":
        """
        Parses ASCII matrix representation into a TacticalMap instance.
        Default Legend:
          '.' = GROUND
          '#' = HIGH_GROUND
          'S' = SPAWN (Red box)
          'G' = GOAL (Blue box)
          'X' = FORBIDDEN (Walkable ground, cannot deploy)
          '_' or ' ' = EMPTY
        """
        default_legend = {
            ".": TileType.GROUND,
            "#": TileType.HIGH_GROUND,
            "S": TileType.SPAWN,
            "G": TileType.GOAL,
            "X": TileType.FORBIDDEN,
            "_": TileType.EMPTY,
            " ": TileType.EMPTY
        }
        active_legend = {**default_legend, **(legend or {})}

        clean_lines = [line.rstrip("\r\n") for line in lines if line.strip()]
        rows = len(clean_lines)
        cols = max(len(l) for l in clean_lines) if rows > 0 else 0

        grid = []
        spawns = []
        goals = []

        for r, line in enumerate(clean_lines):
            row_tiles = []
            for c in range(cols):
                char = line[c] if c < len(line) else "_"
                tile = active_legend.get(char, TileType.EMPTY)
                row_tiles.append(tile)
                if tile == TileType.SPAWN:
                    spawns.append((r, c))
                elif tile == TileType.GOAL:
                    goals.append((r, c))
            grid.append(row_tiles)

        return cls(name=name, rows=rows, cols=cols, grid=grid, spawns=spawns, goals=goals)

    def to_ascii_art(self) -> str:
        """Exports map back to human-readable ASCII format."""
        tile_to_char = {
            TileType.GROUND: ".",
            TileType.HIGH_GROUND: "#",
            TileType.SPAWN: "S",
            TileType.GOAL: "G",
            TileType.FORBIDDEN: "X",
            TileType.EMPTY: "_",
            TileType.HOLE: "O"
        }
        lines = []
        for row in self.grid:
            lines.append("".join(tile_to_char.get(t, "_") for t in row))
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes map to dictionary."""
        return {
            "name": self.name,
            "rows": self.rows,
            "cols": self.cols,
            "spawns": [list(p) for p in self.spawns],
            "goals": [list(p) for p in self.goals],
            "ascii": self.to_ascii_art()
        }

    def save_yaml(self, filepath: str) -> None:
        """Saves map to YAML file."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, allow_unicode=True, sort_keys=False)

    @classmethod
    def load_yaml(cls, filepath: str) -> "TacticalMap":
        """Loads map from YAML file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        ascii_lines = data["ascii"].splitlines()
        return cls.from_ascii_art(name=data.get("name", "Unnamed"), lines=ascii_lines)

    @classmethod
    def create_1_7(cls) -> "TacticalMap":
        """
        Creates canonical 1-7 ("固源岩圣地") tactical map.
        6 rows x 11 cols:
        Left: Spawns S (r=1, c=0; r=4, c=0)
        Right: Goal G (r=2, c=10)
        Middle: High ground platforms (#) and deployable ground roads (.).
        """
        ascii_map = [
            "__######___",
            "S....#...._",
            "_.##...##.G",
            "_.##...##._",
            "S....#...._",
            "__######___"
        ]
        return cls.from_ascii_art("Level_1-7", ascii_map)