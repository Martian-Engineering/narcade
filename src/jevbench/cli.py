from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .laya_policy import LayaPolicy, cache_laya_checkpoint
from .models import DEFAULT_MODELS, SystemOneModel, load_models
from .policies import HeuristicPolicy, RandomPolicy
from .registry import GAME_DESCRIPTIONS, create_game
from .runner import run_benchmark
from .systemone import SystemOnePolicy

BASELINE_POLICIES = {"random", "heuristic"}
DEFAULT_COMPARISON = "jev,openjev,kev"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jev-bench",
        description="Run reproducible structured-state game benchmarks.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List games, scores, and built-in model lanes")

    cache = subparsers.add_parser("cache", help="Download pinned local-model checkpoints")
    cache.add_argument(
        "--models",
        default="laya,laya-typed,laya-multilingual",
        help="Comma-separated local-runtime model names",
    )
    cache.add_argument("--models-file", type=Path)
    cache.add_argument("--cache-dir", type=Path)

    run = subparsers.add_parser("run", help="Run one game with one model or baseline")
    run.add_argument("game", choices=sorted(GAME_DESCRIPTIONS))
    run.add_argument(
        "--policy",
        default="jev",
        help="Model name from the model config, or random/heuristic (default: jev)",
    )
    _add_run_options(run)

    compare = subparsers.add_parser(
        "compare",
        help="Run several models on an identical game seed pack",
    )
    compare.add_argument("game", choices=sorted(GAME_DESCRIPTIONS))
    compare.add_argument(
        "--models",
        default=DEFAULT_COMPARISON,
        help=f"Comma-separated model or baseline names (default: {DEFAULT_COMPARISON})",
    )
    _add_run_options(compare)
    return parser


def _add_run_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--episodes", type=_positive_int, default=1)
    parser.add_argument("--seed", type=int, default=0, help="First episode seed")
    parser.add_argument("--difficulty", choices=("easy", "medium", "hard"), default="medium")
    parser.add_argument(
        "--mode",
        choices=("lockstep", "realtime"),
        help="Timing mode; defaults to realtime for Tetris/Pong/Snake and lockstep otherwise",
    )
    parser.add_argument(
        "--max-seconds",
        type=_positive_float,
        help="Explicit diagnostic time cap for Tetris, or match limit for Pong (default: 120)",
    )
    parser.add_argument(
        "--max-decisions",
        type=_positive_int,
        help="Safety cap on model calls per episode; game-specific default",
    )
    parser.add_argument(
        "--max-pieces",
        type=_positive_int,
        help="Explicit diagnostic Tetris piece cap; normal runs continue to top-out",
    )
    parser.add_argument(
        "--timeout",
        type=_positive_float,
        default=30.0,
        help="System One request timeout in seconds",
    )
    parser.add_argument(
        "--models-file",
        type=Path,
        help="TOML overrides for built-in models or additional System One models",
    )
    parser.add_argument("--record-decisions", action="store_true")
    parser.add_argument("--output", type=Path, help="Write the JSON result to this path")


