from __future__ import annotations

import argparse
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


def _load_job_runner() -> ModuleType:
    path = Path(__file__).parents[1] / "hf_space" / "job_runner.py"
    spec = importlib.util.spec_from_file_location("narcade_hf_job_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


job_runner = _load_job_runner()
GAMES = job_runner.GAMES
MODELS = job_runner.MODELS
_csv = job_runner._csv
_run_command = job_runner._run_command
_validate = job_runner._validate
_benchmark_error = job_runner._benchmark_error


def _args(**overrides: object) -> argparse.Namespace:
    values = {
        "episodes": 3,
        "seed": 100,
        "difficulty": "medium",
        "mode": "auto",
        "max_seconds": None,
        "max_pieces": 200,
        "max_decisions": 2_000,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class HuggingFaceJobTests(unittest.TestCase):
    def test_csv_rejects_unknown_and_duplicate_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown models"):
            _csv("jev,nope", choices=MODELS, field="models")
        with self.assertRaisesRegex(ValueError, "duplicates"):
            _csv("jev,jev", choices=MODELS, field="models")

    def test_hosted_lanes_require_job_secrets_before_a_run(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            self.assertRaisesRegex(ValueError, "TYPESAFE_API_KEY, CODIV_API_KEY"),
        ):
            _validate(_args(), ["jev", "openjev"], ["tetris"])

    def test_realtime_suite_rejects_minesweeper(self) -> None:
        with self.assertRaisesRegex(ValueError, "Minesweeper"):
            _validate(_args(mode="realtime"), ["laya"], list(GAMES))

    def test_command_applies_time_cap_only_to_supported_games(self) -> None:
        args = _args(max_seconds=30.0, max_decisions=50)
        with tempfile.TemporaryDirectory() as directory:
            pong = _run_command(
                model="laya",
                game="pong",
                args=args,
                output=Path(directory) / "pong.json",
            )
            snake = _run_command(
                model="laya",
                game="snake",
                args=args,
                output=Path(directory) / "snake.json",
            )
        self.assertIn("--max-seconds", pong)
        self.assertNotIn("--max-seconds", snake)
        self.assertIn("--max-decisions", snake)

    def test_command_applies_piece_cap_only_to_tetris(self) -> None:
        args = _args()
        with tempfile.TemporaryDirectory() as directory:
            tetris = _run_command(
                model="laya",
                game="tetris",
                args=args,
                output=Path(directory) / "tetris.json",
            )
            pong = _run_command(
                model="laya",
                game="pong",
                args=args,
                output=Path(directory) / "pong.json",
            )
        self.assertIn("--max-pieces", tetris)
        self.assertNotIn("--max-pieces", pong)

    def test_model_call_failures_in_result_fail_the_lane(self) -> None:
        self.assertEqual(
            _benchmark_error({"aggregate": {"timeouts": 1, "policy_errors": 2}}),
            "benchmark reported model-call failures: timeouts=1, policy_errors=2",
        )
        self.assertIsNone(_benchmark_error({"aggregate": {"timeouts": 0, "policy_errors": 0}}))


if __name__ == "__main__":
    unittest.main()
