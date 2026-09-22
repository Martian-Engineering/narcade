---
title: NARCADE
emoji: 🕹️
colorFrom: purple
colorTo: pink
sdk: docker
app_port: 7860
suggested_hardware: a100-large
suggested_storage: small
models:
  - jaredpalmer/kev-4b
  - convaiinnovations/laya
  - convaiinnovations/laya-typed-decisions
  - convaiinnovations/laya-multilingual
---

# NARCADE runner

The image supports two entry points:

- `python /app/app.py` starts the interactive Space for Laya smoke tests.
- `python /app/job_runner.py` runs a complete, sequential benchmark job against hosted Jev and
  OpenJev plus local Kev. Laya checkpoints are available as optional lanes.

The job runner loads one local model family at a time, records the Hugging Face hardware flavor and
GPU name, writes raw results plus `manifest.json` to `/outputs`, and returns a nonzero status when a
lane fails. Its paid-run defaults cap Tetris at 200 pieces and every episode at 2,000 decisions.
Open checkpoints use pinned revisions. Python dependencies and the Kev runtime use the versions in
`requirements.lock`.

The Space UI accepts only pinned Laya lanes and does not spend hosted-model credentials. Use the
Hugging Face Job launcher in the NARCADE repository for full benchmark runs.
