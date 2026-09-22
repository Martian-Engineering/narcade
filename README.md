# NARCADE

A benchmark for decision models playing Minesweeper, Tetris, Pong, and Snake.
The repository contains the engines, one suite runner, a Hugging Face launcher,
and a static results site. Random and game-specific heuristic players provide
comparison baselines.

## Run locally

Requires Python 3.11+ and uv. Model definitions and checkpoint revisions live in
`src/jevbench/models.py`. Hosted Jev and OpenJev read `TYPESAFE_API_KEY` and
`CODIV_API_KEY` from the environment. Select only the models you want to run.

```sh
uv run jev-bench --models random,heuristic --games minesweeper,pong \
  --episodes 3 --seed 100 --output-dir results/local-001
```

`--models` and `--games` accept comma-separated names. The default model set is
random, heuristic, Jev, OpenJev, and Kev; all four games run by default.
Local Kev requires its pinned serving runtime from `hf/requirements.in`.
Laya lanes require `uv sync --extra laya`. Each model runs in its own process so
its accelerator memory is released before the next model loads. Kev's server
starts and stops automatically.

Every run needs an empty output directory. The runner writes one result JSON
per model/game plus a manifest, preserves partial results, and exits nonzero on
model failures. `--trace` adds separate per-decision JSONL files. Raw output is
ignored by Git.

## Run on Hugging Face

The launcher mounts a wheel, pinned dependencies, and the same run configuration
into a CUDA container. No Space or Gradio application is required.

```sh
uv run --extra hub python scripts/run_hf_job.py \
  --models kev --flavor a100-large --episodes 3 --seed 100 \
  --output-dir results/hf-001
```

The launcher waits for completion and downloads the output volume. `--detach`
prints the Job and artifact locations and returns immediately. `--job-timeout`
defaults to six hours. Only secrets required by the selected models are sent;
`--models kev` sends no hosted-provider keys. To keep hosted keys local, run Jev
and OpenJev locally and local-weight models on HF with the same seeds and caps.
Label the hardware in published comparisons; realtime scores depend on latency.

## Game protocol

- Minesweeper: safe squares revealed, plus solve time for cleared boards only.
  Model latency is measured without advancing the board.
- Tetris: classic line-clear score; top-out ends play. Six fixed controls.
- Pong: points against a seeded tracking opponent; first to three or 120 simulated seconds.
- Snake: food eaten; walls/body collisions or a filled board end play. Four fixed directions.

Pong, Tetris, and Snake default to realtime. The engine advances while the model
answers. Pong and Snake retain the previous movement; Tetris applies gravity
and discards a response if the observed piece has locked. `--mode lockstep`
is a separate diagnostic track. Minesweeper always uses turn-based play.

`--difficulty` sets easy/medium/hard rules and timing. `--max-seconds` caps Tetris
or sets Pong's match duration; it does not affect Snake or Minesweeper.
`--max-pieces` is an optional Tetris diagnostic cap. `--max-decisions` defaults
to 2,000 calls per episode. Diagnostic stops are not wins.

Protocol 0.5.0 uses smaller observations: a single coordinate representation for
Snake, a single board representation for Tetris, and fewer derived fields in
Minesweeper/Pong. Rules and heuristic players retain rules version 0.4.0. Bump `RULES_VERSION` in
`registry.py` when rules, scoring, timing semantics, or heuristics change. Action presentation
order remains deterministic per game, seed, and decision.

## Publish and compare

The website reads `app/src/data/published.json`, generated from explicitly
selected completed runs. Failed runs, duplicate model/game entries, and mixed
protocols or seeds within one game are rejected.

```sh
uv run python -m jevbench.publication \
  results/local-001/random-minesweeper.json \
  results/local-001/heuristic-minesweeper.json \
  --label 'Run 001' --output app/src/data/published.json
cd app
pnpm install --frozen-lockfile
pnpm build
```

Deploy `app/out/` as static files. The checked-in publication is a three-seed
0.4.0 lockstep reference run, including the heuristic players. Raw outputs and
historical reports are kept outside source control.

To measure whether simplified observations help, rerun the same models, hardware,
seeds, mode, difficulty, and caps as the reference. Use `--mode lockstep
--max-pieces 200 --max-decisions 500 --episodes 3 --seed 100` for that reference.
Pass `--compare-with app/src/data/published.json` to the publisher and write to a
new output file. It reports paired seed score differences, absolute mean changes,
and percentage changes when the old mean is nonzero. It rejects changed model
revisions, hardware, rules, or seeds. An observation protocol version change is allowed; the separate rules version
must match.
No new model-performance claim is made until those reruns finish.

## Validate

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
uvx ruff check .
cd app && pnpm build
```
