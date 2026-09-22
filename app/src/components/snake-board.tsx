"use client";

import { useId } from "react";
import { ReplayViewer, type ReplayFrame } from "@/components/replay-viewer";

type Cell = [number, number];

function isCell(value: unknown): value is Cell {
  return Array.isArray(value) && value.length === 2 && value.every(Number.isFinite);
}

export function SnakeBoard({ frame }: { frame: ReplayFrame }) {
  const gridId = useId().replace(/:/g, "");
  const width = Math.max(1, Number(frame.state.grid_size?.[0]) || 20);
  const height = Math.max(1, Number(frame.state.grid_size?.[1]) || 20);
  const snake: Cell[] = (frame.state.snake ?? []).filter(isCell);
  const food = isCell(frame.state.food) ? frame.state.food : null;
  const heading = String(frame.state.direction ?? "RIGHT").toUpperCase();
  const headingAngles: Record<string, number> = { RIGHT: 0, DOWN: 90, LEFT: 180, UP: 270 };
  const angle = headingAngles[heading] ?? 0;
  const score = frame.result.score ?? frame.state.score ?? 0;

  return (
    <figure style={{ margin: 0, width: "100%", maxWidth: 620, marginInline: "auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginBottom: 14, textTransform: "uppercase", color: "var(--muted)", fontSize: 14 }}>
        <span>Food <strong style={{ color: "var(--green)" }}>{score}</strong></span>
        <span>Length <strong style={{ color: "var(--ink)" }}>{snake.length}</strong></span>
        <span>Heading <strong style={{ color: "var(--cyan)" }}>{heading}</strong></span>
      </div>
      <svg
        viewBox={`-0.12 -0.12 ${width + 0.24} ${height + 0.24}`}
        role="img"
        aria-label={`Snake board, ${width} by ${height}. Score ${score}. Heading ${heading}. Head at ${snake[0]?.join(", ") ?? "unknown"}. Food at ${food?.join(", ") ?? "none"}.`}
        style={{ display: "block", width: "100%", maxHeight: "65vh", background: "var(--bg)", border: "1px solid var(--line-bright)", boxShadow: "0 0 24px rgba(116,255,134,.04)" }}
      >
        <defs>
          <pattern id={gridId} width="1" height="1" patternUnits="userSpaceOnUse">
            <path d="M 1 0 L 0 0 0 1" fill="none" stroke="var(--line)" strokeWidth="0.025" />
          </pattern>
        </defs>
        <rect width={width} height={height} fill={`url(#${gridId})`} />
        {food && (
          <g transform={`translate(${food[0] + 0.5} ${food[1] + 0.5})`}>
            <rect x="-0.41" y="-0.41" width="0.82" height="0.82" fill="var(--pink)" opacity="0.12" />
            <path d="M -.15 -.3 H .15 V -.15 H .3 V .15 H .15 V .3 H -.15 V .15 H -.3 V -.15 H -.15 Z" fill="var(--pink)" />
          </g>
        )}
        {snake.map(([x, y], index) => (
          <g key={`${index}-${x}-${y}`} transform={`translate(${x + 0.5} ${y + 0.5})`}>
            <rect x="-0.43" y="-0.43" width="0.86" height="0.86" fill="var(--green)" opacity={index === 0 ? 1 : Math.max(0.4, 0.85 - index / Math.max(snake.length, 1) * 0.4)} />
            {index === 0 && (
              <g transform={`rotate(${angle})`} fill="var(--bg)">
                <rect x="0.1" y="-0.29" width="0.17" height="0.17" />
                <rect x="0.1" y="0.12" width="0.17" height="0.17" />
              </g>
            )}
          </g>
        ))}
        <rect width={width} height={height} fill="none" stroke="var(--line-bright)" strokeWidth="0.1" />
      </svg>
      <figcaption style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8, paddingTop: 12, color: "var(--muted)", fontSize: 12, textTransform: "uppercase" }}>
        <span><span style={{ color: "var(--green)" }}>■</span> Snake · <span style={{ color: "var(--pink)" }}>■</span> Food</span>
        <span>Coordinates start at top left · Y increases downward</span>
      </figcaption>
    </figure>
  );
}

export function SnakeReplay() {
  return <ReplayViewer game="snake" title="Snake" renderBoard={(frame) => <SnakeBoard frame={frame} />} />;
}
