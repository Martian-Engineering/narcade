# NARCADE

NARCADE (**N**on-**A**utoregressive **R**anking and **C**hoice **A**cross **D**iscrete **E**nvironments) measures how well decision models play structured-state games. The initial suite contains Minesweeper, Tetris, Pong, and Snake. Each game is deterministic for a given seed, runs headlessly, exposes a bounded legal action set, and returns an objective score.

## Leaderboard website

The Next.js results site lives in `app/` and presents the first benchmark run, protocol, and game-level leaderboard.

```sh
cd app
pnpm install
pnpm dev
```

The model comparison has hosted, local, and open-weight lanes:

| Lane | Default model | Endpoint | Authentication |
|---|---|---|---|
| Jev | `jev-1.13.0` | `https://api.typesafe.ai/v1/systemone` | `TYPESAFE_API_KEY` |
| OpenJev | `openjev-0.1` | `https://api.codiv.ai/v1/systemone` | `CODIV_API_KEY` |
| Kev | `kev-latest`, serving `jaredpalmer/kev-4b` | `http://127.0.0.1:8009/v1/systemone` | Local dummy key |
| Laya | `convaiinnovations/laya` | Local Python runtime | None |
| Laya Typed | `convaiinnovations/laya-typed-decisions` | Local Python runtime | None |
| Laya Multilingual | `convaiinnovations/laya-multilingual` | Local Python runtime | None |

Hosted models and Kev use the same System One HTTP adapter. Laya uses its official local runtime with the same state, instructions, and choice criteria.

## Install

The benchmark requires Python 3.11 or later and has no runtime dependencies.

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
jev-bench list
```

Install the optional Laya runtime to run either local Laya lane:

```sh
pip install -e '.[laya]'
```

For development without installation, prefix commands with `PYTHONPATH=src python3 -m jevbench`.

Pre-download all pinned Laya checkpoints into the Hugging Face cache with:

```sh
jev-bench cache
```

## Run the comparison

Start the local Kev server:

```sh
git clone https://github.com/jaredpalmer/kev
cd kev
uv sync --extra serve
KEV_DTYPE=bf16 uv run --extra serve python -m kev.serve \
  --run jaredpalmer/kev-4b --port 8009
```

Set the two hosted-service keys, then run the models on the same seed pack:

```sh
export TYPESAFE_API_KEY="..."
export CODIV_API_KEY="..."

jev-bench compare minesweeper \
  --models jev,openjev,kev,laya \
  --episodes 20 \
  --seed 100 \
  --record-decisions \
  --output results/minesweeper.json
```

The command runs models sequentially. Every model receives the same game seeds, state encoder, instructions, and deterministic action-ordering rule. Their later states can differ because each model follows its own trajectory. `--record-decisions` preserves each presented action order, selected action, full provider probability vector when supplied, confidence, entropy, usage, latency, and model-input hash.

Use the same command for the other games. Tetris, Pong, and Snake default to the latency-aware real-time track:

```sh
jev-bench compare tetris --episodes 10 --seed 100 \
  --record-decisions --output results/tetris.json
jev-bench compare pong --episodes 10 --seed 100 --difficulty medium \
  --record-decisions --output results/pong.json
jev-bench compare snake --episodes 10 --seed 100 --difficulty medium \
  --record-decisions --output results/snake.json
```

Use `--mode lockstep` to measure action quality without allowing latency to change game state. Pong defaults to a 120-second match limit. Tetris and Snake have no time or decision limit by default: Tetris runs until top-out, and Snake runs until collision or a filled board.

`--max-seconds`, `--max-pieces`, and `--max-decisions` can explicitly cap Tetris for debugging or cost control. These are diagnostic stops, not successful game outcomes.

## Run on Hugging Face

The Hugging Face deployment uses one Docker image for interactive smoke tests and batch benchmark
runs. A batch run uses one GPU and evaluates model lanes sequentially. This keeps local-model scores
on the same accelerator and releases Kev before Laya starts. Separate GPUs are useful only for
parallel throughput or runtimes that require different accelerator architectures.

The primary hardware track is `a100-large`, a single 80 GB A100. It has enough memory for Kev and
the Laya family, is widely available, and gives every local lane the same latency environment.
`a10g-small` is suitable for cheaper smoke tests. Do not mix hardware flavors on one leaderboard.

The default run covers the three requested model lanes: hosted Jev, hosted OpenJev, and local Kev.
Random and heuristic policies run alongside them as calibration anchors. Optional Laya lanes also
run locally on the Job GPU. Local OpenJev NVFP4 inference requires Hopper or Blackwell hardware and
belongs in a separate hardware track; Jev does not publish local weights.

Publish the private Docker Space that supplies the Job image:

```sh
uv run --with huggingface-hub python scripts/publish_hf_space.py YOUR_ORG/narcade
```

The publisher creates a private Docker Space and does not request paid hardware. The Space UI runs
pinned Laya checkpoints for smoke tests. The same image includes the pinned Kev runtime and the
batch entry point.

Provide hosted-model keys in the launcher environment, then start a pay-per-minute Job:

```sh
export TYPESAFE_API_KEY=...
export CODIV_API_KEY=...

uv run --with 'huggingface-hub>=1.32,<2' python scripts/run_hf_job.py \
  YOUR_ORG/narcade \
  --flavor a100-large \
  --models random,heuristic,jev,openjev,kev \
  --games minesweeper,tetris,pong,snake \
  --episodes 3 \
  --seed 100
