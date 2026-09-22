# Jev Game Bench

Jev Game Bench measures how well decision models play structured-state games. The initial suite contains Minesweeper, Tetris, and Pong. Each game is deterministic for a given seed, runs headlessly, exposes a bounded legal action set, and returns an objective score.

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

Use the same command for the other games. Tetris has one standard ruleset and therefore uses the default `--difficulty medium` value:

```sh
jev-bench compare tetris --episodes 10 --seed 100 --max-decisions 200 \
  --record-decisions --output results/tetris.json
jev-bench compare pong --episodes 10 --seed 100 --difficulty medium \
  --record-decisions --output results/pong.json
```

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

OpenJev's local server normally runs at `http://127.0.0.1:8080`. Its NVFP4 DiffusionGemma checkpoint is roughly 19 GB, and the current setup requires an NVIDIA GPU with at least 24 GB. Pin the OpenJev commit and container digest because its inference stack is still changing.

Never put hosted API keys in `models.toml`. Keep `api_key_env` for hosted lanes and provide secrets through the environment. Result metadata omits credentials and URL query strings.

Additional System One-compatible models can be added as `[models.<name>]` tables with at least `base_url` and `model`.

## Games and scores

| Game | Primary score | Success | Opponent or reference |
|---|---|---|---|
| Minesweeper | Safe squares revealed | Clear every safe square | Random clicker and a local clue-risk heuristic |
| Tetris | Classic line-clear score | Survive the configured piece limit | Random placement and a board-feature heuristic |
| Pong | Points scored | Defeat the opponent | Seeded tracking bot at easy, medium, or hard strength |

Raw scores remain game-specific. Minesweeper points are not added to Tetris points. Future cross-game normalization can use `(model - random) / (heuristic - random)`, but raw scores and seed-level results should remain visible.

## Pong opponent and timing

The evaluated model controls the right paddle. The left paddle is a deterministic tracking bot whose speed, reaction interval, and seeded aiming error are set by `--difficulty`. This avoids making the score depend on a second model release.

Pong supports two timing modes:

- `--mode lockstep` advances the game by 100 ms after every answer and ignores request latency in the physics. This measures action quality.
- `--mode realtime` advances the ball while the model is answering. The previous paddle command remains active until the new answer arrives. This measures action quality and response speed together.

Run and report both modes. A model can be strategically correct in lockstep and too slow to intercept the same shots in real time.

## Fairness and result contract

The runner fixes consecutive environment seeds, game difficulty, timing mode, decision budget, model identifier, and endpoint. It deterministically randomizes legal-action order per game, seed, and step. No model receives a retry that changes the prompt, and no failed call is replaced by a scripted move.

Each model result separates gameplay from systems behavior:

- score distribution and success rate;
- invalid actions, provider errors, and timeouts;
- median and p95 end-to-end decision latency;
- input and output tokens;
- mean confidence and probability entropy when supplied.

Probability entropy is not a calibration score. Calibration needs a defensible action-quality label or downstream outcome definition and remains a separate evaluation. Operators should declare known game-specific training exposure and use unseen variants for final leaderboards.

For a publishable local-model result, fill in the checkpoint revision, runtime revision, container digest, quantization, hardware, and training exposure fields. Hosted responses record both the requested model and the provider-reported resolved model when available.

## Repository structure

```text
models.toml                model lanes and reproducibility metadata
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
tests/                     engine, runner, config, CLI, and client tests
docs/BENCHMARK_RESEARCH.md repository survey and design notes
TODO.md                    linked backlog for larger environments
```

## Validation

```sh
uvx ruff check .
python3 -m unittest discover -s tests -v
```
