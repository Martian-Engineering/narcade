from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
import time
from collections.abc import Callable
from typing import Any

from .core import Action, Game, Observation, Policy, PolicyError, PolicyTimeout


def run_episode(
    game: Game,
    policy: Policy,
    *,
    seed: int,
    max_decisions: int | None,
    record_decisions: bool = False,
) -> dict[str, Any]:
    latencies: list[float] = []
    input_tokens = 0
    output_tokens = 0
    invalid_actions = 0
    timeouts = 0
    policy_errors = 0
    decisions: list[dict[str, Any]] = []
    entropies: list[float] = []
    confidences: list[float] = []
    override_reason: str | None = None

    while not game.done and (max_decisions is None or len(latencies) < max_decisions):
        observation = game.observation()
        actions = _ordered_actions(game.legal_actions(), game.id, seed, len(latencies))
        if not actions:
            override_reason = "empty_action_set"
            policy_errors += 1
            break

        started = time.perf_counter()
        try:
            decision = policy.decide(game, observation, actions)
        except PolicyTimeout:
            latency_ms = (time.perf_counter() - started) * 1000
            latencies.append(latency_ms)
            game.advance_time(latency_ms)
            timeouts += 1
            if not game.done:
                override_reason = "policy_timeout"
            if record_decisions:
                decisions.append(
                    _decision_record(
                        observation,
                        actions,
                        selected_action_id=None,
                        latency_ms=latency_ms,
                        input_tokens=0,
                        output_tokens=0,
                        valid=False,
                        error="policy_timeout",
                        probabilities=None,
                        confidence=None,
                        step=len(latencies),
                    )
                )
            break
        except PolicyError:
            latency_ms = (time.perf_counter() - started) * 1000
            latencies.append(latency_ms)
            game.advance_time(latency_ms)
            policy_errors += 1
            if not game.done:
                override_reason = "policy_error"
            if record_decisions:
                decisions.append(
                    _decision_record(
                        observation,
                        actions,
                        selected_action_id=None,
                        latency_ms=latency_ms,
                        input_tokens=0,
                        output_tokens=0,
                        valid=False,
                        error="policy_error",
                        probabilities=None,
                        confidence=None,
                        step=len(latencies),
                    )
                )
            break
        latency_ms = (time.perf_counter() - started) * 1000
        latencies.append(latency_ms)
        game.advance_time(latency_ms)
        input_tokens += decision.input_tokens
        output_tokens += decision.output_tokens
        entropy = _entropy_bits(decision.probabilities)
        if entropy is not None:
            entropies.append(entropy)
        if decision.confidence is not None:
            confidences.append(decision.confidence)

        legal_ids = {action.id for action in actions}
        valid = decision.action_id in legal_ids
        if record_decisions:
            decisions.append(
                _decision_record(
                    observation,
                    actions,
                    selected_action_id=decision.action_id,
                    latency_ms=latency_ms,
                    input_tokens=decision.input_tokens,
                    output_tokens=decision.output_tokens,
                    valid=valid,
                    error=None if valid else "invalid_action",
                    probabilities=decision.probabilities,
                    confidence=decision.confidence,
                    step=len(latencies),
                )
            )
        if not valid:
            invalid_actions += 1
            if not game.done:
                override_reason = "invalid_action"
            break

        if not game.done:
            game.step(decision.action_id, latency_ms=latency_ms)

    if not game.done and override_reason is None and max_decisions is not None:
        override_reason = "decision_limit"

    game_result = game.result()
    simulated_seconds = float(game_result.get("simulated_seconds", 0.0))
    if game_result.get("mode") == "realtime":
        game_result["score_per_second"] = (
            round(float(game_result["score"]) / simulated_seconds, 6)
            if simulated_seconds > 0
            else None
        )
    if override_reason:
        game_result["success"] = False
        game_result["terminal_reason"] = override_reason

    episode = {
        "seed": seed,
        "game": game.id,
        "policy": policy.name,
        "policy_metadata": policy.metadata(),
        **game_result,
        "decisions": len(latencies),
        "invalid_actions": invalid_actions,
        "timeouts": timeouts,
        "policy_errors": policy_errors,
        "latency_ms": {
            "mean": round(statistics.fmean(latencies), 3) if latencies else 0.0,
            "p50": round(statistics.median(latencies), 3) if latencies else 0.0,
            "p95": round(_percentile(latencies, 0.95), 3) if latencies else 0.0,
            "max": round(max(latencies), 3) if latencies else 0.0,
        },
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "mean_probability_entropy_bits": (
            round(statistics.fmean(entropies), 6) if entropies else None
        ),
        "mean_confidence": round(statistics.fmean(confidences), 6) if confidences else None,
        "_latency_samples": latencies,
        "_entropy_samples": entropies,
        "_confidence_samples": confidences,
    }
    if record_decisions:
        episode["decision_log"] = decisions
    return episode


