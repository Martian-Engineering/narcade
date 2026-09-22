from __future__ import annotations

import random

from .core import Action, Game, Observation, PolicyDecision


class RandomPolicy:
    name = "random"

    def __init__(self, seed: int):
        self._rng = random.Random(seed)

    def decide(
        self,
        game: Game,
        observation: Observation,
        actions: list[Action],
    ) -> PolicyDecision:
        del game, observation
        return PolicyDecision(self._rng.choice(actions).id)

    def metadata(self) -> dict[str, str]:
        return {"kind": "baseline", "name": self.name}


class HeuristicPolicy:
    name = "heuristic"

    def decide(
        self,
        game: Game,
        observation: Observation,
        actions: list[Action],
    ) -> PolicyDecision:
        del observation
        action_id = game.heuristic_action_id()
        return PolicyDecision(action_id)

    def metadata(self) -> dict[str, str]:
        return {"kind": "baseline", "name": self.name}
