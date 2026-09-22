from __future__ import annotations

import math
import random
from collections import deque
from enum import StrEnum

from ...core import Action, Observation

Cell = tuple[int, int]

TICK_SECONDS = {
    "easy": 1.5,
    "medium": 1.0,
    "hard": 0.5,
}


class Direction(StrEnum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"

    @property
    def vector(self) -> Cell:
        return {
            Direction.UP: (0, -1),
            Direction.DOWN: (0, 1),
            Direction.LEFT: (-1, 0),
            Direction.RIGHT: (1, 0),
        }[self]

    @property
    def opposite(self) -> Direction:
        return {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT,
        }[self]


class Snake:
    """Seeded, headless Snake adapted from iammusham/jev-snake."""

    id = "snake"
    score_name = "food_eaten"
    width = 20
    height = 20

    def __init__(
        self,
        seed: int,
        difficulty: str = "medium",
        mode: str = "lockstep",
    ):
        if difficulty not in TICK_SECONDS:
            raise ValueError(f"unknown Snake difficulty: {difficulty}")
        if mode not in {"lockstep", "realtime"}:
            raise ValueError(f"unknown Snake mode: {mode}")
        self.seed = seed
        self.difficulty = difficulty
        self.mode = mode
        self.tick_seconds = TICK_SECONDS[difficulty]
        self._rng = random.Random(seed)
        center_x, center_y = self.width // 2, self.height // 2
        self.snake: list[Cell] = [
            (center_x, center_y),
            (center_x - 1, center_y),
            (center_x - 2, center_y),
        ]
        self.direction = Direction.RIGHT
        self.score = 0
        self.ticks = 0
        self.elapsed_seconds = 0.0
        self.late_decisions = 0
        self.missed_ticks = 0
        self._cycle_remainder = 0.0
        self._done = False
        self._won = False
        self._terminal_reason = "playing"
        self.food = self._spawn_food()

    @property
    def done(self) -> bool:
        return self._done

    @property
    def head(self) -> Cell:
        return self.snake[0]

    def _all_cells(self) -> list[Cell]:
        return [(x, y) for y in range(self.height) for x in range(self.width)]

    def _spawn_food(self) -> Cell | None:
        occupied = set(self.snake)
        available = [cell for cell in self._all_cells() if cell not in occupied]
        return self._rng.choice(available) if available else None

    def _inside(self, cell: Cell) -> bool:
        x, y = cell
        return 0 <= x < self.width and 0 <= y < self.height

    def _next_cell(self, direction: Direction) -> Cell:
        dx, dy = direction.vector
        x, y = self.head
        return x + dx, y + dy

    def _collision_reason(self, cell: Cell, *, growing: bool = False) -> str | None:
        if not self._inside(cell):
            return "wall"
        body = self.snake if growing else self.snake[:-1]
        if cell in body:
            return "self"
        return None

    def _non_reversing_directions(self) -> list[Direction]:
        return [direction for direction in Direction if direction != self.direction.opposite]

    def observation(self) -> Observation:
        return Observation(
            state={
                "grid_size": [self.width, self.height],
                "snake": [list(cell) for cell in self.snake],
                "direction": self.direction.value,
                "food": list(self.food) if self.food is not None else None,
                "tick_interval_ms": round(self.tick_seconds * 1000),
            },
            instructions=(
                "Play Snake. Coordinates are [x,y], origin top-left, y increases down. "
                "The snake is ordered head to tail. Choose UP, DOWN, LEFT, or RIGHT. "
                "Eat food to grow; walls and body collisions end the game. "
                "Reversals are ignored. In realtime, movement continues while you decide."
            ),
        )

    def legal_actions(self) -> list[Action]:
        if self.done:
            return []
        return [
            Action(direction.value, f"Move {direction.value.lower()}") for direction in Direction
        ]

    def step(self, action_id: str) -> None:
        try:
            requested_direction = Direction(action_id)
        except ValueError as error:
            raise ValueError(f"illegal Snake action: {action_id}") from error
        if requested_direction != self.direction.opposite:
            self.direction = requested_direction
        if self.mode == "lockstep":
            self._advance_tick()
        else:
            self.elapsed_seconds += self._cycle_remainder
            self._advance_tick()
            self._cycle_remainder = 0.0

    def _advance_tick(self) -> None:
        direction = self.direction
        next_head = self._next_cell(direction)
        ate_food = next_head == self.food
        reason = self._collision_reason(next_head, growing=ate_food)
        self.ticks += 1

        if reason:
            self._done = True
            self._terminal_reason = reason
            return

        self.snake.insert(0, next_head)
        if ate_food:
            self.score += 1
            self.food = self._spawn_food()
            if self.food is None:
                self._done = True
                self._won = True
                self._terminal_reason = "board_filled"
        else:
            self.snake.pop()

    def advance_time(self, latency_ms: float) -> None:
        if self.mode != "realtime" or self.done:
            return

        latency_seconds = max(0.0, latency_ms / 1000)
        duration = latency_seconds
        ticks = max(0, math.floor((duration - 1e-12) / self.tick_seconds))
        if latency_ms / 1000 > self.tick_seconds:
            self.late_decisions += 1
        for _ in range(ticks):
            self.elapsed_seconds += self.tick_seconds
            self.missed_ticks += 1
            self._advance_tick()
            if self.done:
                self._cycle_remainder = 0.0
                return

        residual = max(0.0, duration - (ticks * self.tick_seconds))
        self.elapsed_seconds += residual
        if self.done:
            self._cycle_remainder = 0.0
        else:
            if duration < 1e-12:
                self._cycle_remainder = self.tick_seconds
            elif abs(residual - self.tick_seconds) < 1e-12:
                self._cycle_remainder = 0.0
            else:
                self._cycle_remainder = self.tick_seconds - residual

    def heuristic_action_id(self) -> str:
        def value(direction: Direction) -> tuple[int, int, int, str]:
            next_head = self._next_cell(direction)
            growing = next_head == self.food
            if self._collision_reason(next_head, growing=growing):
                return (-1, -self.width * self.height, 0, direction.value)

            body = self.snake if growing else self.snake[:-1]
            blocked = set(body)
            blocked.discard(next_head)
            distances = {next_head: 0}
            queue = deque([next_head])
            while queue:
                cell = queue.popleft()
                for candidate_direction in Direction:
                    dx, dy = candidate_direction.vector
                    candidate = (cell[0] + dx, cell[1] + dy)
                    if (
                        self._inside(candidate)
                        and candidate not in blocked
                        and candidate not in distances
                    ):
                        distances[candidate] = distances[cell] + 1
                        queue.append(candidate)
            food_distance = distances.get(self.food) if self.food is not None else 0
            reaches_food = int(food_distance is not None)
            distance_value = (
                -food_distance if food_distance is not None else -self.width * self.height
            )
            return (reaches_food, distance_value, len(distances), direction.value)

        return max(self._non_reversing_directions(), key=value).value

    def result(self) -> dict[str, object]:
        return {
            "score": self.score,
            "score_name": self.score_name,
            "success": self._won,
            "terminal_reason": self._terminal_reason,
            "ticks": self.ticks,
            "snake_length": len(self.snake),
            "difficulty": self.difficulty,
            "mode": self.mode,
            "simulated_seconds": round(self.elapsed_seconds, 3),
            "tick_interval_ms": round(self.tick_seconds * 1000),
            "late_decisions": self.late_decisions,
            "missed_ticks": self.missed_ticks,
        }
