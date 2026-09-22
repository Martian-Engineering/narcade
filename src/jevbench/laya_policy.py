from __future__ import annotations

import importlib
import platform
from typing import Any

from .core import Action, Game, Observation, PolicyDecision, PolicyError
from .models import SystemOneModel


class LayaPolicy:
    """Local adapter for official Laya checkpoints."""

    def __init__(self, config: SystemOneModel):
        self.name = config.name
        self._config = config
        self._resolved_model: str | None = None
        try:
            runtime = importlib.import_module("laya")
        except ModuleNotFoundError as error:
            raise PolicyError(
                "the laya runtime is required; install jev-game-bench[laya]"
            ) from error
        checkpoint = config.artifact or config.model
        if config.artifact_revision:
            try:
                hub = importlib.import_module("huggingface_hub")
                checkpoint = hub.snapshot_download(
                    repo_id=checkpoint,
                    revision=config.artifact_revision,
                    allow_patterns=[
                        "rl_agent_config.json",
                        "model.safetensors",
                        "tokenizer/*",
                        "encoder/*",
                    ],
                )
            except Exception as error:
                raise PolicyError(
                    f"{self.name} could not fetch pinned checkpoint {config.artifact_revision}: "
                    f"{error}"
                ) from error
        try:
            self._agent = runtime.load(checkpoint)
        except Exception as error:
            raise PolicyError(f"{self.name} could not load {checkpoint}: {error}") from error

    @staticmethod
    def validate_runtime() -> None:
        try:
            importlib.import_module("laya")
        except ModuleNotFoundError as error:
            raise PolicyError(
                "the laya runtime is required; install jev-game-bench[laya]"
            ) from error

    def decide(
        self,
        game: Game,
        observation: Observation,
        actions: list[Action],
    ) -> PolicyDecision:
        del game
        if not actions:
            raise PolicyError(f"{self.name} received an empty legal action set")
        questions = {
            "action": {
                "type": "choice",
                "instructions": observation.instructions,
                "criteria": {action.id: action.description for action in actions},
            }
        }
        try:
            body = self._agent.system_one(observation.state, questions)
            answer = body["answers"]["action"]
            action_id = answer["choice"]
        except Exception as error:
            raise PolicyError(f"{self.name} inference failed: {error}") from error
        if not isinstance(action_id, str):
            raise PolicyError(f"{self.name} answers.action.choice must be a string")
        resolved_model = body.get("model")
        if isinstance(resolved_model, str):
            self._resolved_model = resolved_model
        return PolicyDecision(
            action_id=action_id,
            input_tokens=_usage_int(body.get("usage"), "input_tokens"),
            output_tokens=_usage_int(body.get("usage"), "output_tokens"),
            probabilities=_probabilities(answer.get("probabilities")),
            confidence=_optional_unit_float(answer.get("confidence"), "confidence"),
        )

    def metadata(self) -> dict[str, str | None]:
        return {
            "kind": "model",
            "provider": "laya-local",
            "endpoint": None,
            "requested_model": self._config.model,
            "resolved_model": self._resolved_model,
            "artifact": self._config.artifact,
            "artifact_revision": self._config.artifact_revision,
            "runtime": self._config.runtime,
            "runtime_revision": self._config.runtime_revision,
            "container_digest": self._config.container_digest,
            "quantization": self._config.quantization,
            "hardware": self._config.hardware or _runtime_hardware(self._agent),
            "training_exposure": self._config.training_exposure,
        }


def _usage_int(usage: Any, key: str) -> int:
    if not isinstance(usage, dict):
        return 0
    value = usage.get(key, 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PolicyError(f"usage.{key} must be a non-negative integer")
    return value


def _runtime_hardware(agent: Any) -> str:
    device = getattr(agent, "device", "unknown device")
    return f"{platform.system()} {platform.machine()} · {device}"


def _probabilities(value: Any) -> dict[str, float] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or not value:
        raise PolicyError("answers.action.probabilities must be a non-empty object")
    result = {
        key: _unit_float(probability, f"probability for {key!r}")
        for key, probability in value.items()
        if isinstance(key, str)
    }
    if len(result) != len(value):
        raise PolicyError("probability action identifiers must be strings")
    if not any(result.values()):
        raise PolicyError("answers.action.probabilities must contain positive mass")
    return result


def _optional_unit_float(value: Any, field: str) -> float | None:
    if value is None:
        return None
    return _unit_float(value, field)


def _unit_float(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PolicyError(f"{field} must be a number from 0 to 1")
    numeric = float(value)
    if not 0 <= numeric <= 1:
        raise PolicyError(f"{field} must be a number from 0 to 1")
    return numeric
