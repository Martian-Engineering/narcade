from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def test_suite_runs_all_engines_and_writes_separate_traces(self):
        with tempfile.TemporaryDirectory() as directory:
            command = [
                sys.executable,
                "-m",
                "jevbench",
                "--models",
                "random,heuristic",
                "--episodes",
                "2",
                "--seed",
                "40",
                "--max-decisions",
                "2",
                "--trace",
                "--output-dir",
                directory,
            ]
            completed = subprocess.run(
                command, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": "src"}
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            output = Path(directory)
            self.assertEqual(
                json.loads((output / "manifest.json").read_text())["status"], "completed"
            )
            for game in ("minesweeper", "tetris", "snake"):
                result = json.loads((output / f"random-{game}.json").read_text())
                self.assertEqual([e["seed"] for e in result["episodes"]], [40, 41])
                self.assertNotIn("decision_log", result["episodes"][0])
                self.assertEqual(
                    result["configuration"]["mode"],
                    "lockstep" if game == "minesweeper" else "realtime",
                )
                traces = [
                    json.loads((output / f"{name}-{game}.jsonl").read_text().splitlines()[0])
                    for name in ("random", "heuristic")
                ]
                self.assertEqual(
                    traces[0]["presented_action_ids"], traces[1]["presented_action_ids"]
                )
            # A repeated invocation cannot mix fresh data with an older run.
            second = subprocess.run(
                command, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": "src"}
            )
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("empty", second.stderr)

    def test_config_file_uses_same_runner(self):
        from dataclasses import asdict

        from jevbench.config import RunConfig

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "output").mkdir()
            (path / "output/.keep").touch()
            config = RunConfig(
                models=["random"], games=["minesweeper"], episodes=1, max_decisions=1
            )
            (path / "config.json").write_text(json.dumps(asdict(config)))
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "jevbench",
                    "--config",
                    str(path / "config.json"),
                    "--output-dir",
                    str(path / "output"),
                ],
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": "src"},
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((path / "output/random-minesweeper.json").exists())
