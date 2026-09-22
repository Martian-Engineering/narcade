# Jev Game Benchmark: repository survey and benchmark design

Research date: 2026-09-21

Source catalog: [Games and real time built with Jev](https://madewithjev.com/categories/games-and-real-time)

## Recommendation

Build a benchmark runner around a small environment protocol. Keep each game behind an adapter and pin the adapter to a game-engine revision. Do not copy all of the catalog repositories into one monorepo.

The benchmark should publish four measurements for every game:

1. **Outcome:** wins, score, progress, or task completion.
2. **Responsiveness:** median, p95, and deadline-miss latency.
3. **Reliability:** invalid actions, timeouts, retries, and harness fallbacks.
4. **Efficiency:** input tokens, model calls, and estimated cost.

Run two game modes when latency affects the outcome:

- **Lockstep:** the environment waits for the model. This isolates decision quality.
- **Real time:** the game continues while the model answers. This measures whether decision quality arrives in time to matter.

Keep structured-state and visual-control tasks on separate leaderboards. Nearly every project in this survey gives Jev structured state and a bounded legal action set. Calling that equivalent to playing from pixels would overstate what the model does.

## What is in the catalog

The catalog contains 29 entries: 16 GitHub builds, 11 X posts, and 2 articles. The source survey found exact public code for most GitHub builds and several X-only demonstrations. Where the original demo code was not public, the table names a related public implementation and labels it as such.

| Catalog entry | Public code found | Benchmark signal | Recommendation |
|---|---|---|---|
| Jev plays Super Mario Bros. | [fhshaik/typesafe-mario](https://github.com/fhshaik/typesafe-mario) | Level progress, reward, deaths, completion, latency. Includes headless mode and episode reset. | Strong later environment. Requires a legally obtained ROM and has no repository license. |
| Jev plays Doom | The launch demo has no public source. Related: [lukaske/jev-doom-agent](https://github.com/lukaske/jev-doom-agent). | Kills, health, survival time, map progress, completion, action latency. | Good real-time tier. Use Freedoom and a fixed map. The related repository exposes structured state and short control macros. |
| Wikiracing | No standalone repository found; the demo is described in the [TypeSafe launch article](https://typesafe.ai/blog/introducing-system-one-models-and-jev). | Reaches target, link clicks, elapsed time, invalid links. | Reimplement against a pinned Wikipedia snapshot. Useful long-horizon navigation task. |
| Jev plays chess | Article points to the same experiment represented by [maxim-saplin/llm_chess](https://github.com/maxim-saplin/llm_chess). | Win/draw/loss, Elo against fixed engines, illegal moves, game duration. | Adopt its benchmark concepts. Prefer a smaller adapter around `python-chess` over importing its large result history. |
| Jev plays Slay the Spire 2 | Original X demo source not confirmed. Public alternatives: [DiscreteTom/jev-sts2](https://github.com/DiscreteTom/jev-sts2) and [alexmeckes/jev-the-spire](https://github.com/alexmeckes/jev-the-spire). | Floors, combats won, HP, act/boss completion, run score, cost. Recorded-state evals exist. | Strong long-horizon tier. Pin game/mod versions and separate offline state-choice accuracy from full runs. |
| Jev plays Subway Surfers | Original source not found. Related: [afcodehub/Jev-Subway-Runner-3D](https://github.com/afcodehub/Jev-Subway-Runner-3D). | Distance, survival time, coins, collisions, action deadlines. | Reimplement a small endless runner to avoid asset and reproducibility problems. |
| Jev plays Smash Bros. against itself | No source found. | Match wins, stocks, damage, KOs, self-play rating. | Defer. Emulator and ROM setup plus multi-agent self-play make this expensive and hard to reproduce. |
| Jev plays Tetris | Original X demo source not found. Public alternatives: [trungdq88/jev-tetris](https://github.com/trungdq88/jev-tetris) and the Stacker scene in [lafollett-labs/typesafe-jev-dojo](https://github.com/lafollett-labs/typesafe-jev-dojo). | Lines, pieces survived, line rate, holes, top-out, missed deadlines. Both seeded and lockstep modes exist. | Core suite. Use the MIT-licensed Dojo engine or obtain permission for the other implementation. |
| Game levels generated in real time | No source found. | Playability, solvability, novelty, generation latency. | Separate generation track. It does not measure game-playing skill. |
| Jev plays Pokémon | [milanboers/jev-plays-pokemon](https://github.com/milanboers/jev-plays-pokemon) | Milestones, badges, battles, play time, decisions, cost. Headless PyBoy integration exists. | Later long-horizon environment. The harness uses macro goals plus deterministic pathfinding, so label it as macro-action control. |
| Beat Jev | [ojusave/beat-jev](https://github.com/ojusave/beat-jev) | Goals scored, saves, match win rate. | Optional two-player task. Replace the human with pinned shooter/keeper policies and remove hosted Render/Postgres requirements. |
| Jev runs a city's traffic | [skcache/jevtrafficsim](https://github.com/skcache/jevtrafficsim) | Travel time, delay, stops, queueing, throughput, policy failures. It has a headless benchmark CLI, deterministic replay, and scenario hashes. | Excellent control/simulation suite, but not the same leaderboard as games. No repository license is present. |
| TypeEvacSafe | [using76/TypeEvacSafe](https://github.com/using76/TypeEvacSafe) | Evacuation, deaths, exposure, congestion, rescue, family separation, decision speed. | Separate safety/control suite. License is PolyForm Noncommercial and the repository notes patent constraints. |
| jev-piano | [LamplighterPaul/jev-piano](https://github.com/LamplighterPaul/jev-piano) | Musical output and latency, but no objective game outcome. | Creative steering showcase, not a game benchmark. A listening study or style classifier would be a separate benchmark. |
| Can Jev steer music? | [wustep/jev-playground](https://github.com/wustep/jev-playground) | Style-match judgments, rendering validity, latency, tokens. | Creative-generation track. The repository has no license file. |
| Jev Pong | [ably-labs/jev-pong](https://github.com/ably-labs/jev-pong) | First to five, hit rate, prediction accuracy, p50/p95 latency, missed calls. | Core suite. It is Apache-2.0 and already separates engine behavior from presentation. |
| Jev vs the LLMs: Tetris | [trungdq88/jev-tetris](https://github.com/trungdq88/jev-tetris) | Lines, pieces, garbage, top-out, latency, deadline misses, invalid actions, tokens, cost. | Core design reference. It already has shared seeds, lockstep play, real-time gravity, and deterministic engine tests. |
| Kiru Hai Coach | [smilior/kiru-hai-coach](https://github.com/smilior/kiru-hai-coach) | Discard quality against a Mahjong engine or labeled positions. The app itself stores efficiency/safety/wait judgments. | Offline decision or coaching suite, not a game-playing environment. Repository code is not offered under an open-source license. |
| Jev plays Puyo Puyo | [puyoai/puyoai](https://github.com/puyoai/puyoai) is the game/AI framework; the Jev adapter from the X demo was not found. | Wins, chains, garbage sent, score, top-out, latency. | Promising turn-based core game after writing an adapter. The engine is older C++ and has a heavier build. |
| Jev plays Pokémon Showdown | [izzuddin8803/jev-showdown](https://github.com/izzuddin8803/jev-showdown) | Win rate, legal-action rate, turns, matchups, latency, tokens, cost. Includes fixed teams, swapped orientations, saved decisions, and exact replay verification. | Strong second-wave environment. The repository has no license file, so obtain permission or reproduce the experiment against Pokémon Showdown. |
| Mario Never Dies | [superradcompany/mario-never-dies](https://github.com/superradcompany/mario-never-dies) | Level progress, deaths, branches consumed, model calls, wall time, compute. | Research track for search/checkpoint policies. It changes the agent's resources by allowing VM branching, so do not compare its score directly with single-trajectory Mario. |
| Both hands on a piano, in real time | No source found. | Timing accuracy and missed notes could be objective; musicality is subjective. | Separate real-time control or music track after a reproducible note chart and timing judge exist. |
| jevs-fly | [webdevcody/jevs-fly](https://github.com/webdevcody/jevs-fly) | Pop count, crashes, flight duration, speed, altitude, tree clearance, answer mix. Includes seeded headless flight tests and reports. | Good second-wave continuous-control task. The repository has no license file. |
| game-coach | [JoelLewis/game-coach](https://github.com/JoelLewis/game-coach) | Agreement with labeled coaching judgments, calibration, latency, cost. Stockfish supplies objective chess facts. | Separate judgment/coaching suite. GPL-3.0 affects integration choices. |
| minecraft-agent | [rmalde/minecraft-agent](https://github.com/rmalde/minecraft-agent) | Victory, completion time, deaths, stage completion, actions, model calls. It records completion evidence and uses a fixed seed/route. | Capstone task. It uses an Astra planner, Jev controller, Mineflayer actions, surveyed coordinates, and a favorable seed. Report those assists as part of the task definition. |
| LLM Chess: jev-latest | [maxim-saplin/llm_chess](https://github.com/maxim-saplin/llm_chess) | Elo, win/loss, duration, illegal moves, tokens, cost, interruptions. | Strong second-wave environment and a useful result-schema reference. |
| JevMinesweeper | [EnesYilmazcode/JevMinesweeper](https://github.com/EnesYilmazcode/JevMinesweeper) | Clears and safe squares revealed on seeded boards. Includes random and solver baselines, deterministic replay, logs, and tests. | Best first environment. Reimplement the small engine or obtain permission because the repository has no license file. |
| typesafe-jev-dojo | [lafollett-labs/typesafe-jev-dojo](https://github.com/lafollett-labs/typesafe-jev-dojo) | The Stacker scene records lines, pieces, height, holes, latency, confidence, and top-out. | Best licensed source for the first Tetris adapter. MIT licensed. |
| A leveling agent that gets cheaper as it runs | [chalkychalk42/jev](https://github.com/chalkychalk42/jev) | XP/hour, levels, deaths, interventions, route completion, cost per XP, learned-policy coverage. | Capstone/continual-learning track. It targets a private TBC server and Windows capture, so reproducibility is limited. |

## Snake follow-up

An X search found two public Jev Snake implementations posted on September 17, 2026. [Musham Khan's post](https://x.com/iammusham/status/2100499596095209849) links to [`iammusham/jev-snake`](https://github.com/iammusham/jev-snake), a pure Python, seeded engine with structured state, explicit difficulty presets, terminal causes, tests, and benchmark guidance. [Nick Trierweiler's post](https://x.com/siroccomask/status/2100526283805675875) reports a 29-food, 461-decision run and links to [`siroccomask/snake-jev`](https://github.com/siroccomask/snake-jev). That controller asks nine binary subquestions per tick—three questions about each of three relative moves—and combines the answers in handwritten code. Those are not nine movement choices, but they are also not NARCADE's single four-way player decision.

[`sorrycc/typesafe-snake`](https://github.com/sorrycc/typesafe-snake) is the strongest TypeScript alternative: it has a seeded pure engine and fixed clock, but it filters moves and adds code-generated pathfinding features to their descriptions. NARCADE instead uses a classic 20x20 rules engine with seeded food. On every tick the model chooses exactly one of `UP`, `DOWN`, `LEFT`, and `RIGHT`; the engine applies classic reversal behavior, advances the snake, handles food and growth, detects collisions, and decides when the episode ends. No danger filter or pathfinding fact changes what the player sees.

## Best starting environments

### 1. Minesweeper

Minesweeper has the cleanest benchmark boundary in the survey:

- deterministic boards from a seed;
- a legal action set that changes each turn;
- exact terminal states;
- a useful partial score when the agent loses;
- cheap random and solver baselines;
- fast headless execution;
- replayable action logs.

Use multiple mine densities. Report clear rate and mean safe squares revealed. A solver should define the upper anchor; random clicks should define the lower anchor. Do not select showcase seeds after seeing model results.

### 2. Tetris

Tetris adds planning and a latency-sensitive mode without adding licensed game assets. Run the same seeded piece streams in two tracks:

- lockstep control, scored by lines and pieces survived until top-out;
- real time with fixed gravity, scored by lines, pieces, top-out time, and missed deadlines.

In both tracks the model receives only the fixed player controls `LEFT`, `RIGHT`, `ROTATE`,
`SOFT_DROP`, `HARD_DROP`, and `NONE`. The engine owns the active piece, gravity, collisions,
locking, line clears, scoring, and top-out. Do not expose engine-computed placement outcomes such
as projected holes, height, bumpiness, or line clears in the choices.

The Dojo Stacker engine is the easiest licensed starting point. The `jev-tetris` repository is the stronger experimental reference because it already compares models under both lockstep and gravity.

### 3. Pong

Pong isolates reaction speed. The existing repository is Apache-2.0 and records the right latency data. Add a deterministic server-side opponent and seeded serves. Run at several ball speeds so the leaderboard shows the point where each model's latency stops being useful.

### 4. Snake

Snake adds short-horizon navigation and self-collision while retaining an objective arcade score. Use seeded food and expose the same four absolute directions to every model on every tick, including fatal moves and the current direction's opposite. The rules engine—not the model adapter—owns reversal behavior, movement, growth, collision, and death. Report food eaten as the primary score and survival ticks as a secondary metric.

### 5. Chess and Pokémon Showdown

These add multi-turn strategy while retaining exact rules and legal moves. Chess already has conventional Elo anchors. Pokémon Showdown contributes hidden information, team matchups, stochastic outcomes, and a strong reproducibility pattern: fixed fixtures, swapped sides, saved decisions, source fingerprints, and replay verification.

### 6. Doom or Jev's Fly

These add continuous state and short control macros. Use one fixed map/seed and publish both task reward and control failures. Doom should use Freedoom assets. Jev's Fly needs licensing permission or a small replacement environment.

### 7. Long-horizon capstones

Pokémon Red, Slay the Spire 2, Minecraft, and the WoW leveling agent belong in milestone-based tracks. Full completion is too sparse by itself. Define intermediate milestones before evaluating models and preserve checkpoints only for recovery from infrastructure failure, unless checkpoint branching is the task being measured.

## Benchmark protocol

### Environment adapter

Every game adapter should implement the same conceptual interface:

```text
reset(seed, difficulty) -> Observation
legal_actions()         -> Action[]
step(action)            -> Transition
result()                -> EpisodeResult
replay(action_log)      -> EpisodeResult
```

`Observation` contains only information allowed by the task. `Action` has a stable identifier and a plain-language description. `Transition` records reward/progress, terminal state, and engine events. `EpisodeResult` contains raw game metrics; the runner adds model latency, token, cost, timeout, and validity data.

The adapter, not the model client, owns legality checks, state transitions, seed handling, and terminal conditions.

### Model adapter

Use one `ModelDriver` interface for Jev and chat/reasoning models:

```text
decide(observation, legal_actions, deadline_ms) -> Decision
```

All models receive the same semantic state and legal options. Jev can receive a native typed `Choice`; chat models receive a constrained JSON schema containing the same option identifiers. Score only the selected action. Treat probabilities, log probabilities, and model-reported confidence as optional diagnostics because providers expose them differently.

An invalid response counts as an invalid action. Do not silently substitute a heuristic. If an environment needs a fallback to keep running, record the fallback and exclude the episode from pure model-play claims or score it under a published penalty.

### Tracks

Publish separate tables for:

| Track | What it measures | Candidate games |
|---|---|---|
| Discrete decision quality | Strategy when the game waits | Minesweeper, Tetris lockstep, chess, Pokémon Showdown, Puyo Puyo |
| Real-time play | Decision quality under deadlines | Pong, Tetris gravity, Doom, Jev's Fly, endless runner |
| Long-horizon play | Memory, exploration, recovery, and planning | Wikiracing, Pokémon Red, Slay the Spire 2, Minecraft, WoW |
| Control and simulation | System-level outcomes across many decisions | Traffic, evacuation |
| Coaching and judgment | Agreement with engine truth or labels | game-coach, Kiru Hai Coach |
| Creative steering | Validity and human preference, not game skill | Piano and level generation projects |

### Run record

Write one append-only JSONL record per decision and one summary record per episode. At minimum, record:

```text
benchmark_version, game_id, adapter_commit, engine_version
model_provider, model_id, model_release, model_parameters
seed, difficulty, episode_id, step
observation_hash, legal_action_ids, selected_action_id
valid, timed_out, fallback_used
latency_ms, input_tokens, output_tokens, estimated_cost
raw_game_score, success, terminal_reason
```

Store the full observation and raw response in a separate artifact when provider policy and dataset size allow it. Hashes alone are insufficient for audit or replay.

## Scoring

Do not collapse the first release to one number. A leaderboard matrix is more informative:

```text
model × game = outcome, success rate, p50/p95 latency,
               invalid rate, deadline-miss rate, tokens, cost
```

For a later cross-game score, normalize each game's primary metric against two published anchors:

```text
normalized_skill = (model_score - random_score) / (reference_score - random_score)
```

Use a fixed scripted or search-based reference policy. Preserve values above 1 when a model beats the reference. Report bootstrap confidence intervals over seeds or matchups. Show the raw score beside the normalized score so the normalization cannot hide task-specific behavior.

The aggregate should be a mean of per-game normalized scores only within a track. A single overall rank across chess, traffic control, music, and Minecraft would combine unlike tasks and reward the chosen weights more than model capability.

## Fairness and reproducibility rules

1. Freeze engine, adapter, prompt, option descriptions, model version, and test seeds for a leaderboard release.
2. Keep development seeds public and final evaluation seeds hidden until submission. Rotate the hidden set in versioned releases.
3. Run enough seeds to report uncertainty. Repeat identical states when model nondeterminism matters.
4. Swap sides, teams, colors, and starting orientations where applicable.
5. Give every model the same state fields and action granularity. A model choosing `go_to_village` is not directly comparable with one choosing every key press.
6. Report helper systems such as pathfinding, search, planners, checkpoint branching, hand-authored routes, and safety overrides.
7. Separate model failures from provider failures and harness failures. Publish counts for all three.
8. Measure end-to-end wall-clock latency at the runner, including serialization and network time.
9. Enforce episode budgets for calls, tokens, cost, and elapsed time.
10. Replay every saved action sequence and verify that the terminal result matches the original run.

## Packaging and licensing

Use a central runner with thin adapters and a source lockfile:

```text
benchmark/
  games/<game-id>/manifest.yaml
  games/<game-id>/adapter.{py,ts}
  games/<game-id>/tests/
  models/<provider>.{py,ts}
  runner/
  schemas/
  seed-packs/
  results/
  sources.lock
```

`sources.lock` should record repository URL, commit, license, engine/data downloads, and checksums.

The permissively licensed starting points are Jev Pong (Apache-2.0), typesafe-jev-dojo (MIT), jev-plays-pokemon (MIT, but the ROM is external), beat-jev (MIT), jev-piano (MIT), PuyoAI (mostly MIT), Mario Never Dies (Apache-2.0), and game-coach (GPL-3.0, which imposes distribution conditions). TypeEvacSafe is noncommercial. Many otherwise attractive repositories have no license file; public source is not permission to copy or redistribute it. Obtain permission, depend on it as an optional external checkout, or write a small independent engine.

Commercial game binaries and assets should never be included. Require users to supply owned ROMs/games for Mario, Pokémon Red, Slay the Spire 2, Smash Bros., Minecraft, and WoW. Prefer open replacements such as Freedoom when the task does not depend on the original assets.

## Proposed releases

### Release 0: benchmark kernel

- Define the environment, model, decision-log, and episode-result schemas.
- Implement Jev and OpenAI-compatible model drivers.
- Add deterministic replay, budgets, resume behavior, and a result validator.
- Add random and scripted reference policies before model evaluation.

### Release 1: small deterministic games

- Minesweeper: independently implemented seeded engine.
- Tetris: adapter around the MIT Dojo engine.
- Pong: adapter around the Apache-2.0 repository.
- Snake: deterministic engine adapted from `iammusham/jev-snake`.
- Publish lockstep and real-time tables, raw logs, and confidence intervals.

### Release 2: strategic games

- Chess against fixed engine levels.
- Pokémon Showdown with fixed teams and swapped orientations.
- Puyo Puyo if the engine integration is tractable.

### Release 3: continuous and long-horizon tasks

- Doom/Freedoom or a small original continuous-control game.
- Wikiracing against a pinned snapshot.
- Pokémon Red and Slay the Spire 2 milestone suites.
- Minecraft as an explicitly assisted capstone.

Traffic, evacuation, coaching, and creative tasks should become sibling suites that reuse the runner and logging format without contributing to the core game-playing score.

## The first concrete build

Start with Minesweeper, Tetris, Pong, and Snake. Together they test inference over hidden hazards, multi-step spatial planning, real-time reaction, and short-horizon navigation with self-collision. They run headlessly, have objective outcomes, support seeded episodes, and span both lockstep and deadline-sensitive play. This group is small enough to make the runner and scoring rules correct before emulator setup and long-horizon state management dominate the work.
