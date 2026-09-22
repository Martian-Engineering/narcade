import published from "./published.json";

export const records = published.records;
export const runLabel = published.label;
export const gameNames: Record<string, string> = {
  minesweeper: "Minesweeper", tetris: "Tetris", snake: "Snake",
};
export const policyNames: Record<string, string> = {
  jev: "Jev", openjev: "OpenJev", kev: "Kev", laya: "Laya",
  "laya-typed": "Laya Typed", "laya-multilingual": "Laya Multilingual",
  heuristic: "Heuristic", random: "Random",
};
export const isBaseline = (policy: string) => policy === "random" || policy === "heuristic";
