from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

from .models import DEFAULT_MODELS

KEV_PORT = urlsplit(DEFAULT_MODELS["kev"].base_url).port
KEV_CHECKPOINT = f"{DEFAULT_MODELS['kev'].artifact}@{DEFAULT_MODELS['kev'].artifact_revision}"


def _wait_for_kev(process: subprocess.Popen[str], timeout: float = 900.0) -> None:
    deadline = time.monotonic() + timeout
    url = f"http://127.0.0.1:{KEV_PORT}/v1/models"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Kev server exited with status {process.returncode}")
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (TimeoutError, urllib.error.URLError):
            time.sleep(2)
    raise RuntimeError("Kev server did not become ready within 15 minutes")


@contextmanager
def _kev_server(output_dir: Path, enabled: bool) -> Iterator[None]:
    if not enabled:
        yield
        return

    import torch

    device = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
    os.environ["NARCADE_HARDWARE"] = " · ".join(
        value for value in (os.environ.get("ACCELERATOR"), device) if value
    )
    log_path = output_dir / "kev-server.log"
    with log_path.open("w", encoding="utf-8") as log:
        env = dict(os.environ)
        env.setdefault("KEV_DTYPE", "bf16")
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "kev.serve",
                "--run",
                KEV_CHECKPOINT,
                "--port",
                str(KEV_PORT),
            ],
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            _wait_for_kev(process)
            yield
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
