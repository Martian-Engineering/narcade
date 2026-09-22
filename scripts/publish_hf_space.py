from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from huggingface_hub import HfApi


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and publish the NARCADE Docker Space")
    parser.add_argument("space_id", help="Hugging Face Space id, for example org/narcade")
    parser.add_argument(
        "--public",
        action="store_true",
        help="Make the Space public; deployments are private by default",
    )
    args = parser.parse_args()

    repository = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="narcade-space-") as directory:
        stage = Path(directory)
        wheel_dir = stage / "dist"
        subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(wheel_dir)],
            cwd=repository,
            check=True,
        )
        for name in ("README.md", "Dockerfile", "app.py", "job_runner.py", "requirements.lock"):
            shutil.copy2(repository / "hf_space" / name, stage / name)

        api = HfApi()
        api.create_repo(
            repo_id=args.space_id,
            repo_type="space",
            space_sdk="docker",
            private=not args.public,
            exist_ok=True,
        )
        api.update_repo_settings(
            repo_id=args.space_id,
            repo_type="space",
            private=not args.public,
        )
        api.upload_folder(
            repo_id=args.space_id,
            repo_type="space",
            folder_path=stage,
            commit_message="Publish NARCADE benchmark runner",
            delete_patterns=["dist/*"],
        )

    print(f"Published https://huggingface.co/spaces/{args.space_id}")


if __name__ == "__main__":
    main()
