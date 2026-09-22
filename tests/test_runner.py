from __future__ import annotations

import unittest
from unittest.mock import patch

from jevbench.core import Action, Observation, PolicyDecision, PolicyTimeout
from jevbench.games.minesweeper import Minesweeper
from jevbench.games.pong import Pong
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


class RunnerTests(unittest.TestCase):
    def test_invalid_action_terminates_and_is_reported(self) -> None:
        result = run_episode(
            Minesweeper(1),
            InvalidPolicy(),
            seed=1,
            max_decisions=10,
            record_decisions=True,
        )
        self.assertEqual(result["terminal_reason"], "invalid_action")
        self.assertEqual(result["invalid_actions"], 1)
        self.assertFalse(result["success"])
        self.assertEqual(len(result["decision_log"]), 1)
        self.assertFalse(result["decision_log"][0]["valid"])
        self.assertEqual(result["decision_log"][0]["selected_action_id"], "not_legal")

    @patch("jevbench.runner.time.perf_counter", side_effect=[10.0, 13.5])
    def test_realtime_timeout_advances_game_by_wait_duration(self, perf_counter) -> None:
        del perf_counter
        result = run_episode(
            Pong(1, difficulty="easy", mode="realtime"),
            TimeoutPolicy(),
            seed=1,
            max_decisions=10,
        )

        self.assertEqual(result["terminal_reason"], "policy_timeout")
        self.assertEqual(result["timeouts"], 1)
        self.assertAlmostEqual(result["simulated_seconds"], 3.5)

    @patch("jevbench.runner.time.perf_counter", side_effect=[10.0, 10.2])
    def test_invalid_response_is_counted_when_latency_ends_match(self, perf_counter) -> None:
        del perf_counter
        result = run_episode(
            Pong(1, difficulty="easy", mode="realtime", max_seconds=0.1),
            InvalidPolicy(),
            seed=1,
            max_decisions=10,
            record_decisions=True,
        )

        self.assertEqual(result["terminal_reason"], "time_limit")
        self.assertEqual(result["invalid_actions"], 1)
        self.assertFalse(result["decision_log"][0]["valid"])

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