```

The launcher validates required secrets before provisioning compute, creates a writable output
volume, waits for the Job, and downloads the results. Each run produces one raw JSON file plus a
`manifest.json` containing the Job ID, Docker image, hardware flavor, GPU name, seed pack, and run
status. The paid runner defaults to a 200-piece Tetris cap and a 2,000-decision safety cap per
episode. A provider error or request timeout fails its lane and the final Job while preserving all
partial outputs. Use `--detach` to schedule without waiting. Hugging Face Jobs require a positive
credit balance and bill until the process exits or reaches `--timeout`.

Run random and heuristic anchors before paying for model calls:

```sh
jev-bench compare minesweeper --models random,heuristic --episodes 20 --seed 100
jev-bench run pong --policy heuristic --episodes 10 --seed 100
```

## Model configuration

Built-in settings work without a config file. Copy or edit [`models.toml`](models.toml) when running OpenJev locally or when recording exact local revisions:

```toml
[models.openjev]
base_url = "http://127.0.0.1:8080"
model = "openjev-0.1"
api_key = "local"
artifact = "nvidia/diffusiongemma-26B-A4B-it-NVFP4"
artifact_revision = "<pinned Hugging Face commit>"
runtime = "openjev"
runtime_revision = "<pinned OpenJev commit>"
container_digest = "sha256:<digest>"
quantization = "NVFP4"
hardware = "<GPU model>"
training_exposure = "unknown"
```

Pass the file explicitly:

```sh
jev-bench compare minesweeper --models-file models.toml --episodes 20 --seed 100
```

OpenJev's local server normally runs at `http://127.0.0.1:8080`. Its NVFP4 DiffusionGemma checkpoint
targets NVIDIA Hopper and Blackwell GPUs. Pin the OpenJev commit, container digest, and exact GPU
because its local results are a distinct hardware track from the A100 Job above.

Never put hosted API keys in `models.toml`. Keep `api_key_env` for hosted lanes and provide secrets through the environment. Result metadata omits credentials and URL query strings.

Additional System One-compatible models can be added as `[models.<name>]` tables with at least `base_url` and `model`.

## Games and scores

| Game | Primary score | Success | Opponent or reference |
|---|---|---|---|
| Minesweeper | Safe squares revealed | Clear every safe square | Random clicker and a local clue-risk heuristic |
| Tetris | Classic line-clear score | No win state; play ends at top-out | Random controls and a board-feature heuristic baseline |
| Pong | Points scored | Defeat the opponent | Seeded tracking bot at easy, medium, or hard strength |
| Snake | Food eaten | Fill the board | Random movement and a deterministic pathfinding heuristic |

Raw scores remain game-specific. Minesweeper points are not added to Tetris points. Future cross-game normalization can use `(model - random) / (heuristic - random)`, but raw scores and seed-level results should remain visible.

## Timing

The evaluated model controls the right paddle. The left paddle is a deterministic tracking bot whose speed, reaction interval, and seeded aiming error are set by `--difficulty`. This avoids making the score depend on a second model release.

The three dynamic games support two timing modes:

- `--mode realtime` is the default leaderboard track. Pong and Snake keep executing the previous command while the model answers. Tetris applies gravity while the model answers and discards a response only if its observed piece has already locked.
- `--mode lockstep` is the diagnostic track. It advances once per answer and ignores request latency in game state, isolating action quality.

Difficulty controls timing pressure: Tetris control/gravity intervals are 500/250/100 ms and Snake ticks are 1500/1000/500 ms on easy/medium/hard. Pong uses a 100 ms control interval at every difficulty. Tetris always presents `LEFT`, `RIGHT`, `ROTATE`, `SOFT_DROP`, `HARD_DROP`, and `NONE`, without computed outcome hints. Snake always presents exactly `UP`, `DOWN`, `LEFT`, and `RIGHT`. In both games the engine alone owns movement rules, scoring, and terminal state. Report both timing tracks when diagnosing why a model wins or loses, but do not combine them in one leaderboard.

## Fairness and result contract

The runner fixes consecutive environment seeds, game difficulty, timing mode, decision budget, model identifier, and endpoint. It deterministically randomizes legal-action order per game, seed, and step. No model receives a retry that changes the prompt, and no failed call is replaced by a scripted move.

Each model result separates gameplay from systems behavior:

- score distribution and success rate;
- invalid actions, provider errors, and timeouts;
- median and p95 end-to-end decision latency;
- late-decision rate, missed pieces/ticks, simulated seconds, and score per second in real time;
- input and output tokens;
- mean confidence and probability entropy when supplied.

Probability entropy is not a calibration score. Calibration needs a defensible action-quality label or downstream outcome definition and remains a separate evaluation. Operators should declare known game-specific training exposure and use unseen variants for final leaderboards.

For a publishable local-model result, fill in the checkpoint revision, runtime revision, container digest, quantization, hardware, and training exposure fields. Hosted responses record both the requested model and the provider-reported resolved model when available.

## Repository structure

```text
models.toml                model lanes and reproducibility metadata
hf_space/                  Docker Space UI and runtime image
scripts/publish_hf_space.py reproducible Space publisher
src/jevbench/
  cli.py                   run and compare commands
  core.py                  game and policy contracts
  models.py                model configuration loader
  systemone.py             shared Jev/OpenJev/Kev client
  runner.py                episode execution and aggregation
  games/
    minesweeper/           seeded board and partial-progress score
    tetris/                seeded seven-bag engine and arcade score
    pong/                  physics and deterministic opponents
    snake/                 classic four-choice engine and food score
tests/                     engine, runner, config, CLI, and client tests
docs/BENCHMARK_RESEARCH.md repository survey and design notes
TODO.md                    linked backlog for larger environments
```

## Validation

```sh
uvx ruff check .
python3 -m unittest discover -s tests -v
```
