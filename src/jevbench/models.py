from __future__ import annotations

from dataclasses import dataclass


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
        artifact_revision="ec4ff3df205028f4e81c954c2227f9312b3ec2ea",
    ),
    "kev": SystemOneModel(
        name="kev",
        base_url="http://127.0.0.1:8009",
        model="kev-latest",
        api_key="local",
        artifact="jaredpalmer/kev-4b",
        artifact_revision="485ace8703592fcf405488b262449990824cfed1",
        runtime="kev",
        runtime_revision="5e94a28818cfd3d0ec9b8bca046dc8db0d79a704",
        quantization="bf16",
        training_exposure=(
            "No exposure to the benchmark's exact Minesweeper, Tetris, Pong, or Snake "
            "environments declared in the Kev-4B model card"
        ),
    ),
    "laya": SystemOneModel(
        name="laya",
        base_url="",
        model="laya-0.3.5",
        artifact="convaiinnovations/laya",
        artifact_revision="1c5edc17a7acd8701df6fc341c0d179f1c62c982",
        runtime="laya",
        runtime_revision="0.3.5",
        training_exposure="No benchmark-game exposure declared",
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
    "laya-multilingual": SystemOneModel(
        name="laya-multilingual",
        base_url="",
        model="laya-multilingual-0.3.5",
        artifact="convaiinnovations/laya-multilingual",
        artifact_revision="052592a15d198d9ad47da779604259b10b47b7aa",
        runtime="laya",
        runtime_revision="0.3.5",
        quantization="fp32",
        training_exposure="No benchmark-game exposure declared",
    ),
}