def main(argv: list[str] | None = None) -> None:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "list":
        print("Games:")
        for game_id, description in GAME_DESCRIPTIONS.items():
            print(f"  {game_id:12} {description}")
        print("Models:")
        for name, model in DEFAULT_MODELS.items():
            location = "local runtime" if model.runtime == "laya" else model.endpoint
            print(f"  {name:12} {model.model} at {location}")
        print("Baselines:")
        print("  random       seeded random legal action")
        print("  heuristic    deterministic game-specific policy")
        return

    if args.command == "cache":
        try:
            models = load_models(args.models_file)
            names = _model_names(args.models)
            snapshots = {}
            for name in names:
                if name not in models or models[name].runtime != "laya":
                    raise ValueError(f"{name!r} is not a configured local Laya model")
                snapshots[name] = cache_laya_checkpoint(models[name], args.cache_dir)
        except (OSError, ValueError, RuntimeError) as error:
            print(f"error: {error}", file=sys.stderr)
            raise SystemExit(2) from error
        print(json.dumps({"cached": snapshots}, indent=2, sort_keys=True))
        return

    mode = _resolved_mode(args.game, args.mode)
    if args.game == "minesweeper" and mode != "lockstep":
        parser.error("Minesweeper supports only --mode lockstep")
    if args.game != "tetris" and args.max_pieces is not None:
        parser.error("--max-pieces applies only to Tetris")
    args.mode = mode
    if args.game in {"minesweeper", "snake"}:
        if args.max_seconds is not None:
            parser.error(f"--max-seconds does not apply to {args.game}")
    elif args.game == "pong":
        args.max_seconds = args.max_seconds or 120.0

    try:
        models = load_models(args.models_file)
        if args.command == "run":
            result = _run_one(args, args.policy, models)
        else:
            names = _model_names(args.models)
            _validate_policies(names, models, args.timeout)
            results = {name: _run_one(args, name, models) for name in names}
            result = {
                "benchmark_version": "0.4.0",
                "game": args.game,
                "mode": args.mode,
                "max_seconds": args.max_seconds,
                "max_pieces": args.max_pieces,
                "models": names,
                "first_seed": args.seed,
                "episode_count": args.episodes,
                "results": results,
            }
    except (OSError, ValueError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from error

    rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


def _run_one(
    args: argparse.Namespace,
    policy_name: str,
    models: dict[str, SystemOneModel],
) -> dict[str, Any]:
    max_decisions = args.max_decisions
    if max_decisions is None:
        max_decisions = {
            "minesweeper": 81,
            "tetris": None,
            "pong": 2_000 if args.mode == "realtime" else 500,
            "snake": None,
        }[args.game]
    piece_limit = args.max_pieces

    def game_factory(seed: int):
        return create_game(
            args.game,
            seed=seed,
            difficulty=args.difficulty,
            mode=args.mode,
            piece_limit=piece_limit,
            max_seconds=args.max_seconds,
        )

    shared_model_policy = None
    if policy_name in models:
        config = models[policy_name]
        shared_model_policy = (
            LayaPolicy(config)
            if config.runtime == "laya"
            else SystemOnePolicy(config, timeout_seconds=args.timeout)
        )

    def policy_factory(seed: int):
        if policy_name == "random":
            return RandomPolicy(seed ^ 0x5EED)
        if policy_name == "heuristic":
            return HeuristicPolicy()
        if policy_name not in models:
            available = ", ".join(sorted(BASELINE_POLICIES | set(models)))
            raise ValueError(f"unknown policy {policy_name!r}; choose from: {available}")
        assert shared_model_policy is not None
        return shared_model_policy

    return run_benchmark(
        game_factory,
        policy_factory,
        game_id=args.game,
        policy_name=policy_name,
        first_seed=args.seed,
        episodes=args.episodes,
        max_decisions=max_decisions,
        record_decisions=args.record_decisions,
    )


def _model_names(value: str) -> list[str]:
    names = [name.strip() for name in value.split(",") if name.strip()]
    if not names:
        raise ValueError("--models must contain at least one model name")
    if len(names) != len(set(names)):
        raise ValueError("--models cannot contain duplicate names")
    return names


def _resolved_mode(game: str, requested: str | None) -> str:
    if requested:
        return requested
    return "lockstep" if game == "minesweeper" else "realtime"


def _validate_policies(
    names: list[str],
    models: dict[str, SystemOneModel],
    timeout_seconds: float,
) -> None:
    available = ", ".join(sorted(BASELINE_POLICIES | set(models)))
    for name in names:
        if name in BASELINE_POLICIES:
            continue
        if name not in models:
            raise ValueError(f"unknown policy {name!r}; choose from: {available}")
        if models[name].runtime == "laya":
            LayaPolicy.validate_runtime()
        else:
            SystemOnePolicy(models[name], timeout_seconds=timeout_seconds)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed
