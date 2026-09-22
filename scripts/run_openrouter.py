"""Budget-limited, single-seed OpenRouter comparison using the existing game protocol."""

from __future__ import annotations

import argparse
import getpass
import json
import math
import os
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from pathlib import Path

from jevbench.config import RunConfig
from jevbench.core import PolicyDecision, PolicyError, PolicyTimeout
from jevbench.registry import RULES_VERSION, create_game
from jevbench.runner import FAILURES, PROTOCOL, latency_summary, run_benchmark
from jevbench.suite import write_json

API = "https://openrouter.ai/api/v1"
MODELS = ("openai/gpt-6-luna", "openai/gpt-6-sol", "anthropic/claude-sonnet-5")
MAX_TOKENS = 4096


class BudgetStop(Exception):
    pass


def synchronized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self.lock:
            return method(self, *args, **kwargs)

    return call


class Budget:
    def __init__(self, limit, path):
        self.limit, self.path = limit, path
        self.charged = 0.0
        self.reserved = 0.0
        self.calls = []
        self.lock = threading.RLock()

    def save(self):
        write_json(
            self.path,
            dict(
                limit_usd=self.limit,
                charged_usd=self.charged,
                reserved_usd=self.reserved,
                calls=self.calls,
            ),
        )

    @synchronized
    def reserve(self, ceiling):
        if self.charged + self.reserved + ceiling > self.limit:
            raise BudgetStop("Insufficient budget for the next request's maximum cost")
        self.reserved += ceiling
        self.save()

    @synchronized
    def settle(self, ceiling, cost, record):
        # Unknown charges retain their full reservation; never assume failed calls are free.
        if cost is not None:
            if not math.isfinite(cost) or cost < 0:
                raise BudgetStop("Invalid provider cost")
            self.reserved -= ceiling
            self.charged += cost
        self.calls.append({**record, "cost_usd": cost, "reserved_ceiling_usd": ceiling})
        self.save()


class ResumePolicy:
    """Replay a recorded lockstep prefix without calling the model again."""

    def __init__(self, policy, prefix, usage):
        self.policy, self.prefix, self.usage = policy, prefix, usage
        self.index = 0

    def metadata(self):
        return self.policy.metadata()

    def decide(self, game, observation, actions):
        if self.index >= len(self.prefix):
            return self.policy.decide(game, observation, actions)
        old = self.prefix[self.index]
        if (
            old["state"] != observation.state
            or old["instructions"] != observation.instructions
            or old["presented_action_ids"] != [a.id for a in actions]
            or old["error"]
        ):
            raise ValueError("Recorded prefix does not match the current engine")
        usage = self.usage[self.index].get("usage", {})
        self.index += 1
        return PolicyDecision(
            old["selected_action_id"],
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
        )


