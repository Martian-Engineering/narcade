import type { Metadata } from "next";
import { TetrisReplay } from "@/components/tetris-board";

export const metadata: Metadata = {
  title: "Tetris replays · NARCADE",
  description: "Watch recorded Tetris decisions from the NARCADE benchmark.",
};

export default function TetrisPage() {
  return <TetrisReplay />;
}
