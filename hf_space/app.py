from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import gradio as gr

OPEN_MODELS = ["laya", "laya-typed", "laya-multilingual"]


def _results_dir() -> Path:
    preferred = Path(os.environ.get("NARCADE_RESULTS_DIR", "/data/results"))
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred
    except OSError:
        fallback = Path("/tmp/narcade-results")
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def _validate_models(models: list[str]) -> None:
    if not models:
        raise gr.Error("Select at least one model.")
    if any(model not in OPEN_MODELS for model in models):
        raise gr.Error("The Space runner accepts only its pinned open-model lanes.")


def _command_error(completed: subprocess.CompletedProcess[str]) -> gr.Error:
    detail = completed.stderr.strip() or completed.stdout.strip() or "Benchmark process failed."
    return gr.Error(detail[-4000:])


def cache_models(models: list[str]) -> str:
    selected = [model for model in models if model in OPEN_MODELS]
    if not selected:
        raise gr.Error("Select at least one open Laya model to download.")
    completed = subprocess.run(
        [sys.executable, "-m", "jevbench", "cache", "--models", ",".join(selected)],
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode:
        raise _command_error(completed)
    cached = json.loads(completed.stdout)["cached"]
    return "Cached pinned checkpoints:\n\n" + "\n".join(
        f"- `{name}` → `{path}`" for name, path in cached.items()
    )


def run_benchmark(
    game: str,
    models: list[str],
    difficulty: str,
    mode: str,
    episodes: float,
    seed: float,
    max_seconds: float | None,
    max_decisions: float,
) -> tuple[str, str]:
    _validate_models(models)
    output = _results_dir() / f"{game}-{uuid.uuid4().hex[:10]}.json"
    command = [
        sys.executable,
        "-m",
        "jevbench",
        "compare",
        game,
        "--models",
        ",".join(models),
        "--difficulty",
        difficulty,
        "--episodes",
        str(int(episodes)),
        "--seed",
        str(int(seed)),
        "--record-decisions",
        "--output",
        str(output),
    ]
    if game in {"pong", "tetris"} and max_seconds is not None:
        command.extend(["--max-seconds", str(float(max_seconds))])
    if mode != "auto":
        command.extend(["--mode", mode])
    if max_decisions:
        command.extend(["--max-decisions", str(int(max_decisions))])

    completed = subprocess.run(command, capture_output=True, check=False, text=True)
    if completed.returncode:
        raise _command_error(completed)

    payload = json.loads(output.read_text(encoding="utf-8"))
    rows = [
        "| Model | Mean score | Success | p50 latency | Late decisions |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, result in payload["results"].items():
        aggregate = result["aggregate"]
        rows.append(
            f"| {name} | {aggregate['mean_score']:.3f} | "
            f"{aggregate['success_rate']:.1%} | {aggregate['p50_latency_ms']:.1f} ms | "
            f"{aggregate.get('late_decisions', 0)} |"
        )
    summary = (
        f"### {game.title()} · {payload['mode']}\n\n"
        + "\n".join(rows)
        + f"\n\nSeeds: `{payload['first_seed']}`-"
        f"`{payload['first_seed'] + payload['episode_count'] - 1}`"
    )
    return summary, str(output)


with gr.Blocks(title="NARCADE") as demo:
    gr.Markdown(
        "# NARCADE 🕹️\n"
        "Latency-aware game evaluation for non-autoregressive decision models. "
        "Dynamic games default to real time; late answers change the game state."
    )
    with gr.Row():
        game = gr.Dropdown(["minesweeper", "tetris", "pong", "snake"], value="tetris", label="Game")
        models = gr.CheckboxGroup(OPEN_MODELS, value=["laya"], label="Models")
        difficulty = gr.Dropdown(["easy", "medium", "hard"], value="medium", label="Difficulty")
        mode = gr.Dropdown(["auto", "realtime", "lockstep"], value="auto", label="Timing")
    with gr.Row():
        episodes = gr.Number(value=3, precision=0, minimum=1, maximum=100, label="Episodes")
        seed = gr.Number(value=100, precision=0, label="First seed")
        max_seconds = gr.Number(
            value=None,
            minimum=1,
            label="Max simulated seconds (blank = game default)",
        )
        max_decisions = gr.Number(
            value=0,
            precision=0,
            minimum=0,
            label="Decision cap (0 = game default)",
        )
    with gr.Row():
        run = gr.Button("Run benchmark", variant="primary")
        cache = gr.Button("Download selected open models")
    status = gr.Markdown()
    result_file = gr.File(label="Raw result")

    cache.click(cache_models, inputs=[models], outputs=[status], concurrency_limit=1)
    run.click(
        run_benchmark,
        inputs=[game, models, difficulty, mode, episodes, seed, max_seconds, max_decisions],
        outputs=[status, result_file],
        concurrency_limit=1,
    )

demo.queue(default_concurrency_limit=1).launch()
