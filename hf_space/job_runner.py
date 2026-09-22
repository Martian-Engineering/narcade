from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

GAMES = ("minesweeper", "tetris", "pong", "snake")
MODELS = (
    "random",
    "heuristic",
    "jev",
    "openjev",
    "kev",
    "laya",
    "laya-typed",
    "laya-multilingual",
)
DEFAULT_MODELS = ("random", "heuristic", "jev", "openjev", "kev")
KEV_CHECKPOINT = "jaredpalmer/kev-4b@485ace8703592fcf405488b262449990824cfed1"
KEV_PORT = 8009


def _csv(value: str, *, choices: tuple[str, ...], field: str) -> list[str]:
    values = [item.strip() for item in value.split(",") if item.strip()]
    unknown = sorted(set(values) - set(choices))
    if not values:
        raise ValueError(f"{field} must contain at least one value")
    if unknown:
        raise ValueError(f"unknown {field}: {', '.join(unknown)}")
    if len(values) != len(set(values)):
        raise ValueError(f"{field} cannot contain duplicates")
    return values


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the complete NARCADE suite sequentially on one Hugging Face Job"
    )
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    parser.add_argument("--games", default=",".join(GAMES))
    parser.add_argument("--episodes", type=int, default=3)
    parser.add_argument("--seed", type=int, default=100)
    parser.add_argument("--difficulty", choices=("easy", "medium", "hard"), default="medium")
    parser.add_argument("--mode", choices=("auto", "lockstep", "realtime"), default="auto")
    parser.add_argument("--max-seconds", type=float)
    parser.add_argument("--max-pieces", type=int, default=200)
    parser.add_argument("--max-decisions", type=int, default=2_000)
    parser.add_argument("--output-dir", type=Path, default=Path("/outputs"))
    return parser


def _gpu_name() -> str | None:
    try:
        import torch

        if torch.cuda.is_available():
            return torch.cuda.get_device_name(0)
    except (ImportError, RuntimeError):
        pass
    return None


def _required_secrets(models: list[str]) -> list[str]:
    required = []
    if "jev" in models:
        required.append("TYPESAFE_API_KEY")
    if "openjev" in models:
        required.append("CODIV_API_KEY")
    return required


def _validate(args: argparse.Namespace, models: list[str], games: list[str]) -> None:
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
    missing = [name for name in _required_secrets(models) if not os.environ.get(name)]
    if missing:
        raise ValueError(f"missing job secrets: {', '.join(missing)}")


def _wait_for_kev(process: subprocess.Popen[str], timeout: float = 900.0) -> None:
    deadline = time.monotonic() + timeout
    url = f"http://127.0.0.1:{KEV_PORT}/v1/models"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Kev server exited with status {process.returncode}")
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (TimeoutError, urllib.error.URLError):
            time.sleep(2)
    raise RuntimeError("Kev server did not become ready within 15 minutes")


@contextmanager
def _kev_server(output_dir: Path, enabled: bool) -> Iterator[None]:
    if not enabled:
        yield
        return

    log_path = output_dir / "kev-server.log"
    with log_path.open("w", encoding="utf-8") as log:
        env = dict(os.environ)
        env.setdefault("KEV_DTYPE", "bf16")
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "kev.serve",
                "--run",
                KEV_CHECKPOINT,
                "--port",
                str(KEV_PORT),
            ],
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            _wait_for_kev(process)
            yield
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)


def _run_command(
    *,
    model: str,
    game: str,
    args: argparse.Namespace,
    output: Path,
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "jevbench",
        "run",
        game,
        "--policy",
        model,
        "--episodes",
        str(args.episodes),
        "--seed",
        str(args.seed),
        "--difficulty",
        args.difficulty,
        "--record-decisions",
        "--output",
        str(output),
    ]
    if args.mode != "auto":
        command.extend(["--mode", args.mode])
    if args.max_seconds is not None and game in {"tetris", "pong"}:
        command.extend(["--max-seconds", str(args.max_seconds)])
    if args.max_pieces is not None and game == "tetris":
        command.extend(["--max-pieces", str(args.max_pieces)])
    if args.max_decisions is not None:
        command.extend(["--max-decisions", str(args.max_decisions)])
    return command


def _benchmark_error(payload: dict[str, Any]) -> str | None:
    aggregate = payload["aggregate"]
    failures = {
        name: int(aggregate.get(name, 0))
        for name in ("timeouts", "policy_errors")
        if int(aggregate.get(name, 0)) > 0
    }
    if not failures:
        return None
    detail = ", ".join(f"{name}={count}" for name, count in failures.items())
    return f"benchmark reported model-call failures: {detail}"


