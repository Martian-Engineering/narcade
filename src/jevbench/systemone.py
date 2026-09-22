from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .core import Action, Game, Observation, PolicyDecision, PolicyError, PolicyTimeout
from .models import SystemOneModel

MAX_RESPONSE_BYTES = 1024 * 1024


class SystemOnePolicy:
    """System One client shared by Jev, OpenJev, and Kev."""

    def __init__(
        self,
        config: SystemOneModel,
        *,
        timeout_seconds: float = 30.0,
    ):
        api_key = config.api_key or (
            os.environ.get(config.api_key_env, "") if config.api_key_env else ""
        )
        if not api_key:
            key_source = config.api_key_env or "the model configuration"
            raise PolicyError(f"{key_source} is required for the {config.name} policy")
        self.name = config.name
        self._config = config
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._resolved_model: str | None = None

    def decide(
        self,
        game: Game,
        observation: Observation,
        actions: list[Action],
    ) -> PolicyDecision:
        del game
        if not actions:
            raise PolicyError(f"{self.name} received an empty legal action set")

        payload = {
            "model": self._config.model,
            "state": observation.state,
            "questions": {
                "action": {
                    "type": "choice",
                    "instructions": observation.instructions,
                    "criteria": {action.id: action.description for action in actions},
                }
            },
        }
        request = urllib.request.Request(
            self._config.endpoint,
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "User-Agent": "jev-game-bench/0.2",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                body = json.loads(
                    _read_bounded(response),
                    parse_int=_bounded_json_int,
                    parse_float=_finite_json_float,
                    parse_constant=_reject_json_constant,
                )
        except TimeoutError as error:
            raise PolicyTimeout(
                f"{self.name} request timed out after {self._timeout_seconds:g}s"
            ) from error
        except urllib.error.HTTPError as error:
            detail = error.read(501).decode("utf-8", errors="replace")[:500]
            raise PolicyError(
                f"{self.name} request failed with HTTP {error.code}: {detail}"
            ) from error
        except urllib.error.URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise PolicyTimeout(
                    f"{self.name} request timed out after {self._timeout_seconds:g}s"
                ) from error
            raise PolicyError(f"{self.name} request failed: {error.reason}") from error
        except (ValueError, OSError) as error:
            raise PolicyError(f"{self.name} returned an unreadable response: {error}") from error

        try:
            answer = body["answers"]["action"]
            action_id = answer["choice"]
        except (KeyError, TypeError) as error:
            raise PolicyError(f"{self.name} response is missing answers.action.choice") from error
        if not isinstance(action_id, str):
            raise PolicyError(f"{self.name} answers.action.choice must be a string")
        if isinstance(body.get("model"), str):
            self._resolved_model = body["model"]

        usage = body.get("usage") or {}
        probabilities = _probabilities(answer.get("probabilities"))
        confidence = _optional_unit_float(answer.get("confidence"), "confidence")
        return PolicyDecision(
            action_id=action_id,
            input_tokens=_usage_int(usage, "input_tokens", "inputTokens"),
            output_tokens=_usage_int(usage, "output_tokens", "outputTokens"),
            probabilities=probabilities,
            confidence=confidence,
        )

    def metadata(self) -> dict[str, str | None]:
        return {
            "kind": "model",
            "provider": self.name,
            "endpoint": _sanitized_url(self._config.endpoint),
            "requested_model": self._config.model,
            "resolved_model": self._resolved_model,
            "artifact": self._config.artifact,
            "artifact_revision": self._config.artifact_revision,
            "runtime": self._config.runtime,
            "runtime_revision": self._config.runtime_revision,
            "container_digest": self._config.container_digest,
            "quantization": self._config.quantization,
            "hardware": self._config.hardware,
            "training_exposure": self._config.training_exposure,
        }


def _usage_int(usage: Any, snake_key: str, camel_key: str) -> int:
    if not isinstance(usage, dict):
        return 0
    value = usage.get(snake_key, usage.get(camel_key, 0))
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PolicyError(f"usage.{snake_key} must be a non-negative integer")
    if isinstance(value, int):
        if value < 0:
            raise PolicyError(f"usage.{snake_key} must be a non-negative integer")
        if value > 2**63 - 1:
            raise PolicyError(f"usage.{snake_key} is too large")
        return value
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0 or not numeric.is_integer():
        raise PolicyError(f"usage.{snake_key} must be a non-negative integer")
    if numeric > 2**63 - 1:
        raise PolicyError(f"usage.{snake_key} is too large")
    return int(numeric)


def _read_bounded(response: Any) -> bytes:
    headers = getattr(response, "headers", None)
    content_length = headers.get("Content-Length") if headers is not None else None
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except (TypeError, ValueError) as error:
            raise ValueError("invalid Content-Length header") from error
        if declared_length > MAX_RESPONSE_BYTES:
            raise ValueError(f"response exceeds {MAX_RESPONSE_BYTES} bytes")
    body = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError(f"response exceeds {MAX_RESPONSE_BYTES} bytes")
    return body


def _probabilities(value: Any) -> dict[str, float] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or not value:
        raise PolicyError("answers.action.probabilities must be a non-empty object")
    result = {}
    for key, probability in value.items():
        if not isinstance(key, str):
            raise PolicyError("probability action identifiers must be strings")
        result[key] = _unit_float(probability, f"probability for {key!r}")
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
    if isinstance(value, int):
        if not 0 <= value <= 1:
            raise PolicyError(f"{field} must be a number from 0 to 1")
        return float(value)
    numeric = float(value)
    if not math.isfinite(numeric) or not 0 <= numeric <= 1:
        raise PolicyError(f"{field} must be a number from 0 to 1")
    return numeric


def _bounded_json_int(value: str) -> int:
    if len(value.lstrip("-")) > 19:
        raise ValueError("JSON integer exceeds the supported 64-bit range")
    return int(value)


def _finite_json_float(value: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError("JSON number must be finite")
    return numeric


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


def _sanitized_url(url: str) -> str:
    parsed = urlsplit(url)
    hostname = parsed.hostname or ""
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    netloc = hostname
    if parsed.port is not None:
        netloc = f"{netloc}:{parsed.port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))
