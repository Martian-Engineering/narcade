from __future__ import annotations

import importlib
import os
import platform
from pathlib import Path
from typing import Any

from .core import Action, Game, Observation, PolicyDecision, PolicyError
from .models import SystemOneModel
from .response import parse_decision

CHECKPOINT_PATTERNS = [
    "rl_agent_config.json",
    "model.safetensors",
    "tokenizer/*",
    "encoder/*",
]


def cache_laya_checkpoint(config: SystemOneModel, cache_dir: Path | None = None) -> str:
    """Download a pinned Laya checkpoint and return its local snapshot path."""
    checkpoint = config.artifact or config.model
    try:
        hub = importlib.import_module("huggingface_hub")
        return hub.snapshot_download(
            repo_id=checkpoint,
            revision=config.artifact_revision,
            allow_patterns=CHECKPOINT_PATTERNS,
            cache_dir=str(cache_dir) if cache_dir else None,
        )
    except Exception as error:
        revision = config.artifact_revision or "the default revision"
        raise PolicyError(
            f"{config.name} could not fetch checkpoint {revision}: {error}"
        ) from error


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
            checkpoint = cache_laya_checkpoint(config)
        try:
            self._agent = runtime.load(checkpoint)
        except Exception as error:
            raise PolicyError(f"{self.name} could not load {checkpoint}: {error}") from error

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
        except Exception as error:
            raise PolicyError(f"{self.name} inference failed: {error}") from error
        decision = parse_decision(body)
        resolved_model = body.get("model")
        if isinstance(resolved_model, str):
            self._resolved_model = resolved_model
        return decision

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


def _runtime_hardware(agent: Any) -> str:
    device = getattr(agent, "device", "unknown device")
    accelerator = None
    if getattr(device, "type", None) == "cuda":
        try:
            torch = importlib.import_module("torch")
            accelerator = torch.cuda.get_device_name(device)
        except (AttributeError, RuntimeError):
            pass
    detail = accelerator or str(device)
    flavor = os.environ.get("ACCELERATOR")
    if flavor:
        detail = f"{flavor} · {detail}"
    return f"{platform.system()} {platform.machine()} · {detail}"