class OpenRouterPolicy:
    def __init__(self, key, model, effort, pricing, budget, lane_limit):
        self.key, self.model, self.effort = key, model, effort
        self.pricing, self.budget = pricing, budget
        self.lane_limit, self.lane_spend = lane_limit, 0.0
        self.name = model.replace("/", "--") + "--" + effort
        self.providers = set()
        self.resolved = set()

    def decide(self, game, observation, actions):
        prompt = json.dumps(
            {
                "state": observation.state,
                "instructions": observation.instructions,
                "criteria": {a.id: a.description for a in actions},
            }
        )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Choose exactly one legal action from the game input. "
                    "Return only its action ID, with no explanation or formatting.",
                },
                {"role": "user", "content": prompt},
            ],
            "reasoning": {"effort": self.effort, "exclude": True},
            "max_tokens": MAX_TOKENS,
            "provider": {
                "allow_fallbacks": False,
                "require_parameters": True,
                "max_price": {
                    "prompt": self.pricing["prompt"] * 1e6,
                    "completion": self.pricing["completion"] * 1e6,
                },
            },
        }
        encoded = json.dumps(payload).encode()
        # ASCII input: bytes plus generous framing allowance upper-bound prompt tokens.
        ceiling = (
            (len(encoded) + 4096) * self.pricing["prompt"]
            + MAX_TOKENS * self.pricing["completion"]
            + self.pricing.get("request", 0)
        ) * 1.05
        if self.lane_spend + ceiling > self.lane_limit:
            raise BudgetStop("Per-configuration budget reached")
        self.budget.reserve(ceiling)
        started = time.perf_counter()
        record = {"model": self.model, "effort": self.effort, "game": game.id}
        try:
            request = urllib.request.Request(
                API + "/chat/completions",
                data=encoded,
                headers={"Authorization": "Bearer " + self.key, "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=90) as response:
                body = json.load(response)
        except (OSError, ValueError) as error:
            self.lane_spend += ceiling
            self.budget.settle(ceiling, None, {**record, "error": type(error).__name__})
            if isinstance(error, TimeoutError):
                raise PolicyTimeout("OpenRouter request timed out") from None
            raise PolicyError("OpenRouter request failed: " + type(error).__name__) from None
        latency = (time.perf_counter() - started) * 1000
        usage = body.get("usage", {})
        raw_cost = usage.get("cost")
        cost = float(raw_cost) if raw_cost is not None else None
        self.lane_spend += cost if cost is not None else ceiling
        self.providers.add(body.get("provider", "unknown"))
        self.resolved.add(body.get("model", "unknown"))
        choices = body.get("choices") or [{}]
        action = (choices[0].get("message", {}).get("content") or "").strip()
        self.budget.settle(
            ceiling,
            cost,
            {
                **record,
                "id": body.get("id"),
                "provider": body.get("provider"),
                "latency_ms": latency,
                "finish_reason": choices[0].get("finish_reason"),
                "usage": usage,
                "action": action,
            },
        )
        if body.get("error") or choices[0].get("finish_reason") != "stop":
            raise PolicyError("Incomplete or failed model response")
        # Invalid IDs flow to the shared runner's invalid-action accounting. No repair call.
        return PolicyDecision(
            action, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
        )

    def metadata(self):
        return {
            "kind": "model",
            "provider": "openrouter",
            "requested_model": self.model,
            "resolved_models": sorted(self.resolved),
            "providers": sorted(self.providers),
            "reasoning_effort": self.effort,
            "max_completion_tokens": MAX_TOKENS,
            "cost_usd_or_reserved": self.lane_spend,
            "hardware": "Hosted via OpenRouter",
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--budget", type=float, default=4.75)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=1, choices=range(1, 7))
    parser.add_argument(
        "--games",
        nargs="+",
        default=["minesweeper", "snake", "tetris"],
        choices=["minesweeper", "snake", "tetris"],
    )
    args = parser.parse_args()
    if not 0 < args.budget <= 5:
        parser.error("budget must be between zero and $5")
    if not args.resume and args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("output directory must be empty")
    key = os.environ.get("OPENROUTER_API_KEY") or getpass.getpass("OpenRouter key (hidden): ")
    with urllib.request.urlopen(API + "/models") as response:
        catalog = {m["id"]: m for m in json.load(response)["data"]}
    request = urllib.request.Request(API + "/key", headers={"Authorization": "Bearer " + key})
    with urllib.request.urlopen(request) as response:
        key_info = json.load(response)["data"]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    budget = Budget(args.budget, args.output_dir / "spend.json")
    if args.resume:
        old_budget = json.loads(budget.path.read_text())
        budget.charged = old_budget["charged_usd"]
        budget.reserved = old_budget["reserved_usd"]
        budget.calls = old_budget["calls"]
        # The interrupted request might still be billed; retain its reservation.
    config = RunConfig(mode="lockstep", episodes=1, seed=100, max_pieces=200, max_decisions=500)
    manifest = {
        "protocol": PROTOCOL,
        "budget_usd": args.budget,
        "key_usage_before": key_info.get("usage"),
        "status": "running",
        "runs": [],
        "comparison": "One-seed pilot; compare with Jev seed 100, not three-seed means",
    }
    if args.resume:
        manifest = json.loads((args.output_dir / "manifest.json").read_text())
    manifest.update(
        status="running",
        workers=args.workers,
        active_games=args.games,
        resumed_parallel=args.resume and args.workers > 1,
    )
    write_json(args.output_dir / "manifest.json", manifest)
    manifest_lock = threading.Lock()

    def run_lane(pair):
        model, effort = pair
        item = catalog[model]
        if effort not in item.get("reasoning", {}).get("supported_efforts", []):
            raise ValueError(f"Unsupported effort: {model}/{effort}")
        pricing = {k: float(item["pricing"].get(k, 0)) for k in ("prompt", "completion", "request")}
        policy = OpenRouterPolicy(key, model, effort, pricing, budget, args.budget / 6)
        old_calls = [c for c in budget.calls if c["model"] == model and c["effort"] == effort]
        policy.lane_spend = sum(
            c["cost_usd"] if c["cost_usd"] is not None else c["reserved_ceiling_usd"]
            for c in old_calls
        )
        for game_id in args.games:
            options = config.game_options(game_id)
            game = create_game(game_id, seed=100, **options)
            path = args.output_dir / f"{policy.name}-{game_id}.json"
            if path.exists():
                continue
            trace_path = path.with_suffix(".jsonl")
            prefix = (
                [json.loads(line) for line in trace_path.read_text().splitlines()]
                if trace_path.exists()
                else []
            )
            if prefix:
                backup = trace_path.with_suffix(".interrupted.jsonl")
                if not backup.exists():
                    backup.write_bytes(trace_path.read_bytes())
            replay_policy = ResumePolicy(
                policy, prefix, [c for c in old_calls if c["game"] == game_id]
            )
            latencies = []
            with path.with_suffix(".jsonl").open("w") as stream:

                def trace(record, prefix=prefix, latencies=latencies, stream=stream):
                    if record["step"] <= len(prefix):
                        record = prefix[record["step"] - 1]
                    latencies.append(record["latency_ms"])
                    stream.write(json.dumps(record) + "\n")
                    stream.flush()

                try:
                    result = run_benchmark(
                        lambda seed, game=game: game,
                        lambda seed, policy=replay_policy: policy,
                        game_id=game_id,
                        policy_name=policy.name,
                        first_seed=100,
                        episodes=1,
                        max_decisions=500,
                        trace=trace,
                    )
                    result["configuration"] = {
                        "rules_version": RULES_VERSION,
                        **options,
                        "max_decisions": 500,
                    }
                    result["status"] = (
                        "failed" if any(result["aggregate"][k] for k in FAILURES) else "completed"
                    )
                    latency = latency_summary(latencies)
                    result["episodes"][0]["latency_ms"] = latency
                    result["aggregate"].update(
                        p50_latency_ms=latency["p50"], p95_latency_ms=latency["p95"]
                    )
                    result["execution"] = {
                        "workers": args.workers,
                        "replayed_prefix_decisions": len(prefix),
                    }
                    if prefix:
                        result["episodes"][0]["elapsed_seconds"] = None
                        result["aggregate"]["mean_elapsed_seconds"] = None
                except BudgetStop as error:
                    result = {
                        "status": "budget_stopped",
                        "game": game_id,
                        "policy": policy.name,
                        "partial_result": game.result(),
                        "reason": str(error),
                    }
                write_json(path, result)
            with manifest_lock:
                manifest["runs"].append({"file": path.name, "status": result["status"]})
                write_json(args.output_dir / "manifest.json", manifest)
            print(
                policy.name,
                game_id,
                result["status"],
                result.get("aggregate", {}).get("mean_score"),
                f"total=${budget.charged:.4f}",
                flush=True,
            )

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        list(executor.map(run_lane, [(m, e) for e in ("low", "medium") for m in MODELS]))
    with urllib.request.urlopen(request) as response:
        manifest["key_usage_after"] = json.load(response)["data"].get("usage")
    manifest["status"] = "finished"
    write_json(args.output_dir / "manifest.json", manifest)


if __name__ == "__main__":
    main()
