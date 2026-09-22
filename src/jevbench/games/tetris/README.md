# Tetris environment

NARCADE's Tetris environment is a seeded, headless control loop. On every nonterminal tick the
model receives exactly six player inputs: `LEFT`, `RIGHT`, `ROTATE`, `SOFT_DROP`, `HARD_DROP`,
and `NONE`. The engine owns the active piece, gravity, blocked-input behavior, collision detection,
locking, line clearing, scoring, the seven-bag piece stream, and top-out.

The model sees the settled board, active piece, next piece, score, and line count. Action labels do
not contain simulated placements or derived hints such as resulting height, holes, bumpiness, or
line clears. Those calculations remain private to the optional heuristic baseline.

Real-time mode is the leaderboard track. Gravity continues while the model answers; an answer for
a piece that locked during inference is discarded instead of being applied to the newly spawned
piece. Easy, medium, and hard use 500, 250, and 100 millisecond control/gravity intervals.
Lockstep advances one gravity tick after each player input and is available as an action-quality
diagnostic.

Normal episodes have no time, piece, or model-call limit and finish only when the engine records a
top-out. Operators may explicitly set `--max-seconds`, `--max-pieces`, or `--max-decisions` for
debugging or cost control; those runs are diagnostic and their terminal reasons identify the cap.
