from __future__ import annotations

import math
import random

from ...core import Action, Observation

OPPONENTS = {
    "easy": {"speed": 0.45, "reaction": 0.34, "noise": 0.28},
    "medium": {"speed": 0.65, "reaction": 0.18, "noise": 0.20},
    "hard": {"speed": 0.88, "reaction": 0.09, "noise": 0.16},
}


class Pong:
    id = "pong"
    score_name = "points_scored"
    paddle_height = 0.22
    paddle_width = 0.018
    paddle_speed = 0.90
    ball_radius = 0.014
    left_x = 0.04
    right_x = 0.96
    decision_interval = 0.10
    simulation_tick = 0.01

    def __init__(
        self,
        seed: int,
        difficulty: str = "medium",
        mode: str = "lockstep",
        target_score: int = 3,
        max_seconds: float = 120.0,
    ):
        if difficulty not in OPPONENTS:
            raise ValueError(f"unknown Pong difficulty: {difficulty}")
        if mode not in {"lockstep", "realtime"}:
            raise ValueError(f"unknown Pong mode: {mode}")
        self.seed = seed
        self.difficulty = difficulty
        self.mode = mode
        self.target_score = target_score
        self.max_seconds = max_seconds
        self._rng = random.Random(seed)
        self.agent_score = 0
        self.opponent_score = 0
        self.agent_y = 0.5
        self.opponent_y = 0.5
        self.agent_command = "stay"
        self.opponent_command = "stay"
        self.opponent_target = 0.5
        self._opponent_reaction_left = 0.0
        self.elapsed_seconds = 0.0
        self.returns = 0
        self.rallies = 0
        self._done = False
        self._terminal_reason = "playing"
        self._serve(direction=1 if self._rng.random() < 0.5 else -1)

    @property
    def done(self) -> bool:
        return self._done

    def _serve(self, direction: int) -> None:
        self.ball_x = 0.5
        self.ball_y = 0.5
        self.ball_vx = 0.62 * direction
        self.ball_vy = self._rng.uniform(-0.32, 0.32)
        if abs(self.ball_vy) < 0.10:
            self.ball_vy = math.copysign(0.10, self.ball_vy or 1.0)
        self.rallies += 1

    @staticmethod
    def _command_axis(command: str) -> int:
        return {"up": -1, "stay": 0, "down": 1}[command]

    def _move_paddles(self, dt: float) -> None:
        half = self.paddle_height / 2
        self.agent_y += self._command_axis(self.agent_command) * self.paddle_speed * dt
        opponent = OPPONENTS[self.difficulty]
        self.opponent_y += self._command_axis(self.opponent_command) * opponent["speed"] * dt
        self.agent_y = min(1 - half, max(half, self.agent_y))
        self.opponent_y = min(1 - half, max(half, self.opponent_y))

    def _update_opponent(self, dt: float) -> None:
        self._opponent_reaction_left -= dt
        if self._opponent_reaction_left > 0:
            return
        config = OPPONENTS[self.difficulty]
        self._opponent_reaction_left = config["reaction"]
        if self.ball_vx < 0:
            travel = max(0.0, (self.ball_x - self.left_x) / -self.ball_vx)
            target = _reflected_y(self.ball_y + self.ball_vy * travel)
        else:
            target = 0.5
        self.opponent_target = target + self._rng.uniform(-config["noise"], config["noise"])
        tolerance = 0.035
        if self.opponent_target < self.opponent_y - tolerance:
            self.opponent_command = "up"
        elif self.opponent_target > self.opponent_y + tolerance:
            self.opponent_command = "down"
        else:
            self.opponent_command = "stay"

    def _simulate_tick(self, dt: float) -> None:
        self._update_opponent(dt)
        self._move_paddles(dt)
        old_x = self.ball_x
        self.ball_x += self.ball_vx * dt
        self.ball_y += self.ball_vy * dt

        if self.ball_y - self.ball_radius < 0:
            self.ball_y = self.ball_radius
            self.ball_vy = abs(self.ball_vy)
        elif self.ball_y + self.ball_radius > 1:
            self.ball_y = 1 - self.ball_radius
            self.ball_vy = -abs(self.ball_vy)

        left_face = self.left_x + self.paddle_width
        crossed_left = old_x - self.ball_radius > left_face >= self.ball_x - self.ball_radius
        reached_opponent = (
            abs(self.ball_y - self.opponent_y) <= self.paddle_height / 2 + self.ball_radius
        )
        if self.ball_vx < 0 and crossed_left and reached_opponent:
            self.ball_x = left_face + self.ball_radius
            self.ball_vx = abs(self.ball_vx) * 1.025
            self.ball_vy += (self.ball_y - self.opponent_y) * 1.8
            self.returns += 1

        right_face = self.right_x - self.paddle_width
        crossed_right = old_x + self.ball_radius < right_face <= self.ball_x + self.ball_radius
        reached_agent = abs(self.ball_y - self.agent_y) <= self.paddle_height / 2 + self.ball_radius
        if self.ball_vx > 0 and crossed_right and reached_agent:
            self.ball_x = right_face - self.ball_radius
            self.ball_vx = -abs(self.ball_vx) * 1.025
            self.ball_vy += (self.ball_y - self.agent_y) * 1.8
            self.returns += 1

        self.ball_vx = max(-1.15, min(1.15, self.ball_vx))
        self.ball_vy = max(-0.95, min(0.95, self.ball_vy))

        scored_direction = 0
        if self.ball_x < -self.ball_radius:
            self.agent_score += 1
            scored_direction = 1
        elif self.ball_x > 1 + self.ball_radius:
            self.opponent_score += 1
            scored_direction = -1

        if max(self.agent_score, self.opponent_score) >= self.target_score:
            self._done = True
            self._terminal_reason = "target_score"
        elif self.elapsed_seconds >= self.max_seconds:
            self._done = True
            self._terminal_reason = "time_limit"
        elif scored_direction:
            self._serve(scored_direction)

    def _advance(self, seconds: float) -> None:
        remaining = seconds
        while remaining > 1e-9 and not self.done:
            until_deadline = self.max_seconds - self.elapsed_seconds
            if until_deadline <= 1e-9:
                self._done = True
                self._terminal_reason = "time_limit"
                break
            dt = min(self.simulation_tick, remaining, until_deadline)
            self.elapsed_seconds += dt
            self._simulate_tick(dt)
            remaining -= dt

    def observation(self) -> Observation:
        return Observation(
            state={
                "game": "Pong",
                "mode": self.mode,
                "opponent": f"deterministic {self.difficulty} tracking bot",
                "coordinate_system": "x and y range from 0 to 1; y=0 is the top",
                "agent": {"side": "right", "paddle_y": round(self.agent_y, 4)},
                "opponent_paddle_y": round(self.opponent_y, 4),
                "ball": {
                    "x": round(self.ball_x, 4),
                    "y": round(self.ball_y, 4),
                    "vx": round(self.ball_vx, 4),
                    "vy": round(self.ball_vy, 4),
                },
                "score": {"agent": self.agent_score, "opponent": self.opponent_score},
                "target_score": self.target_score,
            },
            instructions=(
                "Control the right paddle. Choose up, stay, or down. Intercept the ball at the "
                "right edge. Account for its vertical velocity and wall bounces. In real-time "
                "mode, the previous command remains active while this decision is computed."
            ),
        )

    def legal_actions(self) -> list[Action]:
        if self.done:
            return []
        return [
            Action("up", "Move the right paddle upward"),
            Action("stay", "Keep the right paddle at its current position"),
            Action("down", "Move the right paddle downward"),
        ]

    def step(self, action_id: str, latency_ms: float = 0.0) -> None:
        if action_id not in {action.id for action in self.legal_actions()}:
            raise ValueError(f"illegal Pong action: {action_id}")
        if self.mode == "lockstep":
            self.agent_command = action_id
            self._advance(self.decision_interval)
        else:
            self.agent_command = action_id

    def advance_time(self, latency_ms: float) -> None:
        if self.mode == "realtime":
            self._advance(max(self.decision_interval, latency_ms / 1000))

    def heuristic_action_id(self) -> str:
        if self.ball_vx > 0:
            travel = max(0.0, (self.right_x - self.ball_x) / self.ball_vx)
            target = _reflected_y(self.ball_y + self.ball_vy * travel)
        else:
            target = 0.5
        tolerance = 0.025
        if target < self.agent_y - tolerance:
            return "up"
        if target > self.agent_y + tolerance:
            return "down"
        return "stay"

    def result(self) -> dict[str, object]:
        return {
            "score": self.agent_score,
            "score_name": self.score_name,
            "success": self.done and self.agent_score > self.opponent_score,
            "terminal_reason": self._terminal_reason,
            "agent_points": self.agent_score,
            "opponent_points": self.opponent_score,
            "point_differential": self.agent_score - self.opponent_score,
            "returns": self.returns,
            "rallies": self.rallies,
            "simulated_seconds": round(self.elapsed_seconds, 3),
            "opponent": self.difficulty,
            "mode": self.mode,
        }


def _reflected_y(unbounded_y: float) -> float:
    period = unbounded_y % 2.0
    return period if period <= 1.0 else 2.0 - period
