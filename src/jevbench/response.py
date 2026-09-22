from __future__ import annotations

import math
from typing import Any

from .core import PolicyDecision, PolicyError


def parse_decision(body: dict) -> PolicyDecision:
    try:
        answer = body["answers"]["action"]
        action_id = answer["choice"]
    except (KeyError, TypeError) as error:
        raise PolicyError("response is missing answers.action.choice") from error
    if not isinstance(action_id, str):
        raise PolicyError("answers.action.choice must be a string")
    usage = body.get("usage") or {}
    return PolicyDecision(
        action_id=action_id,
        input_tokens=_usage_int(usage, "input_tokens", "inputTokens"),
        output_tokens=_usage_int(usage, "output_tokens", "outputTokens"),
    )


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
