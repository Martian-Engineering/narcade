export type GameKey = "minesweeper" | "tetris" | "pong";
export type PolicyKey = "jev" | "openjev" | "kev" | "heuristic" | "random";

export type Result = {
  mean: number;
  median: number;
  min: number;
  max: number;
  success: number;
  decisions: number;
  p50: number;
  p95: number;
};

export const games: Record<
  GameKey,
  {
    label: string;
    shortLabel: string;
    scoreLabel: string;
    format: (score: number) => string;
    summary: string;
    protocol: string;
    accent: string;
  }
> = {
  minesweeper: {
    label: "Minesweeper",
    shortLabel: "Mine",
    scoreLabel: "safe squares",
    format: (score) => score.toFixed(2),
    summary: "Read the clues, avoid the mines, clear the board.",
    protocol: "9 × 9 · 8 mines · seeded opening",
    accent: "#58eaff",
  },
  tetris: {
    label: "Tetris",
    shortLabel: "Tetris",
    scoreLabel: "arcade score",
    format: (score) => Math.round(score).toLocaleString("en-US"),
    summary: "Place each piece and keep the stack alive.",
    protocol: "10 × 20 · 7-bag · 200 pieces",
    accent: "#ff62c6",
  },
  pong: {
    label: "Pong",
    shortLabel: "Pong",
    scoreLabel: "points scored",
    format: (score) => score.toFixed(2),
    summary: "Track the ball and beat a fixed opponent.",
    protocol: "First to 3 · medium bot · lockstep",
    accent: "#74ff86",
  },
};

export const policies: Record<
  PolicyKey,
  { label: string; detail: string; kind: "model" | "baseline"; color: string }
> = {
  jev: { label: "Jev", detail: "1.13.0 · hosted", kind: "model", color: "#58eaff" },
  openjev: { label: "OpenJev", detail: "0.1 · hosted", kind: "model", color: "#ff62c6" },
  kev: { label: "Kev", detail: "4B · local BF16", kind: "model", color: "#74ff86" },
  heuristic: {
    label: "Heuristic",
    detail: "scripted anchor",
    kind: "baseline",
    color: "#f1eff9",
  },
  random: {
    label: "Random",
    detail: "seeded anchor",
    kind: "baseline",
    color: "#625e70",
  },
};

export const results: Record<GameKey, Record<PolicyKey, Result>> = {
  minesweeper: {
    heuristic: { mean: 69.667, median: 68, min: 68, max: 73, success: 0.3333, decisions: 8, p50: 0.161, p95: 0.196 },
    jev: { mean: 57.667, median: 56, min: 49, max: 68, success: 0, decisions: 2.333, p50: 316.573, p95: 369.955 },
    kev: { mean: 57.333, median: 56, min: 48, max: 68, success: 0, decisions: 2, p50: 2551.437, p95: 3905.374 },
    openjev: { mean: 64.667, median: 68, min: 56, max: 70, success: 0, decisions: 3, p50: 875.343, p95: 1182.686 },
    random: { mean: 58, median: 56, min: 49, max: 69, success: 0, decisions: 2.667, p50: 0.002, p95: 0.005 },
  },
  tetris: {
    heuristic: { mean: 14006.667, median: 14020, min: 13680, max: 14320, success: 1, decisions: 200, p50: 0.296, p95: 0.604 },
    jev: { mean: 8966.667, median: 10100, min: 5420, max: 11380, success: 0.6667, decisions: 186.667, p50: 328.398, p95: 400.589 },
    kev: { mean: 66.667, median: 40, min: 40, max: 120, success: 0, decisions: 39.333, p50: 3220.161, p95: 5921.351 },
    openjev: { mean: 8033.333, median: 7140, min: 6240, max: 10720, success: 0.3333, decisions: 179.333, p50: 455.028, p95: 588.137 },
    random: { mean: 26.667, median: 0, min: 0, max: 80, success: 0, decisions: 28, p50: 0.002, p95: 0.005 },
  },
  pong: {
    heuristic: { mean: 3, median: 3, min: 3, max: 3, success: 1, decisions: 356.667, p50: 0.001, p95: 0.001 },
    jev: { mean: 0.667, median: 1, min: 0, max: 1, success: 0, decisions: 130, p50: 328.908, p95: 399.533 },
    kev: { mean: 2, median: 2, min: 1, max: 3, success: 0.3333, decisions: 269.667, p50: 927.332, p95: 931.379 },
    openjev: { mean: 1, median: 1, min: 1, max: 1, success: 0, decisions: 78.333, p50: 428.829, p95: 614.273 },
    random: { mean: 1, median: 1, min: 0, max: 2, success: 0, decisions: 87.333, p50: 0.001, p95: 0.001 },
  },
};

export const modelLeaders: Record<GameKey, PolicyKey> = {
  minesweeper: "openjev",
  tetris: "jev",
  pong: "kev",
};

export const gameOrder: GameKey[] = ["minesweeper", "tetris", "pong"];
export const policyOrder: PolicyKey[] = ["openjev", "jev", "kev", "heuristic", "random"];
