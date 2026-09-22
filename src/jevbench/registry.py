from __future__ import annotations

from .core import Game
from .games.minesweeper import Minesweeper
from .games.pong import Pong
from .games.snake import Snake
from .games.tetris import Tetris

# Bump when rules, scoring, timing semantics, or heuristic behavior change.
RULES_VERSION = "0.4.0"

GAME_DESCRIPTIONS = {
    "minesweeper": "Seeded 9x9 Minesweeper; score is safe squares revealed.",
    "tetris": "Seeded control-loop Tetris; score uses the classic line-clear table.",
    "pong": "Pong against a seeded tracking bot; score is points won.",
    "snake": "Seeded 20x20 Snake; score is food eaten.",
}


def create_game(
    game_id: str,
    *,
    seed: int,
    difficulty: str,
    mode: str,
    piece_limit: int | None,
    max_seconds: float | None,
) -> Game:
    if game_id == "minesweeper":
        return Minesweeper(seed=seed, difficulty=difficulty)
    if game_id == "tetris":
        return Tetris(
            seed=seed,
            difficulty=difficulty,
            piece_limit=piece_limit,
            mode=mode,
            max_seconds=max_seconds,
        )
    if game_id == "pong":
        assert max_seconds is not None
        return Pong(seed=seed, difficulty=difficulty, mode=mode, max_seconds=max_seconds)
    if game_id == "snake":
        return Snake(seed=seed, difficulty=difficulty, mode=mode)
    raise ValueError(f"unknown game: {game_id}")
