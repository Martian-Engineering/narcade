from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import RunConfig, add_run_options, config_from_args
from .suite import run_suite


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run NARCADE games locally or inside a Hugging Face Job"
    )
    parser.add_argument("--config", type=Path)
    add_run_options(parser)
    args = parser.parse_args(argv)
    try:
        config = (
            RunConfig(**json.loads(args.config.read_text()))
            if args.config
            else config_from_args(args)
        )
        status = run_suite(config, args.output_dir)
    except (OSError, ValueError, RuntimeError) as error:
        parser.error(str(error))
    raise SystemExit(status)
