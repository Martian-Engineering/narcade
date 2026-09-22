# Snake

NARCADE's Snake environment adapts the pure, deterministic rules engine from
[`iammusham/jev-snake`](https://github.com/iammusham/jev-snake). It runs headlessly on a
20x20 grid and exposes all four absolute directions on every tick. The model is only the player:
the engine applies its choice, ignores a direct reversal under classic Snake rules, handles food
and growth, detects wall/body collisions, and decides when the run ends. The benchmark never
filters dangerous moves or overrides the model's choice with pathfinding.

The primary score is real food eaten. The result also records survival ticks, terminal reason, and
final snake length. Food placement is seeded. Difficulty changes only the real-time clock: easy is
1.5 seconds per tick, medium is 1 second, and hard is 500 milliseconds.

Real-time mode is the leaderboard track. A direction received before the next tick controls that
tick. While an answer is
late, the snake continues in its previous direction for every missed tick; those missed ticks and
late decisions are reported. Neither timing mode ends on a wall-clock deadline; play continues
until the engine records a collision or a filled board. The suite defaults to a 2,000-decision safety cap, adjustable with
`--max-decisions`. A capped run ends with
`decision_limit` and is not a completed Snake episode. Lockstep remains available as an
action-quality diagnostic. Models,
the random baseline, and the deterministic pathfinding baseline receive the same seeds and action
ordering. Because trajectories diverge after a different choice, later states will not necessarily
match across controllers.
