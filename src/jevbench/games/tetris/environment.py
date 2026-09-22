from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import pairwise

from ...core import Action, Observation

ROWS = 20
COLS = 10
CONTROL_INTERVAL_SECONDS = {
    "easy": 0.5,
    "medium": 0.25,
    "hard": 0.1,
}

PLAYER_ACTIONS = (
    Action("LEFT", "Move the active piece one column left"),
    Action("RIGHT", "Move the active piece one column right"),
    Action("ROTATE", "Rotate the active piece clockwise"),
    Action("SOFT_DROP", "Move the active piece down one row"),
    Action("HARD_DROP", "Drop and lock the active piece"),
    Action("NONE", "Apply no player input this tick"),
)

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
class Candidate:
    rotation: int
    column: int
    lines: int
    aggregate_height: int
    holes: int
    bumpiness: int


class Tetris:
    id = "tetris"
    score_name = "arcade_score"

    def __init__(
        self,
        seed: int,
        difficulty: str = "medium",
        piece_limit: int | None = None,
        mode: str = "lockstep",
        max_seconds: float | None = None,
    ):
        if difficulty not in CONTROL_INTERVAL_SECONDS:
            raise ValueError(f"unknown Tetris difficulty: {difficulty}")
        if mode not in {"lockstep", "realtime"}:
            raise ValueError(f"unknown Tetris mode: {mode}")
        if piece_limit is not None and piece_limit <= 0:
            raise ValueError("Tetris piece_limit must be greater than zero")
        if max_seconds is not None and max_seconds <= 0:
            raise ValueError("Tetris max_seconds must be greater than zero")

        self.seed = seed
        self.difficulty = difficulty
        self.piece_limit = piece_limit
        self.mode = mode
        self.max_seconds = max_seconds
        self.decision_deadline_seconds = CONTROL_INTERVAL_SECONDS[difficulty]
        self.gravity_interval_seconds = CONTROL_INTERVAL_SECONDS[difficulty]
        self._rng = random.Random(seed)
        self._bag: list[str] = []
        self._board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        self.current = self._next_piece()
        self.next_piece = self._next_piece()
        self.rotation = 0
        self.row = 0
        self.column = self._spawn_column(self.current, self.rotation)
        self.score = 0
        self.lines = 0
        self.pieces = 0
        self.elapsed_seconds = 0.0
        self.late_decisions = 0
        self.missed_ticks = 0
        self.missed_pieces = 0
        self._gravity_age_seconds = 0.0
        self._cycle_remainder = 0.0
        self._stale_response = False
        self._done = False
        self._terminal_reason = "playing"

    @property
    def done(self) -> bool:
        return self._done

    @property
    def active_shape(self) -> tuple[tuple[int, int], ...]:
        return SHAPES[self.current][self.rotation]

    @property
    def active_cells(self) -> list[tuple[int, int]]:
        return [(self.row + dy, self.column + dx) for dy, dx in self.active_shape]

    def _next_piece(self) -> str:
        if not self._bag:
            self._bag = list(SHAPES)
            self._rng.shuffle(self._bag)
        return self._bag.pop()

    @staticmethod
    def _spawn_column(piece: str, rotation: int) -> int:
        width = max(dx for _, dx in SHAPES[piece][rotation]) + 1
        return (COLS - width) // 2

    @staticmethod
    def _fits(
        board: list[list[int]],
        shape: tuple[tuple[int, int], ...],
        row: int,
        column: int,
    ) -> bool:
        return all(
            0 <= row + dy < ROWS and 0 <= column + dx < COLS and board[row + dy][column + dx] == 0
            for dy, dx in shape
        )

    def _try_position(self, row: int, column: int, rotation: int) -> bool:
        shape = SHAPES[self.current][rotation]
        if not self._fits(self._board, shape, row, column):
            return False
        self.row = row
        self.column = column
        self.rotation = rotation
        return True

    def _try_down(self) -> bool:
        return self._try_position(self.row + 1, self.column, self.rotation)

    def _render_board(self) -> list[str]:
        cells = [["#" if value else "." for value in line] for line in self._board]
        if not self.done:
            for row, column in self.active_cells:
                cells[row][column] = "@"
        return ["".join(line) for line in cells]

    def observation(self) -> Observation:
        return Observation(
            state={
                "board": self._render_board(),
                "board_legend": "# locked block, @ active piece, . empty",
                "board_order": "top row first; rows 0-19 and columns 0-9",
                "active_piece": self.current,
                "next_piece": self.next_piece,
                "mode": self.mode,
                "control_interval_ms": round(self.decision_deadline_seconds * 1000),
            },
            instructions=(
                "You are the Tetris player. Choose exactly one control input: LEFT, RIGHT, "
                "ROTATE, SOFT_DROP, HARD_DROP, or NONE. The game engine applies the input, "
                "gravity, collision rules, locking, line clears, scoring, and top-out. A move "
                "or rotation blocked by the board is ignored. No option contains a predicted "
                "placement outcome."
            ),
        )

    def legal_actions(self) -> list[Action]:
        return [] if self.done else list(PLAYER_ACTIONS)

    def step(self, action_id: str) -> None:
        if action_id not in {action.id for action in PLAYER_ACTIONS}:
            raise ValueError(f"illegal Tetris action: {action_id}")

        stale_response = self.mode == "realtime" and self._stale_response
        self._stale_response = False
        pieces_before = self.pieces
        if not stale_response:
            self._apply_player_action(action_id)

        if self.done:
            self._cycle_remainder = 0.0
            return

        if self.mode == "lockstep":
            if self.pieces == pieces_before:
                self._advance_engine(self.gravity_interval_seconds, missed=False)
            else:
                self._advance_clock_without_gravity(self.gravity_interval_seconds)
        elif self._cycle_remainder > 0:
            self._advance_engine(self._cycle_remainder, missed=False)
            self._cycle_remainder = 0.0

    def _apply_player_action(self, action_id: str) -> None:
        if action_id == "LEFT":
            self._try_position(self.row, self.column - 1, self.rotation)
        elif action_id == "RIGHT":
            self._try_position(self.row, self.column + 1, self.rotation)
        elif action_id == "ROTATE":
            next_rotation = (self.rotation + 1) % len(SHAPES[self.current])
            self._try_position(self.row, self.column, next_rotation)
        elif action_id == "SOFT_DROP":
            if not self._try_down():
                self._lock_piece()
        elif action_id == "HARD_DROP":
            while self._try_down():
                pass
            self._lock_piece()

    def _gravity_tick(self) -> bool:
        if self._try_down():
            return False
        self._lock_piece()
        return True

    def _lock_piece(self) -> None:
        for row, column in self.active_cells:
            self._board[row][column] = 1

        kept = [line for line in self._board if not all(line)]
        cleared = ROWS - len(kept)
        self._board = [[0] * COLS for _ in range(cleared)] + kept
        level = self.lines // 10
        self.score += (0, 40, 100, 300, 1200)[cleared] * (level + 1)
        self.lines += cleared
        self.pieces += 1

        if self.piece_limit is not None and self.pieces >= self.piece_limit:
            self._done = True
            self._terminal_reason = "diagnostic_piece_limit"
            return

        self.current = self.next_piece
        self.next_piece = self._next_piece()
        self.rotation = 0
        self.row = 0
        self.column = self._spawn_column(self.current, self.rotation)
        if not self._fits(self._board, self.active_shape, self.row, self.column):
            self._done = True
            self._terminal_reason = "top_out"

    def advance_time(self, latency_ms: float) -> None:
        if self.mode != "realtime" or self.done:
            return

        latency_seconds = max(0.0, latency_ms / 1000)
        if latency_seconds > self.decision_deadline_seconds:
            self.late_decisions += 1
        pieces_before = self.pieces
        self._advance_engine(latency_seconds, missed=True)
        if self.pieces > pieces_before:
            self._stale_response = True

        if self.done:
            self._cycle_remainder = 0.0
            return
        phase = latency_seconds % self.decision_deadline_seconds
        if latency_seconds < 1e-12:
            self._cycle_remainder = self.decision_deadline_seconds
        else:
            self._cycle_remainder = 0.0 if phase < 1e-12 else self.decision_deadline_seconds - phase

    def _advance_engine(self, seconds: float, *, missed: bool) -> None:
        remaining = max(0.0, seconds)
        while remaining > 1e-12 and not self.done:
            until_gravity = self.gravity_interval_seconds - self._gravity_age_seconds
            step = min(remaining, until_gravity)
            if self.max_seconds is not None:
                step = min(step, self.max_seconds - self.elapsed_seconds)
            if step <= 1e-12:
                self._done = True
                self._terminal_reason = "diagnostic_time_limit"
                break

            self.elapsed_seconds += step
            self._gravity_age_seconds += step
            remaining -= step

            if self._gravity_age_seconds >= self.gravity_interval_seconds - 1e-12:
                self._gravity_age_seconds = 0.0
                locked = self._gravity_tick()
                if missed:
                    self.missed_ticks += 1
                    if locked:
                        self.missed_pieces += 1

            if (
                not self.done
                and self.max_seconds is not None
                and self.elapsed_seconds >= self.max_seconds - 1e-12
            ):
                self._done = True
                self._terminal_reason = "diagnostic_time_limit"

    def _advance_clock_without_gravity(self, seconds: float) -> None:
        duration = seconds
        if self.max_seconds is not None:
            duration = min(duration, self.max_seconds - self.elapsed_seconds)
        self.elapsed_seconds += max(0.0, duration)
        if self.max_seconds is not None and self.elapsed_seconds >= self.max_seconds - 1e-12:
            self._done = True
            self._terminal_reason = "diagnostic_time_limit"

    @staticmethod
    def _stats(board: list[list[int]]) -> tuple[int, int, int]:
        heights = []
        holes = 0
        for column in range(COLS):
            top = next((row for row in range(ROWS) if board[row][column]), ROWS)
            height = ROWS - top
            heights.append(height)
            if height:
                holes += sum(board[row][column] == 0 for row in range(top, ROWS))
        bumpiness = sum(abs(left - right) for left, right in pairwise(heights))
        return sum(heights), holes, bumpiness

    def _candidate_placements(self) -> list[Candidate]:
        candidates = []
        for rotation, shape in enumerate(SHAPES[self.current]):
            width = max(dx for _, dx in shape) + 1
            for column in range(COLS - width + 1):
                if not self._fits(self._board, shape, self.row, column):
                    continue
                row = self.row
                while self._fits(self._board, shape, row + 1, column):
                    row += 1
                board = [line[:] for line in self._board]
                for dy, dx in shape:
                    board[row + dy][column + dx] = 1
                kept = [line for line in board if not all(line)]
                cleared = ROWS - len(kept)
                board = [[0] * COLS for _ in range(cleared)] + kept
                aggregate_height, holes, bumpiness = self._stats(board)
                candidates.append(
                    Candidate(
                        rotation=rotation,
                        column=column,
                        lines=cleared,
                        aggregate_height=aggregate_height,
                        holes=holes,
                        bumpiness=bumpiness,
                    )
                )
        return candidates

    def heuristic_action_id(self) -> str:
        def value(candidate: Candidate) -> tuple[float, int, int]:
            score = (
                0.760666 * candidate.lines
                - 0.510066 * candidate.aggregate_height
                - 0.35663 * candidate.holes
                - 0.184483 * candidate.bumpiness
            )
            return score, -candidate.rotation, -candidate.column

        candidates = self._candidate_placements()
        if not candidates:
            return "NONE"
        target = max(candidates, key=value)
        if self.rotation != target.rotation:
            return "ROTATE"
        if self.column > target.column:
            return "LEFT"
        if self.column < target.column:
            return "RIGHT"
        return "HARD_DROP"

    def result(self) -> dict[str, object]:
        return {
            "score": self.score,
            "score_name": self.score_name,
            "success": False,
            "terminal_reason": self._terminal_reason,
            "lines": self.lines,
            "pieces": self.pieces,
            "piece_limit": self.piece_limit,
            "difficulty": self.difficulty,
            "mode": self.mode,
            "simulated_seconds": round(self.elapsed_seconds, 3),
            "max_seconds": self.max_seconds,
            "decision_deadline_ms": round(self.decision_deadline_seconds * 1000),
            "late_decisions": self.late_decisions,
            "missed_ticks": self.missed_ticks,
            "missed_pieces": self.missed_pieces,
        }
