from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from jevbench.core import Action, Observation, PolicyError
from jevbench.games.minesweeper import Minesweeper
from jevbench.models import SystemOneModel
from jevbench.systemone import MAX_RESPONSE_BYTES, SystemOnePolicy


class FakeResponse:
    def __init__(self, body: dict[str, object] | bytes, headers=None):
        self._body = body
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, amount: int = -1) -> bytes:
        if isinstance(self._body, bytes):
            body = self._body
        else:
            body = json.dumps(self._body).encode("utf-8")
        return body if amount < 0 else body[:amount]


class SystemOnePolicyTests(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_choice_and_usage_are_parsed(self, urlopen) -> None:
        urlopen.return_value = FakeResponse(
            {
                "answers": {
                    "action": {
                        "choice": "A1",
                        "confidence": 0.8,
                        "probabilities": {"A1": 0.8, "A2": 0.2},
                    }
                },
                "usage": {"input_tokens": 123, "output_tokens": 0},
                "model": "jev-1.13.0",
            }
        )
        policy = SystemOnePolicy(
            SystemOneModel(
                name="jev",
                base_url="https://api.typesafe.ai",
                model="jev-1.13.0",
                api_key="test-key",
            )
        )
        decision = policy.decide(
            Minesweeper(1),
            Observation({"board": "#"}, "Pick"),
            [Action("A1", "Reveal A1"), Action("A2", "Reveal A2")],
        )
        self.assertEqual(decision.action_id, "A1")
        self.assertEqual(decision.input_tokens, 123)
        self.assertEqual(policy.metadata()["resolved_model"], "jev-1.13.0")
        self.assertEqual(policy.metadata()["endpoint"], "https://api.typesafe.ai/v1/systemone")

        request = urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(payload["model"], "jev-1.13.0")
        self.assertEqual(payload["questions"]["action"]["type"], "choice")
        self.assertEqual(
            list(payload["questions"]["action"]["criteria"]),
            ["A1", "A2"],
        )

    def test_endpoint_metadata_removes_credentials_and_query(self) -> None:
        policy = SystemOnePolicy(
            SystemOneModel(
                name="local",
                base_url="https://user:secret@example.com/path?token=hidden",
                model="test",
                api_key="test-key",
            )
        )
        self.assertEqual(policy.metadata()["endpoint"], "https://example.com/path")

    @patch("urllib.request.urlopen")
    def test_non_finite_provider_metrics_are_rejected(self, urlopen) -> None:
        urlopen.return_value = FakeResponse(
            {
                "answers": {
                    "action": {
                        "choice": "A1",
                        "confidence": float("inf"),
                        "probabilities": {"A1": 1.0},
                    }
                },
                "usage": {"input_tokens": 1, "output_tokens": 0},
            }
        )
        policy = SystemOnePolicy(
            SystemOneModel(
                name="kev",
                base_url="http://127.0.0.1:8009",
                model="kev-latest",
                api_key="local",
            )
        )
        with self.assertRaisesRegex(PolicyError, "unreadable response"):
            policy.decide(
                Minesweeper(1),
                Observation({"board": "#"}, "Pick"),
                [Action("A1", "Reveal A1")],
            )

    @patch("urllib.request.urlopen")
    def test_oversized_provider_integer_is_a_policy_error(self, urlopen) -> None:
        urlopen.return_value = FakeResponse(
            {
                "answers": {"action": {"choice": "A1"}},
                "usage": {"input_tokens": 10**19 - 1, "output_tokens": 0},
            }
        )
        policy = SystemOnePolicy(
            SystemOneModel(
                name="kev",
                base_url="http://127.0.0.1:8009",
                model="kev-latest",
                api_key="local",
            )
        )
        with self.assertRaisesRegex(PolicyError, "input_tokens is too large"):
            policy.decide(
                Minesweeper(1),
                Observation({"board": "#"}, "Pick"),
                [Action("A1", "Reveal A1")],
            )

    @patch("urllib.request.urlopen")
    def test_integer_beyond_decoder_limit_is_a_policy_error(self, urlopen) -> None:
        urlopen.return_value = FakeResponse(
            b'{"answers":{"action":{"choice":"A1"}},"usage":{"input_tokens":'
            + (b"9" * 5000)
            + b',"output_tokens":0}}'
        )
        policy = SystemOnePolicy(
            SystemOneModel(
                name="kev",
                base_url="http://127.0.0.1:8009",
                model="kev-latest",
                api_key="local",
            )
        )
        with self.assertRaisesRegex(PolicyError, "unreadable response"):
            policy.decide(
                Minesweeper(1),
                Observation({"board": "#"}, "Pick"),
                [Action("A1", "Reveal A1")],
            )

    @patch("urllib.request.urlopen")
    def test_oversized_response_is_rejected_before_reading_body(self, urlopen) -> None:
        urlopen.return_value = FakeResponse(
            b"{}",
            headers={"Content-Length": str(MAX_RESPONSE_BYTES + 1)},
        )
        policy = SystemOnePolicy(
            SystemOneModel(
                name="kev",
                base_url="http://127.0.0.1:8009",
                model="kev-latest",
                api_key="local",
            )
        )
        with self.assertRaisesRegex(PolicyError, "response exceeds"):
            policy.decide(
                Minesweeper(1),
                Observation({"board": "#"}, "Pick"),
                [Action("A1", "Reveal A1")],
            )

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_required_environment_key_is_reported(self) -> None:
        with self.assertRaisesRegex(PolicyError, "CODIV_API_KEY"):
            SystemOnePolicy(
                SystemOneModel(
                    name="openjev",
                    base_url="https://api.codiv.ai",
                    model="openjev-0.1",
                    api_key_env="CODIV_API_KEY",
                )
            )


if __name__ == "__main__":
    unittest.main()
