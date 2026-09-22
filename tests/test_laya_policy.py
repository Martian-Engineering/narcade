from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from jevbench.core import Action, Observation
from jevbench.games.minesweeper import Minesweeper
from jevbench.laya_policy import LayaPolicy
from jevbench.models import SystemOneModel


class FakeAgent:
    device = "mps"

    def system_one(self, state, questions):
        assert state == {"board": "#"}
        assert list(questions["action"]["criteria"]) == ["A1", "A2"]
        return {
            "model": "laya-rl-agent",
            "answers": {
                "action": {
                    "choice": "A2",
                    "probabilities": {"A1": 0.25, "A2": 0.75},
                    "confidence": 0.5,
                }
            },
            "usage": {"input_tokens": 42, "output_tokens": 0},
        }


class LayaPolicyTests(unittest.TestCase):
    @patch.dict(sys.modules, {"laya": types.SimpleNamespace(load=lambda checkpoint: FakeAgent())})
    def test_local_runtime_returns_benchmark_decision(self) -> None:
        policy = LayaPolicy(
            SystemOneModel(
                name="laya",
                base_url="",
                model="laya-0.3.5",
                artifact="convaiinnovations/laya",
                runtime="laya",
            )
        )
        decision = policy.decide(
            Minesweeper(1),
            Observation({"board": "#"}, "Pick"),
            [Action("A1", "Reveal A1"), Action("A2", "Reveal A2")],
        )

        self.assertEqual(decision.action_id, "A2")
        self.assertEqual(decision.input_tokens, 42)
        self.assertEqual(policy.metadata()["resolved_model"], "laya-rl-agent")
        self.assertEqual(policy.metadata()["provider"], "laya-local")
        self.assertTrue(policy.metadata()["hardware"].endswith("· mps"))

    def test_pinned_revision_is_resolved_before_loading(self) -> None:
        downloads = []
        loaded = []
        hub = types.SimpleNamespace(
            snapshot_download=lambda **kwargs: downloads.append(kwargs) or "/cache/pinned"
        )
        runtime = types.SimpleNamespace(
            load=lambda checkpoint: loaded.append(checkpoint) or FakeAgent()
        )
        with patch.dict(sys.modules, {"huggingface_hub": hub, "laya": runtime}):
            LayaPolicy(
                SystemOneModel(
                    name="laya",
                    base_url="",
                    model="laya-0.3.5",
                    artifact="convaiinnovations/laya",
                    artifact_revision="abc123",
                    runtime="laya",
                )
            )

        self.assertEqual(downloads[0]["repo_id"], "convaiinnovations/laya")
        self.assertEqual(downloads[0]["revision"], "abc123")
        self.assertEqual(loaded, ["/cache/pinned"])


if __name__ == "__main__":
    unittest.main()
