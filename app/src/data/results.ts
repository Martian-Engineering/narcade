export type GameKey = "minesweeper" | "tetris" | "pong";
export type PublishedGameKey = Exclude<GameKey, "tetris">;
export type PolicyKey =
  | "jev"
  | "openjev"
  | "kev"
  | "laya"
  | "layaTyped"
  | "heuristic"
  | "random";

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
    protocol: "10 × 20 · 7-bag · fixed controls",
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
  {
    label: string;
    detail: string;
    kind: "model" | "baseline";
    color: string;
    variant?: boolean;
  }
> = {
  jev: { label: "Jev", detail: "1.13.0 · hosted", kind: "model", color: "#58eaff" },
  openjev: { label: "OpenJev", detail: "0.1 · hosted", kind: "model", color: "#ff62c6" },
  kev: { label: "Kev", detail: "4B · local BF16", kind: "model", color: "#74ff86" },
  laya: { label: "Laya", detail: "421M · local FP32", kind: "model", color: "#ffd166" },
  layaTyped: {
    label: "Laya Typed",
    detail: "421M · local FP32",
    kind: "model",
    color: "#c9a7ff",
    variant: true,
  },
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

export const results: Record<PublishedGameKey, Record<PolicyKey, Result>> = {
  minesweeper: {
    heuristic: { mean: 69.667, median: 68, min: 68, max: 73, success: 0.3333, decisions: 8, p50: 0.161, p95: 0.196 },
    jev: { mean: 57.667, median: 56, min: 49, max: 68, success: 0, decisions: 2.333, p50: 316.573, p95: 369.955 },
    kev: { mean: 57.333, median: 56, min: 48, max: 68, success: 0, decisions: 2, p50: 2551.437, p95: 3905.374 },
    openjev: { mean: 64.667, median: 68, min: 56, max: 70, success: 0, decisions: 3, p50: 875.343, p95: 1182.686 },
    laya: { mean: 59.333, median: 63, min: 48, max: 67, success: 0, decisions: 4, p50: 99.936, p95: 361.044 },
    layaTyped: { mean: 58, median: 61, min: 46, max: 67, success: 0, decisions: 2.667, p50: 105.426, p95: 202.934 },
    random: { mean: 58, median: 56, min: 49, max: 69, success: 0, decisions: 2.667, p50: 0.002, p95: 0.005 },
  },
  pong: {
    heuristic: { mean: 3, median: 3, min: 3, max: 3, success: 1, decisions: 356.667, p50: 0.001, p95: 0.001 },
    jev: { mean: 0.667, median: 1, min: 0, max: 1, success: 0, decisions: 130, p50: 328.908, p95: 399.533 },
    kev: { mean: 2, median: 2, min: 1, max: 3, success: 0.3333, decisions: 269.667, p50: 927.332, p95: 931.379 },
    openjev: { mean: 1, median: 1, min: 1, max: 1, success: 0, decisions: 78.333, p50: 428.829, p95: 614.273 },
    laya: { mean: 0, median: 0, min: 0, max: 0, success: 0, decisions: 74.667, p50: 57.576, p95: 60.718 },
    layaTyped: { mean: 0.333, median: 0, min: 0, max: 1, success: 0, decisions: 81.667, p50: 58.015, p95: 62.289 },
    random: { mean: 1, median: 1, min: 0, max: 2, success: 0, decisions: 87.333, p50: 0.001, p95: 0.001 },
  },
};

export const modelLeaders: Record<PublishedGameKey, PolicyKey> = {
  minesweeper: "openjev",
  pong: "kev",
};

export const gameOrder: PublishedGameKey[] = ["minesweeper", "pong"];
export const policyOrder: PolicyKey[] = [
  "openjev",
  "jev",
  "kev",
  "laya",
  "layaTyped",
  "heuristic",
  "random",
];
