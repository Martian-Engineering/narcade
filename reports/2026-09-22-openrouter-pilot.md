# OpenRouter pilot: action quality and latency

On September 22, 2026, we tested GPT-6 Luna, GPT-6 Sol, and Claude Sonnet 5 at low and medium reasoning through OpenRouter. All six configurations ate more Snake food than Jev on seed 100; Sol medium also solved Minesweeper. Responses were much slower than Jev. These are single-seed diagnostics, not a replacement for the three-seed leaderboard or evidence of realtime performance. [Structured results](openrouter-pilot-20260922.json) include every attempted episode and the matching Jev baseline.

## Scores and latency

Latency columns show **p50 / p95 in seconds per decision**, including reasoning and request overhead. Snake scores count food; Minesweeper scores count safe squares, including 56 squares from the automatic opening on this seed. Equal percentiles for a one-call episode do not describe a latency distribution.

| Model | Snake score | Snake latency (s) | Minesweeper score | Minesweeper latency (s) |
| --- | ---: | ---: | ---: | ---: |
| Jev 1.13.0 | 1 | 0.339 / 0.520 | 56 | 0.330 / 0.330 |
| GPT-6 Luna, low | 28 | 1.481 / 2.431 | 60 | 6.888 / 9.499 |
| GPT-6 Luna, medium | 37, decision cap | 2.172 / 4.356 | 62 | 16.165 / 37.712 |
| GPT-6 Sol, low | 22 | 1.317 / 2.102 | 65 | 4.680 / 7.480 |
| GPT-6 Sol, medium | 38, budget-stopped | 1.906 / 3.780 | 73, solved | 7.782 / 17.588 |
| Claude Sonnet 5, low | 12 | 1.993 / 5.276 | 56 | 7.930 / 7.930 |
| Claude Sonnet 5, medium | 7 | 2.076 / 5.453 | Failed, no action | 37.542 / 37.542 |

Luna medium Snake reached 500 decisions without a collision; Sol medium stopped at 492 decisions because its budget allocation could not cover another maximum-cost request. Neither is a game victory. Other Snake episodes ended in collisions. All Minesweeper episodes except Sol medium and the failed Claude medium request ended on a mine. Claude medium exhausted its 4,096-token completion allowance on reasoning and returned no action; the initial board score is not credited as model performance.

Two Tetris episodes were attempted before the user requested skipping remaining Tetris work. Luna low topped out with 0 points after 94 decisions (latency 4.743 / 7.750 seconds). Sol low cleared one line for 40 points, then was budget-stopped after 110 decisions (5.541 / 10.572 seconds). Jev seed 100 topped out with 0 points after 20 decisions (0.351 / 0.396 seconds). Unattempted configurations are not zero scores.

## Protocol, costs, and limits

The pilot used protocol 0.5.0, rules 0.4.0, medium difficulty, seed 100, lockstep timing, a 500-decision cap, and a 200-piece Tetris cap. Each request received the existing game state, instructions, and legal action descriptions in the same deterministic presentation order as Jev. A system instruction required exactly one action ID. Requests had no conversation history, external planner, tools, or repair calls. Requested reasoning effort was low or medium with a 4,096-token completion cap including reasoning. This compares interfaces and requested effort settings, not equivalent internal compute across providers.

Initial low-effort requests ran serially. The remaining Snake and Minesweeper work resumed with up to four concurrent workers. Claude-low Snake's 50-decision prefix was validated and replayed without new API calls, retaining its original measured latencies. Its latency distribution therefore combines both phases; medium-effort runs used the concurrent phase. Concurrency, provider routing, and different collection times limit latency comparisons. Lockstep freezes the game while awaiting a response, so higher scores do not establish that these models can sustain realtime play.

Reported per-call charges totaled **$1.944789**, with **$0.053705** still reserved for an uncertain interrupted request: **$1.998494** conservatively accounted for, below the $5 authorization. This is ledger accounting, not a final invoice. The runner used a $4.75 ceiling and divided it into six model/effort allocations, so individual configurations could stop before the overall budget was exhausted. Earlier Tetris spend remained charged to its configuration. Raw request IDs, account usage metadata, credentials, and the private spending ledger are not published.

## Reproduce a new run

This starts paid requests; the hidden prompt accepts the key without putting it in command arguments. Use a fresh output directory. Available model IDs and pricing may change.

```sh
uv run python scripts/run_openrouter.py \
  --output-dir results/openrouter-new --budget 4.75 \
  --workers 4 --games minesweeper snake
```

The historical run included initial Tetris work and an interruption, so this command reproduces the game settings, not its exact spend or scheduling history. Raw outputs remain ignored by Git. The public JSON contains allowlisted aggregate fields only; latency values for incomplete episodes summarize the requests that actually ran.
