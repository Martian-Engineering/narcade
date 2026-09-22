from __future__ import annotations

import random
from collections import deque

from ...core import Action, Observation

DIFFICULTY_MINES = {"easy": 6, "medium": 8, "hard": 10}


class Minesweeper:
    id = "minesweeper"
    score_name = "safe_squares_revealed"
    rows = 9
    cols = 9

    def __init__(self, seed: int, difficulty: str = "hard"):
        if difficulty not in DIFFICULTY_MINES:
            raise ValueError(f"unknown Minesweeper difficulty: {difficulty}")
        self.seed = seed
        self.difficulty = difficulty
        self.mine_count = DIFFICULTY_MINES[difficulty]
        self._mines = self._place_mines(seed)
        self._revealed: set[tuple[int, int]] = set()
        self._lost = False
        self._terminal_reason = "playing"
        self._moves = 0
        self._reveal((self.rows // 2, self.cols // 2))

    @property
    def done(self) -> bool:
        return self._lost or self.safe_revealed == self.max_safe

    @property
    def max_safe(self) -> int:
        return self.rows * self.cols - self.mine_count

    @property
    def safe_revealed(self) -> int:
        return len(self._revealed - self._mines)

    def _place_mines(self, seed: int) -> set[tuple[int, int]]:
        center_r, center_c = self.rows // 2, self.cols // 2
        candidates = [
            (row, col)
            for row in range(self.rows)
            for col in range(self.cols)
            if abs(row - center_r) > 1 or abs(col - center_c) > 1
        ]
        return set(random.Random(seed).sample(candidates, self.mine_count))

    def _neighbors(self, cell: tuple[int, int]) -> list[tuple[int, int]]:
        row, col = cell
        return [
            (next_row, next_col)
            for next_row in range(max(0, row - 1), min(self.rows, row + 2))
            for next_col in range(max(0, col - 1), min(self.cols, col + 2))
            if (next_row, next_col) != cell
        ]

    def _clue(self, cell: tuple[int, int]) -> int:
        return sum(neighbor in self._mines for neighbor in self._neighbors(cell))

    def _reveal(self, cell: tuple[int, int]) -> None:
        if cell in self._mines:
            self._revealed.add(cell)
            self._lost = True
            self._terminal_reason = "mine"
            return

        queue = deque([cell])
        while queue:
            current = queue.popleft()
            if current in self._revealed or current in self._mines:
                continue
            self._revealed.add(current)
            if self._clue(current) == 0:
                queue.extend(self._neighbors(current))

        if self.safe_revealed == self.max_safe:
            self._terminal_reason = "cleared"

    @staticmethod
    def _label(cell: tuple[int, int]) -> str:
        row, col = cell
        return f"{chr(65 + col)}{row + 1}"

    def _visible_value(self, cell: tuple[int, int]) -> str:
        if cell not in self._revealed:
            return "#"
        if cell in self._mines:
            return "*"
        return str(self._clue(cell))

    def _board_text(self) -> str:
        lines = ["    " + " ".join(chr(65 + col) for col in range(self.cols))]
        for row in range(self.rows):
            values = [self._visible_value((row, col)) for col in range(self.cols)]
            lines.append(f"{row + 1:>2}  " + " ".join(values))
        return "\n".join(lines)

    def observation(self) -> Observation:
        return Observation(
            state={
                "game": "Minesweeper",
                "difficulty": self.difficulty,
                "board": self._board_text(),
                "mines": self.mine_count,
                "safe_squares_revealed": self.safe_revealed,
                "safe_squares_total": self.max_safe,
                "notation": "# is covered. Columns are A-I and rows are 1-9.",
            },
            instructions=(
                "Choose one covered square to reveal. A number gives the exact number of mines "
                "in its eight neighboring squares. Revealing a mine ends the game. Reveal every "
                "safe square. Use the visible constraints and choose the safest useful square."
            ),
        )

    def legal_actions(self) -> list[Action]:
        if self.done:
            return []
        actions = []
        for row in range(self.rows):
            for col in range(self.cols):
                cell = (row, col)
                if cell not in self._revealed:
                    actions.append(Action(self._label(cell), f"Reveal square {self._label(cell)}"))
        return actions

    def step(self, action_id: str, latency_ms: float = 0.0) -> None:
        del latency_ms
        legal = {action.id for action in self.legal_actions()}
        if action_id not in legal:
            raise ValueError(f"illegal Minesweeper action: {action_id}")
        col = ord(action_id[0]) - 65
        row = int(action_id[1:]) - 1
        self._moves += 1
        self._reveal((row, col))

    def advance_time(self, latency_ms: float) -> None:
        del latency_ms

    def heuristic_action_id(self) -> str:
        risks: list[tuple[float, str]] = []
        for action in self.legal_actions():
            col = ord(action.id[0]) - 65
            row = int(action.id[1:]) - 1
            estimates = []
            for neighbor in self._neighbors((row, col)):
                if neighbor not in self._revealed or neighbor in self._mines:
                    continue
                covered = [cell for cell in self._neighbors(neighbor) if cell not in self._revealed]
                if covered:
                    estimates.append(self._clue(neighbor) / len(covered))
            risk = max(estimates) if estimates else self.mine_count / (self.rows * self.cols)
            risks.append((risk, action.id))
        return min(risks)[1]

    def result(self) -> dict[str, object]:
        won = self.done and not self._lost
        return {
            "score": self.safe_revealed,
            "score_name": self.score_name,
            "score_max": self.max_safe,
            "success": won,
            "terminal_reason": self._terminal_reason,
            "moves": self._moves,
            "mines": self.mine_count,
            "difficulty": self.difficulty,
        }
