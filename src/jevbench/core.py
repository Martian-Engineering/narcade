from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class Action:
    """One legal action exposed to a policy."""

    id: str
    description: str


@dataclass(frozen=True)
class Observation:
    """The complete model-visible state for one decision."""

    state: dict[str, Any]
    instructions: str


@dataclass(frozen=True)
class PolicyDecision:
    """A policy response plus provider-reported usage."""

    action_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    probabilities: dict[str, float] | None = None
    confidence: float | None = None


class Game(Protocol):
    """Interface implemented by every benchmark game."""

    id: str
    score_name: str

    @property
    def done(self) -> bool: ...

    def observation(self) -> Observation: ...

    def legal_actions(self) -> list[Action]: ...

    def advance_time(self, latency_ms: float) -> None: ...

    def step(self, action_id: str, latency_ms: float = 0.0) -> None: ...

    def heuristic_action_id(self) -> str: ...

    def result(self) -> dict[str, Any]: ...


class Policy(Protocol):
    """A model or baseline that selects one legal action."""

    name: str

    def decide(
        self,
        game: Game,
        observation: Observation,
        actions: list[Action],
    ) -> PolicyDecision: ...

    def metadata(self) -> dict[str, Any]: ...


class PolicyError(RuntimeError):
    """A policy response could not produce a benchmark action."""


class PolicyTimeout(PolicyError):
    """A policy did not answer before its request timeout."""
