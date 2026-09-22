from __future__ import annotations

import unittest

from jevbench.models import DEFAULT_MODELS


class ModelConfigTests(unittest.TestCase):
    def test_builtin_models_match_benchmark_lanes(self) -> None:
        models = DEFAULT_MODELS
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


if __name__ == "__main__":
    unittest.main()
