from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime
from pathlib import Path

from huggingface_hub import run_job, sync_bucket, sync_job_volume, wait_for_job

HOSTED_MODEL_SECRETS = {
    "jev": "TYPESAFE_API_KEY",
    "openjev": "CODIV_API_KEY",
}
KNOWN_MODELS = {
    "random",
    "heuristic",
    "jev",
    "openjev",
    "kev",
    "laya",
    "laya-typed",
    "laya-multilingual",
}
KNOWN_GAMES = {"minesweeper", "tetris", "pong", "snake"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Launch the NARCADE suite as a single-GPU Hugging Face Job"
    )
    parser.add_argument("space_id", help="Docker Space image source, for example org/narcade")
    parser.add_argument("--image", help="Override the default hf.co/spaces/<space_id> image")
    parser.add_argument("--namespace", help="Hugging Face user or organization that owns the Job")
    parser.add_argument("--flavor", default="a100-large", help="Jobs hardware flavor")
    parser.add_argument(
        "--models",
        default="random,heuristic,jev,openjev,kev",
        help="Comma-separated benchmark lanes",
    )
    parser.add_argument("--games", default="minesweeper,tetris,pong,snake")
    parser.add_argument("--episodes", type=int, default=3)
    parser.add_argument("--seed", type=int, default=100)
    parser.add_argument("--difficulty", choices=("easy", "medium", "hard"), default="medium")
    parser.add_argument("--mode", choices=("auto", "lockstep", "realtime"), default="auto")
    parser.add_argument("--max-seconds", type=float)
    parser.add_argument("--max-pieces", type=int, default=200)
    parser.add_argument("--max-decisions", type=int, default=2_000)
    parser.add_argument("--timeout", default="6h", help="Hugging Face Job timeout")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--detach", action="store_true", help="Return after scheduling the Job")
    return parser


def _selected_models(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _validate(args: argparse.Namespace, models: list[str]) -> None:
    games = _selected_models(args.games)
    unknown_models = sorted(set(models) - KNOWN_MODELS)
    unknown_games = sorted(set(games) - KNOWN_GAMES)
    if unknown_models:
        raise ValueError(f"unknown models: {', '.join(unknown_models)}")
    if not games:
        raise ValueError("--games must contain at least one game")
    if unknown_games:
        raise ValueError(f"unknown games: {', '.join(unknown_games)}")
    if args.episodes <= 0:
        raise ValueError("--episodes must be greater than zero")
    if args.max_seconds is not None and args.max_seconds <= 0:
        raise ValueError("--max-seconds must be greater than zero")
    if args.max_pieces is not None and args.max_pieces <= 0:
        raise ValueError("--max-pieces must be greater than zero")
    if args.max_decisions is not None and args.max_decisions <= 0:
        raise ValueError("--max-decisions must be greater than zero")
    if args.mode == "realtime" and "minesweeper" in games:
        raise ValueError("Minesweeper does not support realtime mode")


def _job_secrets(models: list[str]) -> dict[str, str]:
    required = {secret for model, secret in HOSTED_MODEL_SECRETS.items() if model in models}
    missing = sorted(secret for secret in required if not os.environ.get(secret))
    if missing:
        raise ValueError(f"missing local environment variables: {', '.join(missing)}")
    return {secret: os.environ[secret] for secret in sorted(required)}


def _job_command(args: argparse.Namespace) -> list[str]:
    command = [
        "python",
        "/app/job_runner.py",
        "--models",
        args.models,
        "--games",
        args.games,
        "--episodes",
        str(args.episodes),
        "--seed",
        str(args.seed),
        "--difficulty",
        args.difficulty,
        "--mode",
        args.mode,
        "--output-dir",
        "/outputs",
    ]
    if args.max_seconds is not None:
        command.extend(["--max-seconds", str(args.max_seconds)])
    if args.max_pieces is not None:
        command.extend(["--max-pieces", str(args.max_pieces)])
    if args.max_decisions is not None:
        command.extend(["--max-decisions", str(args.max_decisions)])
    return command


def main(argv: list[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    models = _selected_models(args.models)
    if not models:
        raise SystemExit("error: --models must contain at least one model")
    try:
        _validate(args, models)
        secrets = _job_secrets(models)
    except ValueError as error:
        raise SystemExit(f"error: {error}") from error

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_dir = (args.output_dir or Path("results") / "hf" / timestamp).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    volume = sync_job_volume(
        output_dir,
        "/outputs",
        remote_name=f"narcade-{timestamp}",
        read_only=False,
        namespace=args.namespace,
    )
    image = args.image or f"hf.co/spaces/{args.space_id}"
    job = run_job(
        image=image,
        command=_job_command(args),
        env={"NARCADE_JOB_IMAGE": image},
        secrets=secrets,
        flavor=args.flavor,
        timeout=args.timeout,
        name=f"narcade-{timestamp}",
        labels={"benchmark": "narcade", "hardware": args.flavor},
        volumes=[volume],
        namespace=args.namespace,
    )
    print(f"Job: {job.url}")
    print(f"Hardware: {args.flavor}")
    print(f"Output bucket: hf://buckets/{volume.source}/{volume.path or ''}")
    if args.detach:
        return

    finished = wait_for_job(job.id, namespace=args.namespace)
    source = f"hf://buckets/{volume.source}"
    if volume.path:
        source += f"/{volume.path}"
    sync_bucket(source, str(output_dir))
    print(f"Results: {output_dir}")
    if finished.status.stage != "COMPLETED":
        raise SystemExit(f"Job ended with status {finished.status.stage}: {job.url}")


if __name__ == "__main__":
    main()
