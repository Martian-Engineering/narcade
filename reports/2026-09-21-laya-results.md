# Laya NARCADE Results

On September 21, 2026, we ran the English Laya 0.3.5 checkpoint and the separately labeled `laya-typed-decisions` checkpoint locally on an Apple M3 Pro. Both checkpoints used exact pinned Hugging Face revisions, seeds 100 through 102, medium difficulty, and the same lockstep environments and decision budgets as the initial NARCADE run. All 18 episodes completed with no invalid actions, timeouts, or policy errors. These three-seed results validate the integration and reveal large differences, but they are not a stable ranking.

| Policy | Minesweeper | Tetris | Pong | Mines P50 | Tetris P50 | Pong P50 |
|---|---:|---:|---:|---:|---:|---:|
| Laya | 59.33 | 13.33 | 0.00 | 99.94 ms | 94.73 ms | 57.58 ms |
| Laya Typed | 58.00 | 26.67 | 0.33 | 105.43 ms | 103.57 ms | 58.02 ms |

Base Laya landed between OpenJev and the other learned models on Minesweeper, but the 19-point range from 48 to 67 safe squares makes that ordering highly uncertain. Laya Typed exactly matched the prior random mean of 58.00. Neither checkpoint cleared a board. On Tetris, base Laya averaged 13.33 points and performed below the random policy's 26.67; Laya Typed matched random and topped out after about 26 pieces. By comparison, Jev and OpenJev previously averaged 8,966.67 and 8,033.33 points.

Pong was similarly weak. Base Laya lost all three matches without scoring. Laya Typed scored one point across the three matches for a 0.33 mean, below Jev's 0.67, OpenJev and random at 1.00, and Kev at 2.00. Both Laya checkpoints were faster locally than the previously tested learned models after warm-up, with roughly 58 ms median Pong latency, but lockstep scoring deliberately prevents inference speed from affecting ball motion.

The typed-decisions fine-tune did not establish a generally stronger game policy: it improved Tetris and Pong slightly while scoring lower on Minesweeper. NARCADE should therefore keep base Laya as the primary family entry and show Laya Typed only as an ablation. The Laya runtime also warned that its shipped temperature for choice questions with 11 or more options was outside the accepted range and was clamped, so the recorded confidence values should not be interpreted as calibrated probabilities.
