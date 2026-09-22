"""Export protocol 0.5.0 lockstep traces after checking states and final scores."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from jevbench.registry import create_game
from jevbench.runner import PROTOCOL

ROOT = Path(__file__).resolve().parents[1]


def reconstruct(payload: dict, episode: dict, decisions: list[dict]) -> dict:
    game_id = payload["game"]
    if payload["benchmark_version"] != PROTOCOL or payload["status"] != "completed":
        raise ValueError("Expected a completed run from the current protocol")
    if episode.get("mode", "lockstep") != "lockstep":
        raise ValueError("Replay export requires lockstep recordings")
    config = payload["configuration"]
    game = create_game(
        game_id,
        seed=episode["seed"],
        **{key: config[key] for key in ("difficulty", "mode", "piece_limit", "max_seconds")},
    )
    if len(decisions) != episode["decisions"]:
        raise ValueError("Incomplete decision trace")
    frames = []
    for index, decision in enumerate(decisions, 1):
        observation = game.observation()
        criteria = {action.id: action.description for action in game.legal_actions()}
        if (
            decision["step"] != index
            or decision["state"] != observation.state
            or decision["instructions"] != observation.instructions
            or set(decision["presented_action_ids"]) != set(criteria)
        ):
            raise ValueError(f"Trace input mismatch: {game_id}/{payload['policy']}/{index}")
        frames.append(
            {
                "step": decision["step"],
                "state": observation.state,
                "result": game.result(),
                "action": decision["selected_action_id"],
                "latency_ms": decision["latency_ms"],
                "probabilities": decision.get("probabilities"),
                "instructions": observation.instructions,
                "criteria": {key: criteria[key] for key in decision["presented_action_ids"]},
            }
        )
        if decision.get("error") or decision["selected_action_id"] not in criteria:
            raise ValueError("Cannot export failed model calls as verified gameplay")
        game.step(decision["selected_action_id"])
    actual = game.result()
    for key in ("score", "lines", "pieces", "ticks", "moves"):
        if key in actual and actual[key] != episode[key]:
            raise ValueError(f"Final {key} mismatch for {game_id}/{payload['policy']}")
    reason = actual["terminal_reason"] if game.done else "decision_limit"
    if reason != episode["terminal_reason"]:
        raise ValueError("Final termination mismatch")
    frames.append(
        {
            "step": len(frames) + 1,
            "state": game.observation().state,
            "result": {**actual, "terminal_reason": episode["terminal_reason"]},
            "action": None,
            "latency_ms": None,
            "probabilities": None,
            "instructions": "",
            "criteria": {},
        }
    )
    return {
        "id": f"{payload['policy']}-{episode['seed']}",
        "model": payload["policy"],
        "seed": episode["seed"],
        "score": episode["score"],
        "terminal_reason": episode["terminal_reason"],
        "frames": frames,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "app/public/replays")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for game in ("tetris", "snake", "minesweeper"):
        episodes = []
        paths = sorted(
            path for directory in args.input for path in directory.glob(f"*-{game}.json")
        )
        for path in paths:
            payload = json.loads(path.read_text())
            trace = [
                json.loads(line) for line in path.with_suffix(".jsonl").read_text().splitlines()
            ]
            episodes.extend(
                reconstruct(payload, episode, [d for d in trace if d["seed"] == episode["seed"]])
                for episode in payload["episodes"]
            )
        if not episodes or len({e["id"] for e in episodes}) != len(episodes):
            raise ValueError(f"Missing or duplicate recordings for {game}")
        output = {
            "game": game,
            "protocol": PROTOCOL,
            "mode": "lockstep",
            "provenance": (
                "Every recorded state, instruction, action set and final score verified. "
                "Probabilities were not recorded in this protocol."
            ),
            "engine_revision": PROTOCOL,
            "episodes": episodes,
        }
        (args.output / f"{game}.json").write_text(json.dumps(output, separators=(",", ":")) + "\n")
        print(f"{game}: {len(episodes)} episodes verified")


if __name__ == "__main__":
    main()
