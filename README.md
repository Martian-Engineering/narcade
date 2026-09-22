# NARCADE

A benchmark for decision models playing Minesweeper, Tetris, and Snake.
The repository contains the engines, one suite runner, a Hugging Face launcher,
and a static results site. Random and game-specific heuristic players provide
comparison baselines.

## Findings and interpretation

September 22, 2026, protocol 0.5.0. Mean raw scores across three seeds:

| Policy | Tetris points | Snake food | Minesweeper safe squares |
| --- | ---: | ---: | ---: |
| Jev 1.13.0 | 0 | 0.67 | 57.33 |
| OpenJev 0.1 | 0 | 0 | 56.67 |
| Kev 4B | 0 | 0 | 57.33 |
| Heuristic | 4,500 | 33 | 69.67 |
| Random | 0 | 0 | 58.00 |

All 45 episodes completed with zero invalid actions, timeouts, or policy errors.
None of the three models cleared a Tetris line or solved a Minesweeper board.
Jev ate one food in two Snake episodes; the other models ate none. The heuristic
solved one of three Minesweeper boards. Its Tetris episodes reached the diagnostic
decision cap, so the reported score is not a completed-game victory.

NARCADE tests direct action selection from structured game state. Models receive
primitive controls, not scored Tetris placements, a Snake path planner, or a
Minesweeper solver. There is no LLM planner, human intervention, or search over
future game states in the model lanes. The heuristic baseline does use
game-specific logic and is a reference controller, not an equivalent model input.

The protocol 0.5.0 run shows poor autonomous play from Jev, OpenJev, and Kev under
this interface. These results support treating the tested models as decision
components that may need a harness, an LLM planner, or human-provided structure,
not as demonstrated general-purpose agents. Fast action selection alone does not
establish reliable multi-step planning or spatial reasoning.

A successful assisted demo measures the whole system: its model, state encoder,
candidate generator, and external logic. That assistance is a valid engineering
choice, but its contribution should be disclosed when presenting model ability.
This benchmark does not audit every public demo or prove that non-autoregressive
models inherently lack reasoning. It also does not compare assisted and
unassisted variants, so it cannot quantify the benefit of a harness. Prompt
sensitivity, task representation, and model capability remain confounded.

The run uses three seeds (100–102), medium difficulty, lockstep decisions, a
500-decision cap, and a 200-piece Tetris cap. This is a small diagnostic sample,
not a statistically robust ranking. Jev and OpenJev use hosted APIs called from
the local runner; Kev runs in BF16 on an HF A100. Lockstep prevents inference
latency from advancing the games. Minesweeper starts with an automatic safe
opening, so its raw score includes squares the model did not reveal. Tetris and
Snake are scored by line-clear points and food eaten, not a shared notion of
"clearing" all three games.

## Run locally

Requires Python 3.11+ and uv. Model definitions and checkpoint revisions live in
`src/jevbench/models.py`. Hosted Jev and OpenJev read `TYPESAFE_API_KEY` and
`CODIV_API_KEY` from the environment. Select only the models you want to run.

```sh
uv run jev-bench --models random,heuristic --games minesweeper,snake \
  --episodes 3 --seed 100 --output-dir results/local-001
```

`--models` and `--games` accept comma-separated names. The default model set is
random, heuristic, Jev, OpenJev, and Kev; all three games run by default.
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
- Snake: food eaten; walls/body collisions or a filled board end play. Four fixed directions.

Tetris and Snake default to realtime. The engine advances while the model
answers. Snake retains the previous movement; Tetris applies gravity
and discards a response if the observed piece has locked. `--mode lockstep`
is a separate diagnostic track. Minesweeper always uses turn-based play.

`--difficulty` sets easy/medium/hard rules and timing. `--max-seconds` caps Tetris;
it does not affect Snake or Minesweeper.
`--max-pieces` is an optional Tetris diagnostic cap. `--max-decisions` defaults
to 2,000 calls per episode. Diagnostic stops are not wins.

Protocol 0.5.0 uses smaller observations: a single coordinate representation for
Snake, a single board representation for Tetris, and fewer derived fields in
Minesweeper. Rules and heuristic players retain rules version 0.4.0. Bump `RULES_VERSION` in
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
0.5.0 lockstep run, including the heuristic players. Raw outputs and
historical reports are kept outside source control.

To compare future observation changes, rerun the same models, hardware,
seeds, mode, difficulty, and caps as the published reference. Use `--mode lockstep
--max-pieces 200 --max-decisions 500 --episodes 3 --seed 100` for that reference.
Pass `--compare-with app/src/data/published.json` to the publisher and write to a
new output file. It reports paired seed score differences, absolute mean changes,
and percentage changes when the old mean is nonzero. It rejects changed model
revisions, hardware, rules, or seeds. An observation protocol version change is allowed; the separate rules version
must match.
The website replay files are exported from the matching JSONL decision traces.
The exporter rejects state, instruction, action-set, and final-score mismatches:

```sh
uv run python scripts/export_replays.py \
  --input results/hf-v050-final-20260922 results/local-v050-final-20260922
```

Protocol 0.5.0 traces retain states and selected actions, but do not retain returned
probabilities. Replay playback speed is illustrative, not the original request timing.

## Deploy the site

Import `Martian-Engineering/narcade` into Vercel under the Martian Engineering
team. Set the root directory to `app`, select Next.js, and use `pnpm build` with
Node.js 22. The site uses a static export and requires no model API keys.
The importing account needs permission to create projects in that team.

## Validate

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
uvx ruff check .
cd app && pnpm build
```
