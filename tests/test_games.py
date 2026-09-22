from __future__ import annotations

import unittest

from jevbench.games.minesweeper import Minesweeper
from jevbench.games.pong import Pong
from jevbench.games.snake import Snake
from jevbench.games.tetris import Tetris
from jevbench.games.tetris.environment import SHAPES


class MinesweeperTests(unittest.TestCase):
    def test_seed_reproduces_board_and_opening(self) -> None:
        first = Minesweeper(42, "hard")
        second = Minesweeper(42, "hard")
        self.assertEqual(first.observation(), second.observation())
        self.assertGreater(first.safe_revealed, 0)
        self.assertNotIn("*", first.observation().state["board"])

    def test_heuristic_episode_has_bounded_score(self) -> None:
        game = Minesweeper(3, "medium")
        while not game.done:
            game.step(game.heuristic_action_id())
        result = game.result()
        self.assertGreaterEqual(result["score"], 1)
        self.assertLessEqual(result["score"], result["score_max"])


class TetrisTests(unittest.TestCase):
    def test_l_piece_rotations_preserve_handedness(self) -> None:
        self.assertEqual(SHAPES["L"][1], ((0, 0), (1, 0), (2, 0), (2, 1)))
        self.assertEqual(SHAPES["L"][3], ((0, 0), (0, 1), (1, 1), (2, 1)))

    def test_difficulty_sets_realtime_deadline(self) -> None:
        self.assertEqual(Tetris(7, difficulty="easy").decision_deadline_seconds, 0.5)
        self.assertEqual(Tetris(7, difficulty="medium").decision_deadline_seconds, 0.25)
        self.assertEqual(Tetris(7, difficulty="hard").decision_deadline_seconds, 0.1)

    def test_every_tick_offers_only_fixed_player_controls(self) -> None:
        game = Tetris(7)

        self.assertEqual(
            {action.id for action in game.legal_actions()},
            {"LEFT", "RIGHT", "ROTATE", "SOFT_DROP", "HARD_DROP", "NONE"},
        )
        descriptions = " ".join(action.description.lower() for action in game.legal_actions())
        for derived_metric in ("clears", "height", "holes", "bumpiness"):
            self.assertNotIn(derived_metric, descriptions)

    def test_seed_reproduces_piece_stream_and_control_episode(self) -> None:
        first = Tetris(7, piece_limit=20)
        second = Tetris(7, piece_limit=20)
        for _ in range(50):
            self.assertEqual(first.observation(), second.observation())
            self.assertEqual(first.legal_actions(), second.legal_actions())
            action = first.heuristic_action_id()
            self.assertEqual(action, second.heuristic_action_id())
            first.step(action)
            second.step(action)
            if first.done:
                break
        self.assertEqual(first.result(), second.result())

    def test_hard_drop_locks_piece_and_spawns_the_next_piece(self) -> None:
        game = Tetris(1)
        first_piece = game.current

        game.step("HARD_DROP")

        self.assertEqual(game.pieces, 1)
        self.assertNotEqual(game.current, first_piece)
        self.assertEqual(sum(sum(row) for row in game._board), 4)

    def test_engine_clears_lines_and_scores(self) -> None:
        game = Tetris(1)
        game.current = "I"
        game.rotation = 0
        game.row = 0
        game.column = 6
        game._board[-1][:6] = [1] * 6

        game.step("HARD_DROP")

        self.assertEqual(game.lines, 1)
        self.assertEqual(game.score, 40)
        self.assertEqual(sum(game._board[-1]), 0)

    def test_piece_limit_is_an_explicit_diagnostic_stop(self) -> None:
        game = Tetris(1, piece_limit=1)

        game.step("HARD_DROP")

        result = game.result()
        self.assertEqual(result["terminal_reason"], "diagnostic_piece_limit")
        self.assertFalse(result["success"])
        self.assertEqual(result["pieces"], 1)

    def test_locking_input_consumes_time_and_honors_diagnostic_time_cap(self) -> None:
        game = Tetris(1, mode="lockstep", max_seconds=0.1)

        game.step("HARD_DROP")

        self.assertEqual(game.pieces, 1)
        self.assertAlmostEqual(game.elapsed_seconds, 0.1)
        self.assertEqual(game.result()["terminal_reason"], "diagnostic_time_limit")

    def test_engine_decides_top_out(self) -> None:
        game = Tetris(1)
        game.current = "O"
        game.rotation = 0
        game.row = 18
        game.column = 0
        game.next_piece = "O"
        game._board[0][4:6] = [1, 1]

        game.step("HARD_DROP")

        self.assertTrue(game.done)
        self.assertEqual(game.result()["terminal_reason"], "top_out")

    def test_realtime_answer_before_deadline_applies_control_then_gravity(self) -> None:
        game = Tetris(7, mode="realtime", difficulty="medium")
        original_column = game.column

        game.advance_time(100)
        game.step("LEFT")

        self.assertEqual(game.column, original_column - 1)
        self.assertEqual(game.row, 1)
        self.assertEqual(game.pieces, 0)
        self.assertEqual(game.late_decisions, 0)
        self.assertAlmostEqual(game.elapsed_seconds, 0.25)

    def test_realtime_late_answer_advances_gravity_without_autoplay(self) -> None:
        game = Tetris(7, mode="realtime", difficulty="medium")
        original_column = game.column

        game.advance_time(600)
        game.step("LEFT")

        self.assertEqual(game.column, original_column - 1)
        self.assertEqual(game.row, 3)
        self.assertEqual(game.pieces, 0)
        self.assertEqual(game.late_decisions, 1)
        self.assertEqual(game.missed_ticks, 2)
        self.assertEqual(game.missed_pieces, 0)
        self.assertAlmostEqual(game.elapsed_seconds, 0.75)

    def test_realtime_discards_action_if_observed_piece_locked_during_latency(self) -> None:
        game = Tetris(7, mode="realtime", difficulty="medium")
        game.current = "O"
        game.rotation = 0
        game.row = 18
        game.column = 0

        game.advance_time(300)
        spawned_column = game.column
        game.step("LEFT")

        self.assertEqual(game.pieces, 1)
        self.assertEqual(game.column, spawned_column)
        self.assertEqual(game.row, 1)
        self.assertEqual(game.missed_pieces, 1)


