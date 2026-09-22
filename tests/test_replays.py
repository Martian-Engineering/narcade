import copy
import unittest

from jevbench.config import RunConfig
from jevbench.policies import RandomPolicy
from jevbench.registry import create_game
from jevbench.runner import run_benchmark
from scripts.export_replays import reconstruct


class ReplayTests(unittest.TestCase):
    def recording(self):
        trace = []
        options = RunConfig(mode="lockstep").game_options("snake")
        payload = run_benchmark(
            lambda seed: create_game("snake", seed=seed, **options),
            RandomPolicy,
            game_id="snake",
            policy_name="random",
            first_seed=100,
            episodes=1,
            max_decisions=5,
            trace=trace.append,
        )
        payload.update(status="completed", configuration=options)
        return payload, payload["episodes"][0], trace

    def test_reconstructs_terminal_frame(self):
        payload, episode, trace = self.recording()
        replay = reconstruct(payload, episode, trace)
        self.assertEqual(len(replay["frames"]), episode["decisions"] + 1)
        self.assertIsNone(replay["frames"][-1]["action"])
        self.assertEqual(replay["score"], episode["score"])

    def test_rejects_mismatched_state_and_missing_decision(self):
        payload, episode, trace = self.recording()
        bad = copy.deepcopy(trace)
        bad[0]["state"]["direction"] = "invalid"
        with self.assertRaises(ValueError):
            reconstruct(payload, episode, bad)
        with self.assertRaises(ValueError):
            reconstruct(payload, episode, trace[:-1])

    def test_rejects_mismatched_final_score(self):
        payload, episode, trace = self.recording()
        episode["score"] += 1
        with self.assertRaises(ValueError):
            reconstruct(payload, episode, trace)
