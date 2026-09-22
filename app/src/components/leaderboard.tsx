"use client";

import { useMemo, useState } from "react";
import {
  gameOrder,
  games,
  modelLeaders,
  policies,
  policyOrder,
  results,
  type PublishedGameKey,
  type PolicyKey,
} from "@/data/results";

type View = "all" | PublishedGameKey;

function formatLatency(value: number) {
  if (value < 1) return "<1 ms";
  if (value >= 1000) return `${(value / 1000).toFixed(2)} s`;
  return `${Math.round(value)} ms`;
}

function rankForGame(game: PublishedGameKey, policy: PolicyKey, visible: PolicyKey[]) {
  const score = results[game][policy].mean;
  return visible.filter((candidate) => results[game][candidate].mean > score).length + 1;
}

export function Leaderboard() {
  const [view, setView] = useState<View>("all");
  const [showBaselines, setShowBaselines] = useState(true);
  const visible = useMemo(
    () => policyOrder.filter((policy) => showBaselines || policies[policy].kind === "model"),
    [showBaselines],
  );

  const ranked = useMemo(() => {
    if (view === "all") return visible;
    return [...visible].sort((a, b) => results[view][b].mean - results[view][a].mean);
  }, [view, visible]);

  return (
    <div className="leaderboard-shell">
      <div className="leaderboard-controls">
        <div className="view-tabs" aria-label="Leaderboard view">
          {(["all", ...gameOrder] as View[]).map((item) => (
            <button
              className={view === item ? "active" : ""}
              key={item}
              onClick={() => setView(item)}
              type="button"
              aria-pressed={view === item}
            >
              {item === "all" ? "All games" : games[item].label}
            </button>
          ))}
        </div>
        <button
          className={`baseline-toggle ${showBaselines ? "active" : ""}`}
          onClick={() => setShowBaselines((value) => !value)}
          type="button"
          aria-pressed={showBaselines}
        >
          <span aria-hidden="true" />
          Baselines
        </button>
      </div>

      <div className="table-wrap">
        {view === "all" ? (
          <table>
            <thead>
              <tr>
                <th>Policy</th>
                {gameOrder.map((game) => (
                  <th key={game}>
                    {games[game].label}
                    <small>{games[game].scoreLabel}</small>
                  </th>
                ))}
                <th>Leads<small>learned models</small></th>
              </tr>
            </thead>
            <tbody>
              {ranked.map((policy) => {
                const wins = gameOrder.filter((game) => modelLeaders[game] === policy).length;
                return (
                  <tr key={policy} className={policies[policy].kind === "baseline" ? "baseline-row" : ""}>
                    <ModelCell policy={policy} />
                    {gameOrder.map((game) => {
                      const result = results[game][policy];
                      const isLeader = modelLeaders[game] === policy;
                      return (
                        <td key={game} className={isLeader ? "leader-cell" : ""}>
                          <div className="score-value">
                            {games[game].format(result.mean)}
                            {isLeader && <span className="leader-chip">lead</span>}
                          </div>
                          <span className="score-range">
                            {games[game].format(result.min)}–{games[game].format(result.max)} range
                          </span>
                        </td>
                      );
                    })}
                    <td><span className="wins-count">{policies[policy].kind === "model" ? wins : "—"}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          <table>
            <thead>
              <tr>
                <th className="rank-column">Rank</th>
                <th>Policy</th>
                <th>Mean score<small>{games[view].scoreLabel}</small></th>
                <th>Episode range</th>
                <th>Success</th>
                <th>P50 latency<small>end to end</small></th>
              </tr>
            </thead>
            <tbody>
              {ranked.map((policy) => {
                const result = results[view][policy];
                const rank = rankForGame(view, policy, visible);
                return (
                  <tr key={policy} className={policies[policy].kind === "baseline" ? "baseline-row" : ""}>
                    <td className="rank-cell">{String(rank).padStart(2, "0")}</td>
                    <ModelCell policy={policy} />
                    <td><div className="score-value">{games[view].format(result.mean)}</div></td>
                    <td className="numeric-muted">{games[view].format(result.min)}–{games[view].format(result.max)}</td>
                    <td className="numeric-muted">{Math.round(result.success * 100)}%</td>
                    <td className="numeric-muted">{formatLatency(result.p50)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
      <div className="table-note">
        <span>Run 001 · 5 learned lanes · 3 seeds</span>
        <span>↑ Higher is better</span>
      </div>
    </div>
  );
}

function ModelCell({ policy }: { policy: PolicyKey }) {
  const meta = policies[policy];
  return (
    <th className="model-cell" scope="row">
      <span className="model-mark" style={{ backgroundColor: meta.color }} aria-hidden="true" />
      <span>
        <strong>{meta.label}</strong>
        <small>{meta.detail}</small>
      </span>
      {meta.kind === "baseline" && <span className="anchor-chip">anchor</span>}
      {meta.variant && <span className="variant-chip">variant</span>}
    </th>
  );
}