class PongTests(unittest.TestCase):
    def _play(self, seed: int) -> dict[str, object]:
        game = Pong(seed, difficulty="easy", mode="lockstep")
        for _ in range(500):
            if game.done:
                break
            game.step(game.heuristic_action_id())
        return game.result()

    def test_seed_reproduces_match(self) -> None:
        self.assertEqual(self._play(9), self._play(9))

    def test_heuristic_can_score_against_easy_opponent(self) -> None:
        result = self._play(2)
        self.assertGreater(result["agent_points"], 0)
        self.assertIn(result["terminal_reason"], {"target_score", "time_limit"})

    def test_winning_point_does_not_create_an_unplayed_rally(self) -> None:
        game = Pong(1, difficulty="easy", mode="lockstep", target_score=1)
        game.ball_x = -0.02
        game.ball_vx = -0.6
        game._simulate_tick(0.01)
        self.assertTrue(game.done)
        self.assertEqual(game.agent_score, 1)
        self.assertEqual(game.rallies, 1)

    def test_realtime_mode_advances_by_full_model_latency(self) -> None:
        game = Pong(1, difficulty="easy", mode="realtime")
        advanced = []
        game._advance = advanced.append

        game.advance_time(3500)

        self.assertEqual(advanced, [3.5])
        self.assertEqual(game.late_decisions, 1)

    def test_realtime_fast_answer_controls_rest_of_interval(self) -> None:
        game = Pong(1, difficulty="easy", mode="realtime")
        advanced = []
        game._advance = advanced.append

        game.advance_time(30)
        game.step("down")

        self.assertEqual(advanced, [0.03, 0.07])
        self.assertEqual(game.agent_command, "down")

    def test_realtime_mode_stops_at_match_deadline(self) -> None:
        game = Pong(1, difficulty="easy", mode="realtime", max_seconds=120)
        game.elapsed_seconds = 119.995

        game.advance_time(1000)

        self.assertAlmostEqual(game.elapsed_seconds, 120)
        self.assertTrue(game.done)
        self.assertEqual(game.result()["terminal_reason"], "time_limit")


class SnakeTests(unittest.TestCase):
    def test_seed_reproduces_board_and_episode(self) -> None:
        first = Snake(91, "medium")
        second = Snake(91, "medium")
        for _ in range(50):
            self.assertEqual(first.observation(), second.observation())
            action = first.heuristic_action_id()
            self.assertEqual(action, second.heuristic_action_id())
            first.step(action)
            second.step(action)
            if first.done:
                break
        self.assertEqual(first.result(), second.result())

    def test_every_tick_offers_all_four_directions(self) -> None:
        game = Snake(1, "easy")
        while not game.done:
            self.assertEqual(
                {action.id for action in game.legal_actions()},
                {"UP", "DOWN", "LEFT", "RIGHT"},
            )
            game.step("RIGHT")

    def test_engine_ignores_direct_reverse_and_advances_current_heading(self) -> None:
        game = Snake(1, "easy")
        original_head = game.head

        game.step("LEFT")

        self.assertEqual(game.direction.value, "RIGHT")
        self.assertEqual(game.head, (original_head[0] + 1, original_head[1]))

    def test_food_grows_snake_and_scores(self) -> None:
        game = Snake(1, "easy")
        game.food = (game.head[0] + 1, game.head[1])
        game.step("RIGHT")
        self.assertEqual(game.score, 1)
        self.assertEqual(len(game.snake), 4)

    def test_lethal_direction_remains_a_model_choice(self) -> None:
        game = Snake(1, "easy")
        game.snake = [(19, 10), (18, 10), (17, 10)]
        self.assertIn("RIGHT", {action.id for action in game.legal_actions()})
        game.step("RIGHT")
        self.assertTrue(game.done)
        self.assertEqual(game.result()["terminal_reason"], "wall")

    def test_realtime_fast_answer_controls_next_tick(self) -> None:
        game = Snake(1, "easy", mode="realtime")
        game.food = (0, 0)

        game.advance_time(20)
        game.step("UP")

        self.assertEqual(game.head, (10, 9))
        self.assertEqual(game.ticks, 1)
        self.assertEqual(game.missed_ticks, 0)
        self.assertAlmostEqual(game.elapsed_seconds, 1.5)

    def test_realtime_late_answer_keeps_previous_direction_for_missed_ticks(self) -> None:
        game = Snake(1, "hard", mode="realtime")
        game.food = (0, 0)

        game.advance_time(1250)
        game.step("UP")

        self.assertEqual(game.head, (12, 9))
        self.assertEqual(game.ticks, 3)
        self.assertEqual(game.missed_ticks, 2)
        self.assertEqual(game.late_decisions, 1)
        self.assertAlmostEqual(game.elapsed_seconds, 1.5)


if __name__ == "__main__":
    unittest.main()
