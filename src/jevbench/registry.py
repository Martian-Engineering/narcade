from __future__ import annotations

from .core import Game
from .games.minesweeper import Minesweeper
from .games.pong import Pong
from .games.tetris import Tetris

GAME_DESCRIPTIONS = {
    "minesweeper": "Seeded 9x9 Minesweeper; score is safe squares revealed.",
    "tetris": "Seeded hard-drop Tetris; score uses the classic line-clear table.",
    "pong": "Pong against a seeded tracking bot; score is points won.",
}


def create_game(
    game_id: str,
    *,
    seed: int,
    difficulty: str,
    mode: str,
    max_decisions: int,
) -> Game:
    if game_id == "minesweeper":
        return Minesweeper(seed=seed, difficulty=difficulty)
    if game_id == "tetris":
        return Tetris(seed=seed, difficulty=difficulty, piece_limit=max_decisions)
    if game_id == "pong":
        return Pong(seed=seed, difficulty=difficulty, mode=mode)
    raise ValueError(f"unknown game: {game_id}")
