"use client";

import { ReplayViewer, type ReplayFrame } from "@/components/replay-viewer";

const shapes: Record<string, string[]> = {
  I: ["####"],
  O: ["##", "##"],
  T: [".#.", "###"],
  S: [".##", "##."],
  Z: ["##.", ".##"],
  J: ["#..", "###"],
  L: ["..#", "###"],
};

function NextPiece({ name }: { name: string }) {
  const shape = shapes[name];
  if (!shape) return <span>{name || "—"}</span>;
  return (
    <svg viewBox="0 0 120 70" role="img" aria-label={`Next piece: ${name}`} style={{ width: 120, height: 70, display: "block", marginTop: 12 }}>
      {shape.flatMap((row, y) => [...row].map((cell, x) => cell === "#" && (
        <rect key={`${x}-${y}`} x={(120 - shape[0].length * 24) / 2 + x * 24} y={(70 - shape.length * 24) / 2 + y * 24} width="21" height="21" fill="var(--pink)" stroke="#ffc0e9" strokeWidth="1" />
      )))}
    </svg>
  );
}

function TetrisBoard({ frame }: { frame: ReplayFrame }) {
  const board: string[] = Array.isArray(frame.state.board)
    ? frame.state.board.filter((row: unknown): row is string => typeof row === "string")
    : [];
  const rows = board.length || 20;
  const columns = Math.max(10, ...board.map((row) => row.length));
  const cell = 24;
  const metric = (key: string) => frame.result[key] ?? frame.state[key] ?? "—";

  return (
    <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "24px 36px", alignItems: "flex-start", padding: "20px 12px" }}>
      <div style={{ width: "min(100%, 300px)" }}>
        <svg
          viewBox={`0 0 ${columns * cell} ${rows * cell}`}
          role="img"
          aria-label={`Tetris board at decision ${frame.step}. Cyan blocks are locked; pink blocks are the active piece.`}
          style={{ width: "100%", height: "auto", display: "block", background: "#080810", border: "1px solid var(--line-bright)", boxShadow: "0 0 28px rgba(88,234,255,.07)" }}
        >
          {Array.from({ length: columns + 1 }, (_, x) => <line key={`column-${x}`} x1={x * cell} y1={0} x2={x * cell} y2={rows * cell} stroke="#171723" strokeWidth=".6" />)}
          {Array.from({ length: rows + 1 }, (_, y) => <line key={`row-${y}`} x1={0} y1={y * cell} x2={columns * cell} y2={y * cell} stroke="#171723" strokeWidth=".6" />)}
          {board.flatMap((row, y) => [...row].map((block, x) => {
            if (block !== "#" && block !== "@") return null;
            const active = block === "@";
            return (
              <g key={`${x}-${y}`}>
                <rect x={x * cell + 1.5} y={y * cell + 1.5} width={cell - 3} height={cell - 3} fill={active ? "var(--pink)" : "var(--cyan)"} fillOpacity={active ? 1 : .75} />
                <path d={`M${x * cell + 3} ${y * cell + cell - 4}V${y * cell + 3}H${x * cell + cell - 4}`} fill="none" stroke={active ? "#ffb4e3" : "#b6f7ff"} strokeWidth="1" />
              </g>
            );
          }))}
        </svg>
        <p style={{ margin: "12px 0 0", color: "var(--muted)", fontSize: 12, textTransform: "uppercase", textAlign: "center" }}>
          <span style={{ color: "var(--cyan)" }}>■ Locked</span>{" · "}<span style={{ color: "var(--pink)" }}>■ Active</span>
        </p>
        {!board.length && <p style={{ color: "var(--muted)", textAlign: "center" }}>Board unavailable in this frame.</p>}
      </div>
      <div style={{ minWidth: 120, display: "flex", flexDirection: "column", gap: 24, textTransform: "uppercase" }}>
        {[ ["Score", metric("score")], ["Lines", metric("lines")], ["Pieces", metric("pieces")] ].map(([label, value]) => (
          <div key={String(label)}>
            <div style={{ color: "var(--muted)", fontSize: 12, letterSpacing: ".06em" }}>{label}</div>
            <div style={{ color: "var(--green)", fontSize: 28, fontVariantNumeric: "tabular-nums", textShadow: "0 0 12px rgba(116,255,134,.25)" }}>{String(value)}</div>
          </div>
        ))}
        <div>
          <div style={{ color: "var(--muted)", fontSize: 12, letterSpacing: ".06em" }}>Next piece</div>
          <NextPiece name={String(frame.state.next_piece ?? "")} />
        </div>
      </div>
    </div>
  );
}

export function TetrisReplay() {
  return <ReplayViewer game="tetris" title="Tetris" renderBoard={(frame) => <TetrisBoard frame={frame} />} />;
}
