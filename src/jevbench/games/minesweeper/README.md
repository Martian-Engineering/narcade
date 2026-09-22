# Minesweeper environment

The environment uses a seeded 9 by 9 board and automatically reveals the center square. The 3 by 3 area around the center contains no mines, which gives every policy the same informative opening.

Difficulty controls the mine count: easy has 6, medium has 8, and hard has 10. The primary score is the number of safe squares revealed before a mine is hit or the board is cleared. The maximum score is `81 - mine_count`.

Each action reveals one covered coordinate. The model sees only the visible board, mine count, and score.
