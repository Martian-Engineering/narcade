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
        probability = 1 / len(actions)
        return PolicyDecision(
            self._rng.choice(actions).id,
            probabilities={action.id: probability for action in actions},
            confidence=probability,
        )

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
        return PolicyDecision(
            action_id,
            probabilities={action.id: float(action.id == action_id) for action in actions},
            confidence=1.0,
        )

    def metadata(self) -> dict[str, str]:
        return {"kind": "baseline", "name": self.name}
