from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from jevbench.config import RunConfig


class HuggingFaceJobTests(unittest.TestCase):
    def test_shared_config_validates_before_launch(self):
        for config in (
            RunConfig(models=["bogus"]),
            RunConfig(episodes=0),
            RunConfig(max_seconds=float("nan")),
            RunConfig(games=["tetris", "tetris"]),
        ):
            with self.assertRaises(ValueError):
                config.validate()
        options = RunConfig(mode="realtime", max_seconds=30, max_pieces=200)
        self.assertEqual(options.game_options("minesweeper")["mode"], "lockstep")
        self.assertIsNone(options.game_options("snake")["max_seconds"])
        self.assertEqual(options.game_options("tetris")["max_seconds"], 30)
        self.assertEqual(options.game_options("tetris")["piece_limit"], 200)

    def test_local_models_send_no_hosted_secrets(self):
        with patch.dict("os.environ", {"TYPESAFE_API_KEY": "private"}, clear=True):
            self.assertEqual(RunConfig(models=["kev"]).secrets(), {})
            self.assertEqual(RunConfig(models=["jev"]).secrets(), {"TYPESAFE_API_KEY": "private"})
            with self.assertRaisesRegex(ValueError, "CODIV_API_KEY"):
                RunConfig(models=["openjev"]).secrets()

    def test_launcher_mounts_shared_config_and_downloads_failed_job_outputs(self):
        mounted = []

        def mount(path, target, **kwargs):
            if target == "/workspace":
                mounted.append(json.loads((path / "config.json").read_text()))
                self.assertTrue((path / "bootstrap_job.sh").exists())
            return types.SimpleNamespace(source="test", path=target.strip("/"))

        hub = types.SimpleNamespace(
            sync_job_volume=Mock(side_effect=mount),
            run_job=Mock(return_value=types.SimpleNamespace(id="job", url="job-url")),
            wait_for_job=Mock(
                return_value=types.SimpleNamespace(status=types.SimpleNamespace(stage="ERROR"))
            ),
            sync_bucket=Mock(),
        )
        with patch.dict(sys.modules, {"huggingface_hub": hub}):
            spec = importlib.util.spec_from_file_location("launcher", Path("scripts/run_hf_job.py"))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(module.subprocess, "run"),
            patch.dict("os.environ", {}, clear=True),
            self.assertRaisesRegex(SystemExit, "ERROR"),
        ):
            module.main(
                [
                    "--models",
                    "kev",
                    "--episodes",
                    "2",
                    "--max-decisions",
                    "7",
                    "--output-dir",
                    directory,
                ]
            )
        self.assertEqual(mounted[0]["max_decisions"], 7)
        self.assertEqual(hub.run_job.call_args.kwargs["secrets"], {})
        hub.sync_bucket.assert_called_once()
