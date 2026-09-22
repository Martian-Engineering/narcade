from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import pairwise

from ...core import Action, Observation

ROWS = 20
COLS = 10

SHAPES: dict[str, tuple[tuple[tuple[int, int], ...], ...]] = {
    "I": (
        ((0, 0), (0, 1), (0, 2), (0, 3)),
        ((0, 0), (1, 0), (2, 0), (3, 0)),
    ),
    "O": (((0, 0), (0, 1), (1, 0), (1, 1)),),
    "T": (
        ((0, 0), (0, 1), (0, 2), (1, 1)),
        ((0, 1), (1, 0), (1, 1), (2, 1)),
        ((0, 1), (1, 0), (1, 1), (1, 2)),
        ((0, 0), (1, 0), (1, 1), (2, 0)),
    ),
    "S": (
        ((0, 1), (0, 2), (1, 0), (1, 1)),
        ((0, 0), (1, 0), (1, 1), (2, 1)),
    ),
    "Z": (
        ((0, 0), (0, 1), (1, 1), (1, 2)),
        ((0, 1), (1, 0), (1, 1), (2, 0)),
    ),
    "J": (
        ((0, 0), (1, 0), (1, 1), (1, 2)),
        ((0, 0), (0, 1), (1, 0), (2, 0)),
        ((0, 0), (0, 1), (0, 2), (1, 2)),
        ((0, 1), (1, 1), (2, 0), (2, 1)),
    ),
    "L": (
        ((0, 2), (1, 0), (1, 1), (1, 2)),
        ((0, 0), (1, 0), (2, 0), (2, 1)),
        ((0, 0), (0, 1), (0, 2), (1, 0)),
        ((0, 0), (0, 1), (1, 1), (2, 1)),
    ),
}


@dataclass(frozen=True)
class Placement:
    action_id: str
    rotation: int
    column: int
    row: int
    board: tuple[tuple[int, ...], ...]
    lines: int
    aggregate_height: int
    holes: int
    bumpiness: int


class Tetris:
    id = "tetris"
    score_name = "arcade_score"

    def __init__(self, seed: int, difficulty: str = "medium", piece_limit: int = 200):
        if difficulty != "medium":
            raise ValueError("Tetris has one ruleset; use --difficulty medium")
        self.seed = seed
        self.difficulty = difficulty
        self.piece_limit = piece_limit
        self._rng = random.Random(seed)
        self._bag: list[str] = []
        self._board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        self.current = self._next_piece()
        self.next_piece = self._next_piece()
        self.score = 0
        self.lines = 0
        self.pieces = 0
        self._done = False
        self._success = False
        self._terminal_reason = "playing"

    @property
    def done(self) -> bool:
        return self._done

    def _next_piece(self) -> str:
        if not self._bag:
            self._bag = list(SHAPES)
            self._rng.shuffle(self._bag)
        return self._bag.pop()

    @staticmethod
    def _fits(
        board: list[list[int]],
        shape: tuple[tuple[int, int], ...],
        row: int,
        col: int,
    ) -> bool:
        return all(
            0 <= row + dy < ROWS and 0 <= col + dx < COLS and board[row + dy][col + dx] == 0
            for dy, dx in shape
        )

    @staticmethod
    def _stats(board: list[list[int]]) -> tuple[int, int, int]:
        heights = []
        holes = 0
        for col in range(COLS):
            top = next((row for row in range(ROWS) if board[row][col]), ROWS)
            height = ROWS - top
            heights.append(height)
            if height:
                holes += sum(board[row][col] == 0 for row in range(top, ROWS))
        bumpiness = sum(abs(left - right) for left, right in pairwise(heights))
        return sum(heights), holes, bumpiness

    def _placements(self) -> list[Placement]:
        placements = []
        for rotation, shape in enumerate(SHAPES[self.current]):
            width = max(dx for _, dx in shape) + 1
            for column in range(COLS - width + 1):
                if not self._fits(self._board, shape, 0, column):
                    continue
                row = 0
                while self._fits(self._board, shape, row + 1, column):
                    row += 1
                board = [line[:] for line in self._board]
                for dy, dx in shape:
                    board[row + dy][column + dx] = 1
                kept = [line for line in board if not all(line)]
                lines = ROWS - len(kept)
                board = [[0] * COLS for _ in range(lines)] + kept
                aggregate_height, holes, bumpiness = self._stats(board)
                placements.append(
                    Placement(
                        action_id=f"r{rotation}_c{column}",
                        rotation=rotation,
                        column=column,
                        row=row,
                        board=tuple(tuple(line) for line in board),
                        lines=lines,
                        aggregate_height=aggregate_height,
                        holes=holes,
                        bumpiness=bumpiness,
                    )
                )
        return placements

    def observation(self) -> Observation:
        rows = ["".join("#" if cell else "." for cell in row) for row in self._board]
        return Observation(
            state={
                "game": "Tetris",
                "board": rows,
                "board_order": "top row first; # is filled and . is empty",
                "current_piece": self.current,
                "next_piece": self.next_piece,
                "score": self.score,
                "lines": self.lines,
                "pieces_placed": self.pieces,
                "piece_limit": self.piece_limit,
            },
            instructions=(
                "Choose the best hard-drop placement for the current Tetris piece. Prefer line "
                "clears, avoid creating buried holes, keep the stack low, and keep the surface "
                "even. Each option reports the resulting board statistics."
            ),
        )

    def legal_actions(self) -> list[Action]:
        if self.done:
            return []
        return [
            Action(
                placement.action_id,
                (
                    f"Rotation {placement.rotation}, column {placement.column + 1}: "
                    f"clears {placement.lines}, aggregate height {placement.aggregate_height}, "
                    f"holes {placement.holes}, bumpiness {placement.bumpiness}"
                ),
            )
            for placement in self._placements()
        ]

    def step(self, action_id: str, latency_ms: float = 0.0) -> None:
        del latency_ms
        by_id = {placement.action_id: placement for placement in self._placements()}
        if action_id not in by_id:
            raise ValueError(f"illegal Tetris action: {action_id}")
        placement = by_id[action_id]
        level = self.lines // 10
        self.score += (0, 40, 100, 300, 1200)[placement.lines] * (level + 1)
        self.lines += placement.lines
        self.pieces += 1
        self._board = [list(row) for row in placement.board]

        self.current = self.next_piece
        self.next_piece = self._next_piece()
        if self.pieces >= self.piece_limit:
            self._done = True
            self._success = True
            self._terminal_reason = "piece_limit"
        elif not self._placements():
            self._done = True
            self._terminal_reason = "top_out"

    def advance_time(self, latency_ms: float) -> None:
        del latency_ms

    def heuristic_action_id(self) -> str:
        def value(placement: Placement) -> float:
            return (
                0.760666 * placement.lines
                - 0.510066 * placement.aggregate_height
                - 0.35663 * placement.holes
                - 0.184483 * placement.bumpiness
            )

        best = max(
            self._placements(),
            key=lambda placement: (value(placement), placement.action_id),
        )
        return best.action_id

    def result(self) -> dict[str, object]:
        return {
            "score": self.score,
            "score_name": self.score_name,
            "success": self._success,
            "terminal_reason": self._terminal_reason,
            "lines": self.lines,
            "pieces": self.pieces,
            "piece_limit": self.piece_limit,
            "difficulty": self.difficulty,
        }
