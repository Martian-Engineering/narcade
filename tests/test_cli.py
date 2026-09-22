from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout

from jevbench.cli import main


class CliTests(unittest.TestCase):
    def test_compare_runs_same_seed_pack_for_multiple_policies(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(
                [
                    "compare",
                    "minesweeper",
                    "--models",
                    "random,heuristic",
                    "--episodes",
                    "2",
                    "--seed",
                    "40",
                    "--max-decisions",
                    "2",
                    "--record-decisions",
                ]
            )
        result = json.loads(output.getvalue())

        self.assertEqual(result["models"], ["random", "heuristic"])
        for policy in result["results"].values():
            self.assertEqual([episode["seed"] for episode in policy["episodes"]], [40, 41])
        random_actions = result["results"]["random"]["episodes"][0]["decision_log"][0][
            "presented_action_ids"
        ]
        heuristic_actions = result["results"]["heuristic"]["episodes"][0]["decision_log"][0][
            "presented_action_ids"
        ]
        self.assertEqual(random_actions, heuristic_actions)


if __name__ == "__main__":
    unittest.main()
