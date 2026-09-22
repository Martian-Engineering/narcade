from __future__ import annotations

import unittest

from jevbench.games.minesweeper import Minesweeper
from jevbench.games.pong import Pong
from jevbench.games.tetris import Tetris


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
    def test_only_standard_difficulty_is_supported(self) -> None:
        with self.assertRaisesRegex(ValueError, "one ruleset"):
            Tetris(7, difficulty="easy")

    def test_seed_reproduces_piece_stream_and_actions(self) -> None:
        first = Tetris(7, piece_limit=20)
        second = Tetris(7, piece_limit=20)
        for _ in range(10):
            self.assertEqual(first.observation(), second.observation())
            self.assertEqual(first.legal_actions(), second.legal_actions())
            action = first.heuristic_action_id()
            first.step(action)
            second.step(action)
        self.assertEqual(first.result(), second.result())

    def test_piece_limit_is_a_successful_terminal_state(self) -> None:
        game = Tetris(1, piece_limit=25)
        while not game.done:
            game.step(game.heuristic_action_id())
        result = game.result()
        self.assertEqual(result["terminal_reason"], "piece_limit")
        self.assertTrue(result["success"])
        self.assertEqual(result["pieces"], 25)


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

    def test_realtime_mode_stops_at_match_deadline(self) -> None:
        game = Pong(1, difficulty="easy", mode="realtime", max_seconds=120)
        game.elapsed_seconds = 119.995

        game.advance_time(1000)

        self.assertAlmostEqual(game.elapsed_seconds, 120)
        self.assertTrue(game.done)
        self.assertEqual(game.result()["terminal_reason"], "time_limit")


if __name__ == "__main__":
    unittest.main()
