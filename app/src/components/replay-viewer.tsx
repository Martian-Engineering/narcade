"use client";

import { useEffect, useState, type ReactNode } from "react";

export type ReplayFrame = {
  // Game engines expose different JSON observations; renderers validate their own fields.
  state: Record<string, any>;
  result: Record<string, any>;
  action: string | null;
  step: number;
  latency_ms: number | null;
  probabilities: Record<string, number> | null;
  instructions: string;
  criteria: Record<string, string>;
};
type Episode = { id: string; model: string; seed: number; score: number; terminal_reason: string; frames: ReplayFrame[] };
type Recording = { protocol: string; mode: string; provenance: string; engine_revision: string; episodes: Episode[] };
const names: Record<string, string> = { jev: "Jev", openjev: "OpenJev", kev: "Kev", random: "Random", heuristic: "Heuristic" };
const games = ["tetris", "snake", "minesweeper"];

export function ReplayViewer({ game, title, renderBoard }: { game: string; title: string; renderBoard: (frame: ReplayFrame) => ReactNode }) {
  const [recording, setRecording] = useState<Recording | null>(null);
  const [error, setError] = useState("");
  const [model, setModel] = useState("jev");
  const [seed, setSeed] = useState(100);
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(2);
  useEffect(() => {
    const controller = new AbortController();
    fetch(`/replays/${game}.json`, { signal: controller.signal }).then(response => {
      if (!response.ok) throw new Error("Replay recording could not be loaded.");
      return response.json();
    }).then(setRecording).catch(error => { if (error.name !== "AbortError") setError(error.message); });
    return () => controller.abort();
  }, [game]);
  const episode = recording?.episodes.find(e => e.model === model && e.seed === seed);
  const frame = episode?.frames[index];
  const last = (episode?.frames.length ?? 1) - 1;
  useEffect(() => {
    if (!playing || index >= last) return;
    const timer = window.setTimeout(() => {
      setIndex(i => i + 1);
      if (index + 1 >= last) setPlaying(false);
    }, 1000 / speed);
    return () => window.clearTimeout(timer);
  }, [playing, index, last, speed]);
  function reset() { setIndex(0); setPlaying(false); }
  function seek(value: number) { setIndex(Math.max(0, Math.min(last, value))); setPlaying(false); }
  return <main className="page-shell replay-page">
    <header className="site-header"><a className="brand" href="/" aria-label="NARCADE home"><span className="brand-icon" aria-hidden="true">N</span><h1>NARCADE</h1></a><nav><a href="/">Leaderboard ↗</a></nav></header>
    <nav className="replay-games" aria-label="Game replays">{games.map(id => <a key={id} href={`/${id}`} aria-current={id === game ? "page" : undefined}>{id}</a>)}</nav>
    <div className="replay-heading"><h2>{title} / Replay</h2><span>Recorded decisions · {recording?.mode ?? "lockstep"}</span></div>
    <p className="replay-intro">Watch what the model saw and the action it chose. Each frame is the board before that action; the next frame shows its outcome.</p>
    {error && <p role="alert">{error}</p>}
    {!recording && !error && <p role="status">Loading recorded games…</p>}
    {recording && episode && frame && <>
      <div className="replay-selectors">
        <label>Player<select value={model} onChange={e => { setModel(e.target.value); reset(); }}>{[...new Set(recording.episodes.map(e => e.model))].map(id => <option key={id} value={id}>{names[id] ?? id}</option>)}</select></label>
        <label>Seed<select value={seed} onChange={e => { setSeed(Number(e.target.value)); reset(); }}>{recording.episodes.filter(e => e.model === model).map(e => <option key={e.id} value={e.seed}>{e.seed}</option>)}</select></label>
        <label>Playback<select value={speed} onChange={e => setSpeed(Number(e.target.value))}>{[1, 2, 5, 10, 20].map(n => <option key={n} value={n}>{n} decisions / sec</option>)}</select></label>
        <a className="replay-download" href={`/replays/${game}.json`} download>Download traces ↗</a>
      </div>
      <div className="replay-layout">
        <section className="replay-stage" aria-label={`${title} board`}>{renderBoard(frame)}</section>
        <aside className="replay-inspector">
          <div className="replay-step">{index === last ? "Final state" : `Decision ${index + 1} / ${last}`}</div>
          <div className="replay-action">{frame.action ?? "END OF TRACE"}</div>
          <p>{frame.action ? frame.criteria[frame.action] : episode.terminal_reason.replaceAll("_", " ")}</p>
          <dl><div><dt>Score now</dt><dd>{frame.result.score}</dd></div><div><dt>Final score</dt><dd>{episode.score}</dd></div><div><dt>Request latency</dt><dd>{frame.latency_ms == null ? "—" : `${frame.latency_ms.toFixed(1)} ms`}</dd></div></dl>
          {frame.probabilities && <div className="replay-probabilities"><h3>Returned probabilities</h3>{Object.entries(frame.probabilities).sort((a,b) => b[1] - a[1]).map(([action, probability]) => <div key={action} className={action === frame.action ? "chosen" : ""}><span>{action}</span><meter min={0} max={1} value={probability} aria-label={`${action} probability`} /><span>{(probability * 100).toFixed(0)}%</span></div>)}</div>}
        </aside>
      </div>
      <div className="replay-playback"><button onClick={() => seek(0)} aria-label="Restart replay">↺</button><button onClick={() => seek(index - 1)} disabled={index === 0} aria-label="Previous decision">←</button><button className="play-button" onClick={() => { if (index === last) setIndex(0); setPlaying(p => !p); }}>{playing ? "Pause" : index === last ? "Replay" : "Play"}</button><button onClick={() => seek(index + 1)} disabled={index === last} aria-label="Next decision">→</button><input aria-label="Replay position" type="range" min={0} max={last} value={index} onChange={e => seek(Number(e.target.value))} /><span>{index} / {last}</span></div>
      <details className="replay-raw"><summary>Exact state and instructions</summary><pre>{JSON.stringify({state:frame.state, instructions:frame.instructions, criteria:frame.criteria}, null, 2)}</pre></details>
      <p className="replay-provenance">Protocol {recording.protocol} · Engine {recording.engine_revision} · {recording.provenance} Playback speed is illustrative, not original wall-clock timing.</p>
    </>}
    <footer><span>NARCADE</span><a href="https://martian.engineering">Made by Martian Engineering ↗</a></footer>
  </main>;
}
