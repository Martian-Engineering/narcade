from __future__ import annotations

import json
import multiprocessing
import os
import platform
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .config import RunConfig
from .laya_policy import LayaPolicy
from .models import DEFAULT_MODELS
from .policies import HeuristicPolicy, RandomPolicy
from .registry import RULES_VERSION, create_game
from .runner import FAILURES, PROTOCOL, run_benchmark
from .runtime import _kev_server
from .systemone import SystemOnePolicy


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def _run_model(config: RunConfig, name: str, output: Path) -> None:
    failed = False
    try:
        with _kev_server(output, name == "kev"):
            model = DEFAULT_MODELS.get(name)
            policy = None
            if model:
                policy = (
                    LayaPolicy(model)
                    if model.runtime == "laya"
                    else SystemOnePolicy(model, timeout_seconds=config.request_timeout)
                )

            def policy_factory(seed):
                if name == "random":
                    return RandomPolicy(seed ^ 0x5EED)
                return HeuristicPolicy() if name == "heuristic" else policy

            for game in config.games:
                trace_file = None
                try:
                    if config.trace:
                        trace_file = (output / f"{name}-{game}.jsonl").open("w")
                    options = config.game_options(game)
                    result = run_benchmark(
                        lambda seed, game=game, options=options: create_game(
                            game, seed=seed, **options
                        ),
                        policy_factory,
                        game_id=game,
                        policy_name=name,
                        first_seed=config.seed,
                        episodes=config.episodes,
                        max_decisions=config.max_decisions,
                        trace=(
                            lambda record, stream=trace_file: stream.write(
                                json.dumps(record) + "\n"
                            )
                        )
                        if trace_file
                        else None,
                    )
                    result["configuration"] = {
                        "rules_version": RULES_VERSION,
                        **options,
                        "max_decisions": config.max_decisions,
                    }
                    result["status"] = (
                        "failed"
                        if any(result["aggregate"][key] for key in FAILURES)
                        else "completed"
                    )
                    failed |= result["status"] == "failed"
                    write_json(output / f"{name}-{game}.json", result)
                    print(
                        f"{name}/{game}: {result['aggregate']['mean_score']} ({result['status']})",
                        flush=True,
                    )
                except (OSError, ValueError, RuntimeError) as error:
                    failed = True
                    (output / f"{name}-{game}.error.log").write_text(str(error) + "\n")
                finally:
                    if trace_file:
                        trace_file.close()
    except (OSError, ValueError, RuntimeError) as error:
        failed = True
        (output / f"{name}.error.log").write_text(str(error) + "\n")
    raise SystemExit(int(failed))


def run_suite(config: RunConfig, output: Path) -> int:
    config.validate()
    config.secrets()
    output.mkdir(parents=True, exist_ok=True)
    # HF creates a .keep placeholder when mounting an empty output volume.
    if any(path.name != ".keep" or not path.is_file() for path in output.iterdir()):
        raise ValueError("output directory must be empty; use a new directory for each run")
    manifest = {
        "benchmark_version": PROTOCOL,
        "configuration": asdict(config),
        "started_at": datetime.now(UTC).isoformat(),
        "job_id": os.environ.get("JOB_ID"),
        "image": os.environ.get("NARCADE_JOB_IMAGE"),
        "hardware": os.environ.get("ACCELERATOR") or platform.platform(),
        "runs": [],
        "status": "running",
    }
    write_json(output / "manifest.json", manifest)
    # A process per model releases accelerator memory before the next lane loads.
    for name in config.models:
        process = multiprocessing.get_context("spawn").Process(
            target=_run_model, args=(config, name, output)
        )
        process.start()
        process.join()
        manifest["runs"].append(
            {"model": name, "status": "completed" if process.exitcode == 0 else "failed"}
        )
        write_json(output / "manifest.json", manifest)
    failed = any(run["status"] == "failed" for run in manifest["runs"])
    manifest.update(
        status="failed" if failed else "completed", finished_at=datetime.now(UTC).isoformat()
    )
    write_json(output / "manifest.json", manifest)
    return int(failed)
