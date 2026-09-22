"""Produce a small website artifact and paired score changes from raw runs."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from .runner import FAILURES
from .suite import write_json


def summarize(paths: list[Path], label: str) -> dict:
    records = []
    seen = set()
    protocols = {}
    for path in paths:
        result = json.loads(path.read_text())
        if result.get("status") != "completed" or any(result["aggregate"][key] for key in FAILURES):
            raise ValueError(f"cannot publish failed run: {path}")
        game, policy = result["game"], result["policy"]
        if (game, policy) in seen:
            raise ValueError(f"duplicate game/policy: {game}/{policy}")
        seen.add((game, policy))
        protocol = {"version": result["benchmark_version"], **result["configuration"]}
        seeds = [episode["seed"] for episode in result["episodes"]]
        identity = (protocol, seeds)
        if game in protocols and protocols[game] != identity:
            raise ValueError(f"incompatible protocol or seeds for {game}")
        protocols[game] = identity
        records.append(
            {
                "game": game,
                "policy": policy,
                "protocol": protocol,
                "model": result["policy_metadata"],
                "aggregate": {
                    key: result["aggregate"].get(key)
                    for key in (
                        "mean_score",
                        "min_score",
                        "max_score",
                        "success_rate",
                        "p50_latency_ms",
                        "p95_latency_ms",
                        "mean_solve_seconds",
                        "mean_elapsed_seconds",
                    )
                },
                "episodes": [
                    {key: episode.get(key) for key in ("seed", "score", "success", "solve_seconds")}
                    for episode in result["episodes"]
                ],
            }
        )
    if not records:
        raise ValueError("no result files supplied")
    return {"label": label, "records": records}


def compare(before: dict, after: dict) -> list[dict]:
    old = {(row["game"], row["policy"]): row for row in before["records"]}
    changes = []
    for row in after["records"]:
        key = row["game"], row["policy"]
        if key not in old:
            continue
        prior = old[key]
        for field in row["protocol"].keys() | prior["protocol"].keys():
            if field != "version" and row["protocol"].get(field) != prior["protocol"].get(field):
                raise ValueError(f"cannot compare {key}: changed {field}")
        # Model/deployment changes would confound the observation comparison.
        for field in (
            "requested_model",
            "resolved_model",
            "artifact_revision",
            "runtime_revision",
            "hardware",
            "quantization",
        ):
            if row["model"].get(field) != prior["model"].get(field):
                raise ValueError(f"cannot compare {key}: changed model {field}")
        prior_scores = {episode["seed"]: episode["score"] for episode in prior["episodes"]}
        if set(prior_scores) != {episode["seed"] for episode in row["episodes"]}:
            raise ValueError(f"cannot compare {key}: changed seeds")
        deltas = [episode["score"] - prior_scores[episode["seed"]] for episode in row["episodes"]]
        base = statistics.fmean(prior_scores.values())
        delta = statistics.fmean(deltas)
        changes.append(
            {
                "game": key[0],
                "policy": key[1],
                "before": base,
                "after": base + delta,
                "score_delta": delta,
                "percent_change": 100 * delta / base if base else None,
                "seed_deltas": deltas,
            }
        )
    if not changes:
        raise ValueError("no shared game/policy pairs")
    return changes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path, nargs="+")
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compare-with", type=Path)
    args = parser.parse_args()
    try:
        published = summarize(args.inputs, args.label)
        if args.compare_with:
            published["changes"] = compare(json.loads(args.compare_with.read_text()), published)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        write_json(args.output, published)
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
