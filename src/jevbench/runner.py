from __future__ import annotations

import hashlib
import math
import random
import statistics
import time
from collections.abc import Callable
from typing import Any

from .core import Action, Game, Policy, PolicyError, PolicyTimeout

PROTOCOL = "0.5.0"
FAILURES = ("invalid_actions", "timeouts", "policy_errors")


def run_episode(
    game: Game,
    policy: Policy,
    *,
    seed: int,
    max_decisions: int | None,
    trace: Callable[[dict], None] | None = None,
    latency_samples: list[float] | None = None,
) -> dict[str, Any]:
    started_episode = time.monotonic()
    latencies: list[float] = []
    failures = dict.fromkeys(FAILURES, 0)
    tokens = {"input_tokens": 0, "output_tokens": 0}
    reason = None
    while not game.done and (max_decisions is None or len(latencies) < max_decisions):
        observation = game.observation()
        actions = _ordered_actions(game.legal_actions(), game.id, seed, len(latencies))
        if not actions:
            failures["policy_errors"] += 1
            reason = "empty_action_set"
            break
        decision = None
        error = None
        started = time.perf_counter()
        try:
            decision = policy.decide(game, observation, actions)
        except PolicyError as exception:
            timeout = isinstance(exception, PolicyTimeout)
            failures["timeouts" if timeout else "policy_errors"] += 1
            error = "policy_timeout" if timeout else "policy_error"
        latency = (time.perf_counter() - started) * 1000
        latencies.append(latency)
        game.advance_time(latency)
        if decision is not None:
            for key in tokens:
                tokens[key] += getattr(decision, key)
            if decision.action_id not in {action.id for action in actions}:
                failures["invalid_actions"] += 1
                error = "invalid_action"
        if trace is not None:
            trace(
                {
                    "seed": seed,
                    "step": len(latencies),
                    "state": observation.state,
                    "instructions": observation.instructions,
                    "presented_action_ids": [action.id for action in actions],
                    "selected_action_id": decision.action_id if decision else None,
                    "latency_ms": round(latency, 3),
                    "error": error,
                }
            )
        if error:
            if not game.done:
                reason = error
            break
        if not game.done:
            assert decision is not None
            game.step(decision.action_id)
    if not game.done and reason is None:
        reason = "decision_limit"
    result = game.result()
    if reason:
        result.update(success=False, terminal_reason=reason)
    elapsed = time.monotonic() - started_episode
    if latency_samples is not None:
        latency_samples.extend(latencies)
    return {
        "seed": seed,
        **result,
        "decisions": len(latencies),
        **failures,
        **tokens,
        "elapsed_seconds": round(elapsed, 6),
        "solve_seconds": round(elapsed, 6)
        if game.id == "minesweeper" and result["success"]
        else None,
        "latency_ms": latency_summary(latencies),
    }


def run_benchmark(
    game_factory: Callable[[int], Game],
    policy_factory: Callable[[int], Policy],
    *,
    game_id: str,
    policy_name: str,
    first_seed: int,
    episodes: int,
    max_decisions: int | None,
    trace: Callable[[dict], None] | None = None,
) -> dict[str, Any]:
    runs = []
    latencies: list[float] = []
    metadata = {}
    for seed in range(first_seed, first_seed + episodes):
        policy = policy_factory(seed)
        runs.append(
            run_episode(
                game_factory(seed),
                policy,
                seed=seed,
                max_decisions=max_decisions,
                trace=trace,
                latency_samples=latencies,
            )
        )
        metadata = policy.metadata()
    scores = [run["score"] for run in runs]
    solved = [run["solve_seconds"] for run in runs if run["solve_seconds"] is not None]
    aggregate = {
        "score_name": runs[0]["score_name"],
        "mean_score": round(statistics.fmean(scores), 3),
        "min_score": min(scores),
        "max_score": max(scores),
        "success_rate": round(statistics.fmean(run["success"] for run in runs), 4),
        "mean_decisions": round(statistics.fmean(run["decisions"] for run in runs), 3),
        "p50_latency_ms": latency_summary(latencies)["p50"],
        "p95_latency_ms": latency_summary(latencies)["p95"],
        "mean_elapsed_seconds": round(statistics.fmean(run["elapsed_seconds"] for run in runs), 6),
        "mean_solve_seconds": round(statistics.fmean(solved), 6) if solved else None,
        **{
            key: sum(run[key] for run in runs)
            for key in (*FAILURES, "input_tokens", "output_tokens")
        },
    }
    if runs[0].get("mode") == "realtime":
        decisions = sum(run["decisions"] for run in runs)
        late = sum(run.get("late_decisions", 0) for run in runs)
        aggregate.update(
            mean_simulated_seconds=round(
                statistics.fmean(run["simulated_seconds"] for run in runs), 3
            ),
            late_decision_rate=round(late / decisions, 6) if decisions else 0,
        )
    return {
        "benchmark_version": PROTOCOL,
        "game": game_id,
        "policy": policy_name,
        "policy_metadata": metadata,
        "first_seed": first_seed,
        "episode_count": episodes,
        "aggregate": aggregate,
        "episodes": runs,
    }


def latency_summary(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    return {
        "p50": round(statistics.median(ordered), 3) if ordered else 0,
        "p95": round(ordered[math.ceil(len(ordered) * 0.95) - 1], 3) if ordered else 0,
    }


def _ordered_actions(actions: list[Action], game_id: str, seed: int, step: int) -> list[Action]:
    ordered = list(actions)
    order_seed = int.from_bytes(
        hashlib.sha256(f"{game_id}:{seed}:{step}".encode()).digest()[:8], "big"
    )
    random.Random(order_seed).shuffle(ordered)
    return ordered
