#!/usr/bin/env python
"""Download the FutureX dataset from Hugging Face."""

from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import snapshot_download


def main() -> None:
    parser = argparse.ArgumentParser(description="Download FutureX-Online dataset.")
    parser.add_argument(
        "--repo",
        default="futurex-ai/Futurex-Online",
        help="Hugging Face dataset repo (default: futurex-ai/Futurex-Online)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/futurex",
        help="Directory to store the dataset snapshot",
    )
    parser.add_argument(
        "--revision",
        default=None,
        help="Optional dataset revision (branch, tag, or commit)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    snapshot_download(
        repo_id=args.repo,
        repo_type="dataset",
        revision=args.revision,
        local_dir=output_dir,
        local_dir_use_symlinks=False,
    )

    print(f"Downloaded {args.repo} to {output_dir}")


if __name__ == "__main__":
    main()
