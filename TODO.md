# Benchmark backlog

The first suite covers Minesweeper, Tetris, Pong, and Snake. Add environments in this order after the runner and result schema stabilize.

## Next strategic games

- [ ] Chess using the protocol and scoring design from [maxim-saplin/llm_chess](https://github.com/maxim-saplin/llm_chess). Run both colors against pinned engine levels. Report Elo, win/draw/loss, illegal moves, and decision count.
- [ ] Pokémon Showdown using [izzuddin8803/jev-showdown](https://github.com/izzuddin8803/jev-showdown). Pin teams and simulator revision, swap team orientation, and report win rate, turns, legal-action rate, latency, and tokens.
- [ ] Puyo Puyo using [puyoai/puyoai](https://github.com/puyoai/puyoai). Build the missing Jev adapter and score wins, chains, garbage sent, top-out, and latency.
- [ ] Penalty shootout using [ojusave/beat-jev](https://github.com/ojusave/beat-jev). Replace the human with fixed shooter and keeper policies so both roles can be repeated from seeds.

## Real-time arcade games

- [ ] Doom/Freedoom using [lukaske/jev-doom-agent](https://github.com/lukaske/jev-doom-agent). Fix the map and start state. Report completion, kills, health, survival time, fallback count, and latency.
- [ ] Jev's Fly using [webdevcody/jevs-fly](https://github.com/webdevcody/jevs-fly). Reuse its seeded headless flight tests. Score pop count, crashes, duration, speed, and obstacle clearance.
- [ ] Super Mario Bros. using [fhshaik/typesafe-mario](https://github.com/fhshaik/typesafe-mario). Use headless episodes and report progress, reward, deaths, completion, and latency. Require the operator to supply the ROM.
- [ ] Mario checkpoint branching using [superradcompany/mario-never-dies](https://github.com/superradcompany/mario-never-dies). Keep this separate from single-trajectory Mario. Report progress, deaths, branches consumed, calls, and compute.
- [ ] Endless runner. The catalog's Subway Surfers demo has no confirmed source. [afcodehub/Jev-Subway-Runner-3D](https://github.com/afcodehub/Jev-Subway-Runner-3D) is a related implementation. Prefer a small original runner with distance, survival, coins, and collision scores.
- [ ] Pinned arcade environments such as Breakout, Pac-Man, Space Invaders, and Asteroids. Favor engines with deterministic seeds, direct score access, frame stepping, save states, and no network dependency.

## Long-horizon games

- [ ] Wikiracing from the [TypeSafe launch article](https://typesafe.ai/blog/introducing-system-one-models-and-jev). Run against a pinned Wikipedia snapshot and score completion, clicks, loops, and elapsed decisions.
- [ ] Pokémon Red using [milanboers/jev-plays-pokemon](https://github.com/milanboers/jev-plays-pokemon). Define milestones for leaving home, selecting a starter, reaching towns, earning badges, and completing battles. Label its pathfinding-assisted macro actions.
- [ ] Slay the Spire 2 using [DiscreteTom/jev-sts2](https://github.com/DiscreteTom/jev-sts2) or [alexmeckes/jev-the-spire](https://github.com/alexmeckes/jev-the-spire). Separate recorded-state decision tests from full seeded runs. Score floors, combats, HP, bosses, and run completion.
- [ ] Minecraft using [rmalde/minecraft-agent](https://github.com/rmalde/minecraft-agent). Treat the fixed route, Astra planner, Mineflayer actions, and surveyed seed as part of the task specification. Score verified completion, time, deaths, stages, and calls.
- [ ] WoW leveling using [chalkychalk42/jev](https://github.com/chalkychalk42/jev). Score XP per hour, deaths, interventions, route progress, and cost per XP.

## Separate sibling suites

These tasks can share the runner and result schema but should not contribute to the game-playing aggregate.

- [ ] Traffic control with [skcache/jevtrafficsim](https://github.com/skcache/jevtrafficsim): travel time, delay, stops, queueing, throughput, and failures.
- [ ] Fire evacuation with [using76/TypeEvacSafe](https://github.com/using76/TypeEvacSafe): evacuation, exposure, deaths, rescues, separation, congestion, and decision speed.
- [ ] Chess coaching with [JoelLewis/game-coach](https://github.com/JoelLewis/game-coach): agreement with Stockfish-backed labels, calibration, latency, and cost.
- [ ] Mahjong coaching with [smilior/kiru-hai-coach](https://github.com/smilior/kiru-hai-coach): discard quality against an engine or labeled positions.
- [ ] Music steering with [LamplighterPaul/jev-piano](https://github.com/LamplighterPaul/jev-piano) and [wustep/jev-playground](https://github.com/wustep/jev-playground): rendering validity, style agreement, latency, and human preference.
- [ ] Real-time level generation: solvability, playability, novelty, and generation latency.

## Benchmark infrastructure

- [ ] Add bootstrap confidence intervals over episode seeds.
- [x] Add a comparison command that runs model and baseline policies on the same seed pack.
- [ ] Add versioned public development seeds and private evaluation seeds.
- [ ] Store full observations and raw provider responses in an optional audit artifact.
- [ ] Record the runner commit, Python version, operating system, and host timing metadata automatically. Model release, endpoint, local revision, quantization, hardware, and training exposure are already accepted through `models.toml`.
- [ ] Add OpenAI-compatible constrained-JSON and other provider adapters.
- [ ] Add replay verification for every environment.
- [ ] Add wall-clock and token budgets that can terminate an episode independently of its decision count.
- [ ] Add labeled decision sets for calibration metrics. Sequential game entropy is available now, but calibration needs a defensible action-quality target.
- [ ] Add unseen environment variants for final leaderboard seed packs, including changed board sizes, physics, speeds, and reward schedules.