def run_benchmark(
    game_factory: Callable[[int], Game],
    policy_factory: Callable[[int], Policy],
    *,
    game_id: str,
    policy_name: str,
    first_seed: int,
    episodes: int,
    max_decisions: int | None,
    record_decisions: bool = False,
) -> dict[str, Any]:
    runs = []
    for offset in range(episodes):
        seed = first_seed + offset
        runs.append(
            run_episode(
                game_factory(seed),
                policy_factory(seed),
                seed=seed,
                max_decisions=max_decisions,
                record_decisions=record_decisions,
            )
        )

    scores = [float(run["score"]) for run in runs]
    latencies = [float(sample) for run in runs for sample in run["_latency_samples"]]
    entropies = [float(sample) for run in runs for sample in run["_entropy_samples"]]
    confidences = [float(sample) for run in runs for sample in run["_confidence_samples"]]
    for run in runs:
        del run["_latency_samples"]
        del run["_entropy_samples"]
        del run["_confidence_samples"]

    realtime_runs = [run for run in runs if run.get("mode") == "realtime"]
    total_decisions = sum(int(run["decisions"]) for run in runs)
    total_late_decisions = sum(int(run.get("late_decisions", 0)) for run in runs)

    aggregate = {
        "score_name": runs[0]["score_name"],
        "mean_score": round(statistics.fmean(scores), 3),
        "median_score": round(statistics.median(scores), 3),
        "min_score": min(scores),
        "max_score": max(scores),
        "success_rate": round(sum(bool(run["success"]) for run in runs) / episodes, 4),
        "mean_decisions": round(statistics.fmean(int(run["decisions"]) for run in runs), 3),
        "p50_latency_ms": round(statistics.median(latencies), 3) if latencies else 0.0,
        "p95_latency_ms": round(_percentile(latencies, 0.95), 3) if latencies else 0.0,
        "invalid_actions": sum(int(run["invalid_actions"]) for run in runs),
        "timeouts": sum(int(run["timeouts"]) for run in runs),
        "policy_errors": sum(int(run["policy_errors"]) for run in runs),
        "input_tokens": sum(int(run["input_tokens"]) for run in runs),
        "output_tokens": sum(int(run["output_tokens"]) for run in runs),
        "mean_probability_entropy_bits": (
            round(statistics.fmean(entropies), 6) if entropies else None
        ),
        "mean_confidence": (round(statistics.fmean(confidences), 6) if confidences else None),
    }
    if realtime_runs:
        score_rates = [
            float(run["score_per_second"])
            for run in realtime_runs
            if run.get("score_per_second") is not None
        ]
        aggregate.update(
            {
                "mean_simulated_seconds": round(
                    statistics.fmean(float(run["simulated_seconds"]) for run in realtime_runs),
                    3,
                ),
                "mean_score_per_second": (
                    round(statistics.fmean(score_rates), 6) if score_rates else None
                ),
                "late_decisions": total_late_decisions,
                "late_decision_rate": (
                    round(total_late_decisions / total_decisions, 6) if total_decisions else 0.0
                ),
            }
        )

    return {
        "benchmark_version": "0.4.0",
        "game": game_id,
        "policy": policy_name,
        "policy_metadata": _unique_metadata(runs),
        "first_seed": first_seed,
        "episode_count": episodes,
        "aggregate": aggregate,
        "episodes": runs,
    }


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[index]


def _decision_record(
    observation: Observation,
    actions: list[Action],
    *,
    selected_action_id: str | None,
    latency_ms: float,
    input_tokens: int,
    output_tokens: int,
    valid: bool,
    error: str | None,
    probabilities: dict[str, float] | None,
    confidence: float | None,
    step: int,
) -> dict[str, Any]:
    model_input = {
        "state": observation.state,
        "instructions": observation.instructions,
        "criteria": {action.id: action.description for action in actions},
    }
    encoded = json.dumps(model_input, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "step": step,
        "model_input_sha256": hashlib.sha256(encoded).hexdigest(),
        "presented_action_ids": [action.id for action in actions],
        "selected_action_id": selected_action_id,
        "valid": valid,
        "error": error,
        "latency_ms": round(latency_ms, 3),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "probabilities": probabilities,
        "confidence": confidence,
        "probability_entropy_bits": _entropy_bits(probabilities),
    }


def _unique_metadata(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for run in runs:
        metadata = run["policy_metadata"]
        key = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
        unique[key] = metadata
    return list(unique.values())


def _ordered_actions(actions: list[Action], game_id: str, seed: int, step: int) -> list[Action]:
    ordered = list(actions)
    material = f"{game_id}:{seed}:{step}".encode()
    order_seed = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    random.Random(order_seed).shuffle(ordered)
    return ordered


def _entropy_bits(probabilities: dict[str, float] | None) -> float | None:
    if not probabilities:
        return None
    positive = [probability for probability in probabilities.values() if probability > 0]
    total = sum(positive)
    if total <= 0:
        return None
    return -sum((probability / total) * math.log2(probability / total) for probability in positive)
