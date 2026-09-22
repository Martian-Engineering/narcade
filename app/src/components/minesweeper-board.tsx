"use client";

import { ReplayViewer, type ReplayFrame } from "@/components/replay-viewer";

const clueColors = ["var(--muted)", "var(--cyan)", "var(--green)", "var(--pink)", "#ae9fff", "#ffbd73", "#8de6cf", "var(--ink)", "var(--muted)"];

export function MinesweeperBoard({ frame }: { frame: ReplayFrame }) {
  const lines = String(frame.state.board ?? "").trim().split("\n");
  const columns = (lines[0] ?? "").trim().split(/\s+/);
  const rows = lines.slice(1).map((line) => {
    const [label, ...cells] = line.trim().split(/\s+/);
    return { label, cells };
  });
  if (!rows.length) {
    return <p style={{ color: "var(--muted)" }}>No board state was recorded for this frame.</p>;
  }

  const visibleSafe = rows.reduce((sum, row) => sum + row.cells.filter((cell) => /^\d$/.test(cell)).length, 0);
  const selected = typeof frame.action === "string" ? frame.action.toUpperCase() : null;
  const width = columns.length;
  const height = rows.length;

  return (
    <figure style={{ margin: 0, width: "100%", maxWidth: 580, marginInline: "auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 12, marginBottom: 14, textTransform: "uppercase", color: "var(--muted)", fontSize: 14 }}>
        <span>Revealed <strong style={{ color: "var(--green)" }}>{visibleSafe}</strong></span>
        <span>Mines <strong style={{ color: "var(--pink)" }}>{String(frame.state.mines ?? frame.result.mines ?? "—")}</strong></span>
        <span>Next reveal <strong style={{ color: "var(--cyan)" }}>{selected ?? "—"}</strong></span>
      </div>
      <svg
        viewBox={`0 0 ${width + 1} ${height + 1}`}
        role="img"
        aria-label={`Minesweeper board, ${width} columns by ${height} rows. ${visibleSafe} safe squares visible.${selected ? ` Model selected ${selected} to reveal next.` : ""}`}
        style={{ display: "block", width: "100%", maxHeight: "65vh", background: "var(--bg)", border: "1px solid var(--line-bright)", boxShadow: "0 0 24px rgba(88,234,255,.04)" }}
      >
        {columns.map((column, index) => (
          <text key={column} x={index + 1.5} y={0.58} textAnchor="middle" dominantBaseline="middle" fill="var(--muted)" fontSize=".28">{column}</text>
        ))}
        {rows.map((row, y) => (
          <g key={row.label}>
            <text x=".5" y={y + 1.5} textAnchor="middle" dominantBaseline="middle" fill="var(--muted)" fontSize=".28">{row.label}</text>
            {row.cells.map((cell, x) => {
              const label = `${columns[x]}${row.label}`;
              const covered = cell === "#";
              const mine = cell === "*";
              const chosen = label === selected;
              return (
                <g key={label} transform={`translate(${x + 1} ${y + 1})`}>
                  <title>{label}: {covered ? "covered" : mine ? "revealed mine" : `${cell} adjacent mines`}{chosen ? "; next reveal" : ""}</title>
                  <rect x=".035" y=".035" width=".93" height=".93" fill={mine ? "#37152d" : covered ? "#272434" : "var(--panel)"} stroke={chosen ? "var(--cyan)" : "var(--line-bright)"} strokeWidth={chosen ? ".065" : ".018"} />
                  {covered && <path d="M .09 .87 V .09 H .87" fill="none" stroke="var(--muted)" strokeWidth=".025" opacity=".25" />}
                  {mine && (
                    <g stroke="var(--pink)" strokeWidth=".075">
                      <path d="M .5 .2 V .8 M .2 .5 H .8 M .28 .28 L .72 .72 M .28 .72 L .72 .28" />
                      <circle cx=".5" cy=".5" r=".16" fill="var(--pink)" />
                    </g>
                  )}
                  {!covered && !mine && cell !== "0" && (
                    <text x=".5" y=".53" textAnchor="middle" dominantBaseline="middle" fill={clueColors[Number(cell)] ?? "var(--ink)"} fontFamily="var(--font-pixel), monospace" fontSize=".48" fontWeight="700">{cell}</text>
                  )}
                  {chosen && <rect x=".39" y=".39" width=".22" height=".22" fill="var(--cyan)" opacity=".8" />}
                </g>
              );
            })}
          </g>
        ))}
      </svg>
      <figcaption style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: 8, paddingTop: 12, color: "var(--muted)", fontSize: 12, textTransform: "uppercase" }}>
        <span><span style={{ color: "var(--cyan)" }}>□</span> Next reveal · Blank = zero nearby mines</span>
        <span>Hidden mines stay hidden</span>
      </figcaption>
    </figure>
  );
}

export function MinesweeperReplay() {
  return <ReplayViewer game="minesweeper" title="Minesweeper" renderBoard={(frame) => <MinesweeperBoard frame={frame} />} />;
}
