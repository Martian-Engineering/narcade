import { Leaderboard } from "@/components/leaderboard";

const metrics = [
  { value: "03", label: "Learned models" },
  { value: "03", label: "Game environments" },
  { value: "45", label: "Total episodes" },
  { value: "00", label: "Invalid actions" },
];

const games = [
  { index: "01", name: "Minesweeper", detail: "9 × 9 · 8 mines", score: "safe squares" },
  { index: "02", name: "Tetris", detail: "10 × 20 · 200 pieces", score: "arcade points" },
  { index: "03", name: "Pong", detail: "medium bot · first to 3", score: "points scored" },
];

export default function Home() {
  return (
    <main id="top">
      <header className="site-header">
        <a className="brand" href="#top" aria-label="NARCADE home">
          <span className="brand-icon" aria-hidden="true">N</span>
          <span>NARCADE</span>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#results">Results</a>
          <a href="#method">Method</a>
        </nav>
        <a className="maker-link" href="https://martian.engineering" target="_blank" rel="noreferrer">
          Martian Engineering ↗
        </a>
      </header>

      <div className="page-shell">
        <section className="intro" aria-labelledby="page-title">
          <p className="eyebrow"><span /> Model gameplay benchmark · Run 001</p>
          <h1 id="page-title">Which model<br />plays best?</h1>
          <p className="intro-copy">
            <strong>N</strong>on-<strong>A</strong>utoregressive <strong>R</strong>anking and <strong>C</strong>hoice
            {" "}<strong>A</strong>cross <strong>D</strong>iscrete <strong>E</strong>nvironments. Same seeds, same rules,
            objective scores.
          </p>
        </section>

        <section className="metric-grid" aria-label="Run summary">
          {metrics.map((metric) => (
            <div className="metric" key={metric.label}>
              <strong>{metric.value}</strong>
              <span>{metric.label}</span>
            </div>
          ))}
        </section>

        <section className="results-section" id="results" aria-labelledby="results-title">
          <div className="section-heading">
            <div>
              <p className="section-label">01 / Results</p>
              <h2 id="results-title">Leaderboard</h2>
            </div>
            <div className="run-status">
              <span aria-hidden="true" />
              Preliminary · 3 seeds
            </div>
          </div>
          <Leaderboard />
        </section>

        <section className="method-section" id="method" aria-labelledby="method-title">
          <div className="method-copy">
            <p className="section-label">02 / Method</p>
            <h2 id="method-title">A scoreboard,<br />not a vibe check.</h2>
            <p>
              Models receive structured game state and choose from bounded legal actions. The
              engine assigns every score; no judge model is involved.
            </p>
          </div>

          <div className="protocol-list" aria-label="Benchmark protocol">
            <div><span>Seeds</span><strong>100 · 101 · 102</strong></div>
            <div><span>Episodes</span><strong>3 per policy / game</strong></div>
            <div><span>Pong mode</span><strong>Lockstep vs seeded bot</strong></div>
            <div><span>Timing</span><strong>End-to-end latency</strong></div>
          </div>
        </section>

        <section className="game-list" aria-label="Benchmark games">
          {games.map((game) => (
            <article key={game.name}>
              <span className="game-index">{game.index}</span>
              <h3>{game.name}</h3>
              <p>{game.detail}</p>
              <span className="game-score">↑ {game.score}</span>
            </article>
          ))}
        </section>

        <aside className="run-note">
          <span>Run note</span>
          <p>Three seeds validate the harness. A stable public ranking should use at least 20.</p>
        </aside>

        <footer>
          <div className="footer-brand">NARCADE <span>/ 001</span></div>
          <p>Models play. The scoreboard decides.</p>
          <a href="https://martian.engineering" target="_blank" rel="noreferrer">
            Made by Martian Engineering ↗
          </a>
        </footer>
      </div>
    </main>
  );
}
