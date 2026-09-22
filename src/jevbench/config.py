from __future__ import annotations

import argparse
import math
import os
from dataclasses import dataclass, field
from pathlib import Path

from .models import DEFAULT_MODELS
from .registry import GAME_DESCRIPTIONS

BASELINES = ("random", "heuristic")


@dataclass
class RunConfig:
    models: list[str] = field(default_factory=lambda: [*BASELINES, "jev", "openjev", "kev"])
    games: list[str] = field(default_factory=lambda: list(GAME_DESCRIPTIONS))
    episodes: int = 3
    seed: int = 100
    difficulty: str = "medium"
    mode: str = "auto"
    max_seconds: float | None = None
    max_pieces: int | None = None
    max_decisions: int | None = 2000
    request_timeout: float = 30
    trace: bool = False

    def validate(self) -> None:
        for name, choices in (
            ("models", (*BASELINES, *DEFAULT_MODELS)),
            ("games", GAME_DESCRIPTIONS),
        ):
            values = getattr(self, name)
            if not values or len(set(values)) != len(values) or set(values) - set(choices):
                raise ValueError(f"{name} must be unique choices from {', '.join(choices)}")
        for name in ("episodes", "max_seconds", "max_pieces", "max_decisions", "request_timeout"):
            value = getattr(self, name)
            if value is not None and (not math.isfinite(value) or value <= 0):
                raise ValueError(f"{name} must be positive and finite")
        if self.mode not in ("auto", "lockstep", "realtime"):
            raise ValueError("mode must be auto, lockstep, or realtime")
        if self.difficulty not in ("easy", "medium", "hard"):
            raise ValueError("difficulty must be easy, medium, or hard")

    def secrets(self) -> dict[str, str]:
        required = {
            DEFAULT_MODELS[name].api_key_env for name in self.models if name in DEFAULT_MODELS
        }
        required.discard(None)
        missing = sorted(key for key in required if not os.environ.get(key))
        if missing:
            raise ValueError(f"missing environment variables: {', '.join(missing)}")
        return {key: os.environ[key] for key in sorted(required)}

    def game_options(self, game: str) -> dict:
        mode = (
            "lockstep"
            if game == "minesweeper"
            else ("realtime" if self.mode == "auto" else self.mode)
        )
        return dict(
            difficulty=self.difficulty,
            mode=mode,
            piece_limit=self.max_pieces if game == "tetris" else None,
            max_seconds=self.max_seconds if game == "tetris" else None,
        )


def add_run_options(parser: argparse.ArgumentParser) -> None:
    defaults = RunConfig()
    for name in ("models", "games"):
        parser.add_argument(
            f"--{name}", type=lambda s: s.split(","), default=getattr(defaults, name)
        )
    for name, kind in (
        ("episodes", int),
        ("seed", int),
        ("max_seconds", float),
        ("max_pieces", int),
        ("max_decisions", int),
        ("request_timeout", float),
    ):
        parser.add_argument(
            f"--{name.replace('_', '-')}", type=kind, default=getattr(defaults, name)
        )
    parser.add_argument(
        "--difficulty", choices=("easy", "medium", "hard"), default=defaults.difficulty
    )
    parser.add_argument("--mode", choices=("auto", "lockstep", "realtime"), default=defaults.mode)
    parser.add_argument("--trace", action="store_true", help="Write separate decision JSONL files")
    parser.add_argument("--output-dir", type=Path, required=True)


def config_from_args(args: argparse.Namespace) -> RunConfig:
    config = RunConfig(**{name: getattr(args, name) for name in RunConfig.__dataclass_fields__})
    config.validate()
    return config
