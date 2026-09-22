# Tetris environment

The environment uses a seeded seven-bag piece stream on a 10 by 20 board. Each decision chooses one legal rotation and hard-drop column. There is no hold piece or preview beyond the next piece.

The primary score uses the classic line-clear table: 40, 100, 300, or 1,200 points for one through four lines, multiplied by the level plus one. The result also reports lines and pieces. Reaching the configured piece limit counts as survival; top-out counts as failure.

The heuristic baseline scores placements by cleared lines, aggregate height, holes, and bumpiness.
