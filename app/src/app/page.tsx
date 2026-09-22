import { Leaderboard } from "@/components/leaderboard";

const repository = "https://github.com/Martian-Engineering/narcade";

export default function Home() {
  return (
    <main>
      <div className="page-shell">
        <header className="site-header">
          <a className="brand" href="/" aria-label="NARCADE home">
            <span className="brand-icon" aria-hidden="true">N</span>
            <h1>NARCADE</h1>
          </a>
          <nav aria-label="Project links">
            <a href={`${repository}#readme`} target="_blank" rel="noreferrer">About ↗</a>
            <a href={repository} target="_blank" rel="noreferrer">GitHub ↗</a>
          </nav>
        </header>

        <p className="description">
          <strong>NARCADE</strong> (<em>N</em>on-<em>A</em>utoregressive <em>R</em>anking and
          {" "}<em>C</em>hoice <em>A</em>cross <em>D</em>iscrete <em>E</em>nvironments) measures how
          well decision models play deterministic games. Every policy receives the same seeds,
          rules, structured state, and legal actions. Game engines assign objective scores; no
          judge model is involved. Published results currently cover Minesweeper and Pong while
          Tetris and Snake are rerun under corrected control protocols. Full details live on GitHub.
        </p>

        <section className="results" aria-labelledby="results-title">
          <h2 className="sr-only" id="results-title">Benchmark results</h2>
          <Leaderboard />
        </section>

        <footer>
          <span>NARCADE / RUN 001</span>
          <a href="https://martian.engineering" target="_blank" rel="noreferrer">
            Made by Martian Engineering ↗
          </a>
        </footer>
      </div>
    </main>
  );
}