def _run_suite(args: argparse.Namespace, models: list[str], games: list[str]) -> int:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC)
    hardware = {
        "accelerator": os.environ.get("ACCELERATOR") or None,
        "gpu": _gpu_name(),
        "cpu_cores": os.environ.get("CPU_CORES") or None,
        "memory": os.environ.get("MEMORY") or None,
    }
    if hardware["gpu"]:
        os.environ["NARCADE_HARDWARE"] = " · ".join(
            value for value in (hardware["accelerator"], hardware["gpu"]) if value
        )

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "benchmark_version": "0.4.0",
        "job_id": os.environ.get("JOB_ID") or None,
        "image": os.environ.get("NARCADE_JOB_IMAGE") or None,
        "started_at": started.isoformat(),
        "hardware": hardware,
        "configuration": {
            "models": models,
            "games": games,
            "episodes": args.episodes,
            "first_seed": args.seed,
            "difficulty": args.difficulty,
            "mode": args.mode,
            "max_seconds": args.max_seconds,
            "max_pieces": args.max_pieces,
            "max_decisions": args.max_decisions,
        },
        "runs": [],
    }
    failures = 0
    manifest_path = output_dir / "manifest.json"

    def write_manifest() -> None:
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    write_manifest()
    for model in models:
        try:
            with _kev_server(output_dir, model == "kev"):
                for game in games:
                    output = output_dir / f"{model}-{game}.json"
                    run_started = time.monotonic()
                    print(f"[narcade] {model} / {game}", flush=True)
                    completed = subprocess.run(
                        _run_command(model=model, game=game, args=args, output=output),
                        capture_output=True,
                        check=False,
                        text=True,
                    )
                    run: dict[str, Any] = {
                        "model": model,
                        "game": game,
                        "output": output.name,
                        "duration_seconds": round(time.monotonic() - run_started, 3),
                        "status": "completed" if completed.returncode == 0 else "failed",
                    }
                    if completed.returncode == 0:
                        try:
                            payload = json.loads(output.read_text(encoding="utf-8"))
                            run["mean_score"] = payload["aggregate"]["mean_score"]
                            run["success_rate"] = payload["aggregate"]["success_rate"]
                            benchmark_error = _benchmark_error(payload)
                            if benchmark_error:
                                completed = subprocess.CompletedProcess(
                                    completed.args,
                                    1,
                                    completed.stdout,
                                    benchmark_error,
                                )
                                run["status"] = "failed"
                            print(
                                f"[narcade] score={run['mean_score']} "
                                f"success={run['success_rate']}",
                                flush=True,
                            )
                        except (KeyError, OSError, ValueError) as error:
                            completed = subprocess.CompletedProcess(
                                completed.args,
                                1,
                                completed.stdout,
                                f"could not read benchmark output: {error}",
                            )
                            run["status"] = "failed"
                    if completed.returncode != 0:
                        failures += 1
                        error_path = output.with_suffix(".error.log")
                        error = completed.stderr.strip() or completed.stdout.strip()
                        error_path.write_text(error[-20_000:] + "\n", encoding="utf-8")
                        run["error"] = error_path.name
                        print(f"[narcade] failed; see {error_path.name}", flush=True)
                    manifest["runs"].append(run)
                    write_manifest()
        except (OSError, RuntimeError) as error:
            failures += 1
            error_path = output_dir / f"{model}-startup.error.log"
            error_path.write_text(f"{error}\n", encoding="utf-8")
            manifest["runs"].append(
                {
                    "model": model,
                    "game": None,
                    "status": "failed",
                    "error": error_path.name,
                }
            )
            print(f"[narcade] {model} startup failed; continuing", flush=True)
            write_manifest()

    manifest["finished_at"] = datetime.now(UTC).isoformat()
    manifest["status"] = "completed" if failures == 0 else "completed_with_failures"
    manifest["failure_count"] = failures
    write_manifest()
    return 0 if failures == 0 else 1


def main(argv: list[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    try:
        models = _csv(args.models, choices=MODELS, field="models")
        games = _csv(args.games, choices=GAMES, field="games")
        _validate(args, models, games)
        status = _run_suite(args, models, games)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from error
    raise SystemExit(status)


if __name__ == "__main__":
    main()
