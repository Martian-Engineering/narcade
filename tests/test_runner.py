from __future__ import annotations

import unittest
from unittest.mock import patch

from jevbench.core import Action, Observation, PolicyDecision, PolicyError, PolicyTimeout
from jevbench.games.minesweeper import Minesweeper
from jevbench.games.snake import Snake
from jevbench.games.tetris import Tetris
from jevbench.policies import HeuristicPolicy
from jevbench.runner import run_benchmark, run_episode


class InvalidPolicy:
    name = "invalid"

    def decide(self, game, observation: Observation, actions: list[Action]) -> PolicyDecision:
        del game, observation, actions
        return PolicyDecision("not_legal")

    def metadata(self) -> dict[str, str]:
        return {"kind": "test", "name": self.name}


class TimeoutPolicy:
    name = "timeout"

    def decide(self, game, observation: Observation, actions: list[Action]) -> PolicyDecision:
        del game, observation, actions
        raise PolicyTimeout("timed out")

    def metadata(self) -> dict[str, str]:
        return {"kind": "test", "name": self.name}


class ErrorPolicy:
    name = "error"

    def decide(self, game, observation: Observation, actions: list[Action]) -> PolicyDecision:
        del game, observation, actions
        raise PolicyError("failed immediately")

    def metadata(self) -> dict[str, str]:
        return {"kind": "test", "name": self.name}


class StraightPolicy:
    name = "straight"

    def decide(self, game, observation: Observation, actions: list[Action]) -> PolicyDecision:
        del game, observation
        assert {action.id for action in actions} == {"UP", "DOWN", "LEFT", "RIGHT"}
        return PolicyDecision("RIGHT")

    def metadata(self) -> dict[str, str]:
        return {"kind": "test", "name": self.name}


class RunnerTests(unittest.TestCase):
    def test_snake_without_decision_cap_runs_until_engine_death(self) -> None:
        result = run_episode(
            Snake(1, mode="lockstep"),
            StraightPolicy(),
            seed=1,
            max_decisions=None,
        )

        self.assertEqual(result["terminal_reason"], "wall")
        self.assertEqual(result["decisions"], 10)

    def test_invalid_action_terminates_and_is_reported(self) -> None:
        records = []
        result = run_episode(
            Minesweeper(1),
            InvalidPolicy(),
            seed=1,
            max_decisions=10,
            trace=records.append,
        )
        self.assertEqual(result["terminal_reason"], "invalid_action")
        self.assertEqual(result["invalid_actions"], 1)
        self.assertFalse(result["success"])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["error"], "invalid_action")
        self.assertEqual(records[0]["selected_action_id"], "not_legal")

    @patch("jevbench.runner.time.perf_counter", side_effect=[10.0, 13.5])
    def test_realtime_timeout_advances_game_by_wait_duration(self, perf_counter) -> None:
        del perf_counter
        result = run_episode(
            Tetris(1, difficulty="easy", mode="realtime"),
            TimeoutPolicy(),
            seed=1,
            max_decisions=10,
        )

        self.assertEqual(result["terminal_reason"], "policy_timeout")
        self.assertEqual(result["timeouts"], 1)
        self.assertAlmostEqual(result["simulated_seconds"], 3.5)

    @patch("jevbench.runner.time.perf_counter", side_effect=[10.0, 10.2])
    def test_engine_terminal_state_wins_when_invalid_response_ends_match(
        self, perf_counter
    ) -> None:
        del perf_counter
        records = []
        result = run_episode(
            Tetris(1, difficulty="easy", mode="realtime", max_seconds=0.1),
            InvalidPolicy(),
            seed=1,
            max_decisions=10,
            trace=records.append,
        )

        self.assertEqual(result["terminal_reason"], "diagnostic_time_limit")
        self.assertEqual(result["invalid_actions"], 1)
        self.assertFalse(result["success"])
        self.assertEqual(records[0]["error"], "invalid_action")

    @patch("jevbench.runner.time.perf_counter", side_effect=[10.0, 40.0])
    def test_engine_collision_wins_when_snake_times_out(self, perf_counter) -> None:
        del perf_counter
        result = run_episode(
            Snake(1, difficulty="hard", mode="realtime"),
            TimeoutPolicy(),
            seed=1,
            max_decisions=None,
        )

        self.assertEqual(result["terminal_reason"], "wall")
        self.assertEqual(result["timeouts"], 1)

    def test_realtime_aggregate_reports_latency_penalties(self) -> None:
        def games(seed: int):
            return Tetris(seed, difficulty="easy", mode="realtime", max_seconds=0.2)

        def policies(seed: int):
            del seed
            return HeuristicPolicy()

        result = run_benchmark(
            games,
            policies,
            game_id="tetris",
            policy_name="heuristic",
            first_seed=1,
            episodes=1,
            max_decisions=10,
        )

        self.assertIn("mean_simulated_seconds", result["aggregate"])
        self.assertIn("late_decision_rate", result["aggregate"])

    @patch("jevbench.runner.time.perf_counter", side_effect=[10.0, 10.0])
    def test_zero_duration_realtime_error_is_reported(self, perf_counter) -> None:
        del perf_counter

        result = run_benchmark(
            lambda seed: Tetris(seed, difficulty="easy", mode="realtime"),
            lambda seed: ErrorPolicy(),
            game_id="tetris",
            policy_name="error",
            first_seed=1,
            episodes=1,
            max_decisions=10,
        )

        self.assertEqual(result["aggregate"]["policy_errors"], 1)
        self.assertEqual(result["episodes"][0]["simulated_seconds"], 0)

    def test_suite_marks_model_call_failure_and_preserves_output(self):
        import json
        import tempfile
        from pathlib import Path

        from jevbench.config import RunConfig
        from jevbench.suite import _run_model

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with (
                patch("jevbench.suite.SystemOnePolicy", return_value=ErrorPolicy()),
                self.assertRaises(SystemExit) as exited,
            ):
                _run_model(
                    RunConfig(models=["jev"], games=["minesweeper"], episodes=1), "jev", output
                )
            self.assertEqual(exited.exception.code, 1)
            result = json.loads((output / "jev-minesweeper.json").read_text())
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["aggregate"]["policy_errors"], 1)

    def test_minesweeper_solve_time_requires_a_clear(self):
        with patch("jevbench.runner.time.monotonic", side_effect=[10, 12]):
            game = Minesweeper(1)
            game._revealed = {(r, c) for r in range(9) for c in range(9)} - game._mines
            result = run_episode(game, HeuristicPolicy(), seed=1, max_decisions=81)
        self.assertEqual(result["solve_seconds"], 2)
        failed = run_episode(Minesweeper(1), InvalidPolicy(), seed=1, max_decisions=1)
        self.assertIsNone(failed["solve_seconds"])

    def test_aggregate_is_reproducible(self) -> None:
        def games(seed: int):
            return Minesweeper(seed, "easy")

        def policies(seed: int):
            del seed
            return HeuristicPolicy()

        first = run_benchmark(
            games,
            policies,
            game_id="minesweeper",
            policy_name="heuristic",
            first_seed=10,
            episodes=3,
            max_decisions=81,
        )
        second = run_benchmark(
            games,
            policies,
            game_id="minesweeper",
            policy_name="heuristic",
            first_seed=10,
            episodes=3,
            max_decisions=81,
        )
        self.assertEqual(
            [episode["score"] for episode in first["episodes"]],
            [episode["score"] for episode in second["episodes"]],
        )


if __name__ == "__main__":
    unittest.main()
