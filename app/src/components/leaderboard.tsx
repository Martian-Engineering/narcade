"use client";

import { useState } from "react";
import { records, runLabel, gameNames, policyNames, isBaseline } from "@/data/results";

export function Leaderboard() {
  const games = [...new Set(records.map((row) => row.game))];
  const [game, setGame] = useState(games[0]);
  const [showBaselines, setShowBaselines] = useState(true);
  const rows = records.filter((row) => row.game === game && (showBaselines || !isBaseline(row.policy)))
    .sort((a, b) => b.aggregate.mean_score - a.aggregate.mean_score);
  const protocol = records.find((row) => row.game === game)!.protocol;
  const bestModel = Math.max(...rows.filter((row) => !isBaseline(row.policy)).map((row) => row.aggregate.mean_score));
  return (
    <div className="leaderboard-shell">
      <div className="leaderboard-controls">
        <div className="view-tabs" aria-label="Game">
          {games.map((id) => <button key={id} type="button" className={game === id ? "active" : ""}
            aria-pressed={game === id} onClick={() => setGame(id)}>{gameNames[id] || id}</button>)}
        </div>
        <button type="button" className={`baseline-toggle ${showBaselines ? "active" : ""}`}
          aria-pressed={showBaselines} onClick={() => setShowBaselines(!showBaselines)}>
          <span aria-hidden="true" />Baselines
        </button>
      </div>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Policy</th><th>Mean score</th><th>Range</th><th>Success</th>
            <th>P50 latency</th>{game === "minesweeper" && <th>Solve time</th>}</tr></thead>
          <tbody>{rows.map((row) => (
            <tr key={row.policy} className={isBaseline(row.policy) ? "baseline-row" : ""}>
              <th scope="row"><strong>{policyNames[row.policy] || row.policy}</strong>
                <small>{"hardware" in row.model ? String(row.model.hardware || row.model.kind) : row.model.kind}</small></th>
              <td className={row.aggregate.mean_score === bestModel && !isBaseline(row.policy) ? "leader-cell" : ""}>
                {row.aggregate.mean_score.toFixed(2)}</td>
              <td>{row.aggregate.min_score}–{row.aggregate.max_score}</td>
              <td>{Math.round(row.aggregate.success_rate * 100)}%</td>
              <td>{row.aggregate.p50_latency_ms.toFixed(1)} ms</td>
              {game === "minesweeper" && <td>{row.aggregate.mean_solve_seconds == null ? "—" : `${Number(row.aggregate.mean_solve_seconds).toFixed(2)} s`}</td>}
            </tr>
          ))}</tbody>
        </table>
      </div>
      <div className="table-note"><span>{runLabel}</span><span>Protocol {protocol.version} · {protocol.mode} · {protocol.difficulty}</span></div>
      <div className="table-note"><span>Higher scores are better. Solve time includes cleared boards only.</span></div>
    </div>
  );
}
