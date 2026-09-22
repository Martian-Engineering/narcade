from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from jevbench.publication import compare, summarize


def result(policy="jev"):
    return {
        "status": "completed",
        "game": "snake",
        "policy": policy,
        "benchmark_version": "0.5.0",
        "policy_metadata": {"requested_model": "test"},
        "configuration": {
            "rules_version": "0.4.0",
            "mode": "lockstep",
            "difficulty": "medium",
            "max_decisions": 10,
        },
        "episodes": [{"seed": 1, "score": 2, "success": False}],
        "aggregate": {
            "mean_score": 2,
            "min_score": 2,
            "max_score": 2,
            "success_rate": 0,
            "invalid_actions": 0,
            "timeouts": 0,
            "policy_errors": 0,
        },
    }


class PublicationTests(unittest.TestCase):
    def publish(self, payloads):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for i, payload in enumerate(payloads):
                path = Path(directory) / f"{i}.json"
                path.write_text(json.dumps(payload))
                paths.append(path)
            return summarize(paths, "test")

    def test_rejects_mixed_protocols_duplicate_rows_and_failed_runs(self):
        a = result()
        for field, value in (("benchmark_version", "0.4.0"), ("status", "failed")):
            b = result("kev")
            b[field] = value
            with self.assertRaises(ValueError):
                self.publish([a, b])
        with self.assertRaises(ValueError):
            self.publish([a, a])
        b = result("kev")
        b["aggregate"]["invalid_actions"] = 1
        with self.assertRaises(ValueError):
            self.publish([a, b])

    def test_comparison_pairs_seeds_and_reports_zero_baseline_without_percent(self):
        before = self.publish([result()])
        after = copy.deepcopy(before)
        after["records"][0]["episodes"][0]["score"] = 5
        after["records"][0]["protocol"]["version"] = "0.6.0"
        delta = compare(before, after)[0]
        self.assertEqual(delta["score_delta"], 3)
        self.assertEqual(delta["percent_change"], 150)
        before["records"][0]["episodes"][0]["score"] = 0
        self.assertIsNone(compare(before, after)[0]["percent_change"])
        after["records"][0]["protocol"]["mode"] = "realtime"
        with self.assertRaisesRegex(ValueError, "mode"):
            compare(before, after)

    def test_comparison_rejects_changed_rules_even_with_matching_caps(self):
        before = self.publish([result()])
        after = copy.deepcopy(before)
        after["records"][0]["protocol"]["version"] = "0.6.0"
        after["records"][0]["protocol"]["rules_version"] = "0.6.0"
        with self.assertRaisesRegex(ValueError, "rules_version"):
            compare(before, after)

    def test_comparison_rejects_changed_seeds_or_model(self):
        before = self.publish([result()])
        for field in ("seed", "model"):
            after = copy.deepcopy(before)
            if field == "seed":
                after["records"][0]["episodes"][0]["seed"] = 2
            else:
                after["records"][0]["model"]["requested_model"] = "different"
            with self.assertRaises(ValueError):
                compare(before, after)
