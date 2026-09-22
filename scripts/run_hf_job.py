from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from huggingface_hub import run_job, sync_bucket, sync_job_volume, wait_for_job

from jevbench.config import add_run_options, config_from_args


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Launch the same NARCADE suite on Hugging Face Jobs"
    )
    add_run_options(parser)
    parser.add_argument("--flavor", default="a100-large")
    parser.add_argument("--image", default="nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04")
    parser.add_argument("--job-timeout", default="6h")
    parser.add_argument("--namespace")
    parser.add_argument("--detach", action="store_true")
    args = parser.parse_args(argv)
    try:
        config = config_from_args(args)
        secrets = config.secrets()
        if args.output_dir.exists() and any(args.output_dir.iterdir()):
            raise ValueError("output directory must be empty")
    except ValueError as error:
        parser.error(str(error))
    repository = Path(__file__).resolve().parents[1]
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="narcade-job-") as directory:
        stage = Path(directory)
        subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(stage / "dist")], cwd=repository, check=True
        )
        for name in ("bootstrap_job.sh", "requirements.lock"):
            shutil.copy2(repository / "hf" / name, stage / name)
        (stage / "config.json").write_text(json.dumps(asdict(config)))
        source = sync_job_volume(
            stage, "/workspace", remote_name=f"narcade-source-{stamp}", namespace=args.namespace
        )
        volume = sync_job_volume(
            output,
            "/outputs",
            remote_name=f"narcade-results-{stamp}",
            read_only=False,
            namespace=args.namespace,
        )
        job = run_job(
            image=args.image,
            command=["bash", "/workspace/bootstrap_job.sh"],
            env={"NARCADE_JOB_IMAGE": args.image},
            secrets=secrets,
            flavor=args.flavor,
            timeout=args.job_timeout,
            name=f"narcade-{stamp}",
            volumes=[source, volume],
            namespace=args.namespace,
        )
    remote_output = f"hf://buckets/{volume.source}/{volume.path or ''}"
    print(f"Job: {job.url}\nArtifacts: {remote_output}", flush=True)
    if args.detach:
        return
    finished = wait_for_job(job.id, namespace=args.namespace)
    sync_bucket(remote_output, str(output))
    print(f"Results: {output}")
    if finished.status.stage != "COMPLETED":
        raise SystemExit(f"Job ended with status {finished.status.stage}: {job.url}")


if __name__ == "__main__":
    main()
