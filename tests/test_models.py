from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jevbench.models import load_models


class ModelConfigTests(unittest.TestCase):
    def test_builtin_models_match_benchmark_lanes(self) -> None:
        models = load_models()
        self.assertEqual(models["jev"].model, "jev-1.13.0")
        self.assertEqual(models["openjev"].endpoint, "https://api.codiv.ai/v1/systemone")
        self.assertEqual(models["kev"].endpoint, "http://127.0.0.1:8009/v1/systemone")
        self.assertEqual(models["kev"].runtime, "kev")
        self.assertEqual(
            models["kev"].artifact_revision,
            "485ace8703592fcf405488b262449990824cfed1",
        )
        self.assertEqual(models["laya"].runtime, "laya")
        self.assertIsNone(models["laya"].hardware)
        self.assertIsNone(models["laya"].quantization)
        self.assertEqual(models["laya-typed"].artifact, "convaiinnovations/laya-typed-decisions")
        self.assertEqual(
            models["laya-multilingual"].artifact,
            "convaiinnovations/laya-multilingual",
        )

    def test_toml_can_override_a_builtin_and_add_a_model(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "models.toml"
            path.write_text(
                """
[models.openjev]
base_url = "http://127.0.0.1:8080"
api_key = "local"
artifact_revision = "abc123"
hardware = "test-gpu"

[models.experimental]
base_url = "http://127.0.0.1:9000"
model = "experiment-1"
api_key = "local"
""",
                encoding="utf-8",
            )
            models = load_models(path)

        self.assertEqual(models["openjev"].endpoint, "http://127.0.0.1:8080/v1/systemone")
        self.assertEqual(models["openjev"].model, "openjev-0.1")
        self.assertEqual(models["openjev"].artifact_revision, "abc123")
        self.assertEqual(models["openjev"].hardware, "test-gpu")
        self.assertEqual(models["experimental"].model, "experiment-1")


if __name__ == "__main__":
    unittest.main()
