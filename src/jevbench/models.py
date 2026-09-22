from __future__ import annotations

import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SystemOneModel:
    name: str
    base_url: str
    model: str
    api_key_env: str | None = None
    api_key: str | None = None
    artifact: str | None = None
    artifact_revision: str | None = None
    runtime: str | None = None
    runtime_revision: str | None = None
    container_digest: str | None = None
    quantization: str | None = None
    hardware: str | None = None
    training_exposure: str | None = None

    @property
    def endpoint(self) -> str:
        return f"{self.base_url.rstrip('/')}/v1/systemone"


DEFAULT_MODELS = {
    "jev": SystemOneModel(
        name="jev",
        base_url="https://api.typesafe.ai",
        model="jev-1.13.0",
        api_key_env="TYPESAFE_API_KEY",
    ),
    "openjev": SystemOneModel(
        name="openjev",
        base_url="https://api.codiv.ai",
        model="openjev-0.1",
        api_key_env="CODIV_API_KEY",
        artifact="nvidia/diffusiongemma-26B-A4B-it-NVFP4",
    ),
    "kev": SystemOneModel(
        name="kev",
        base_url="http://127.0.0.1:8009",
        model="kev-latest",
        api_key="local",
        artifact="jaredpalmer/kev-4b",
    ),
    "laya": SystemOneModel(
        name="laya",
        base_url="",
        model="laya-0.3.5",
        artifact="convaiinnovations/laya",
        artifact_revision="1c5edc17a7acd8701df6fc341c0d179f1c62c982",
        runtime="laya",
        runtime_revision="0.3.5",
        training_exposure="No Minesweeper, Tetris, or Pong exposure declared",
    ),
    "laya-typed": SystemOneModel(
        name="laya-typed",
        base_url="",
        model="laya-typed-decisions-0.3.5",
        artifact="convaiinnovations/laya-typed-decisions",
        artifact_revision="f9ab0b228f0fc0f14d873dbc99038f135c2da1b2",
        runtime="laya",
        runtime_revision="0.3.5",
        training_exposure=(
            "Fine-tuned on the typed-decisions training split; no game exposure declared"
        ),
    ),
}


def load_models(path: Path | None = None) -> dict[str, SystemOneModel]:
    models = dict(DEFAULT_MODELS)
    if path is None:
        return models
    parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    entries = parsed.get("models")
    if not isinstance(entries, dict):
        raise ValueError(f"{path} must contain a [models.<name>] table")
    for name, values in entries.items():
        if not isinstance(values, dict):
            raise ValueError(f"models.{name} must be a table")
        base = models.get(name)
        models[name] = _model_from_mapping(name, values, base)
    return models


def _model_from_mapping(
    name: str,
    values: dict[str, Any],
    base: SystemOneModel | None,
) -> SystemOneModel:
    allowed = {
        "base_url",
        "model",
        "api_key_env",
        "api_key",
        "artifact",
        "artifact_revision",
        "runtime",
        "runtime_revision",
        "container_digest",
        "quantization",
        "hardware",
        "training_exposure",
    }
    unknown = set(values) - allowed
    if unknown:
        raise ValueError(f"models.{name} has unknown fields: {', '.join(sorted(unknown))}")
    if base is None:
        missing = {"base_url", "model"} - set(values)
        if missing:
            raise ValueError(f"models.{name} is missing: {', '.join(sorted(missing))}")
        base = SystemOneModel(name=name, base_url="", model="")
    for key, value in values.items():
        if value is not None and not isinstance(value, str):
            raise ValueError(f"models.{name}.{key} must be a string")
    return replace(base, name=name, **values)
