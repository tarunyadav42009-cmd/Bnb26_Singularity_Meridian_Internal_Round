"""CLI attestation helper for a current QUORUM run."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.pipeline.source_pipeline import current_run, create_attestation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("builder_id", choices=("builder-a", "builder-b", "builder-c"))
    args = parser.parse_args()
    run = current_run()
    if not run:
        raise SystemExit("No current source build run. Upload/build source first.")
    item = next((x for x in run.get("build_results", []) if x.get("builder_id") == args.builder_id), None)
    if not item or not item.get("success"):
        raise SystemExit("Builder artifact is not available in the current run.")
    artifact = Path(item["artifact_path"])
    path = Path(run["attestations_dir"]) / f"{args.builder_id}.json" if run.get("attestations_dir") else Path("data/runs/current/attestations") / f"{args.builder_id}.json"
    attestation = create_attestation(
        args.builder_id,
        artifact,
        run["source_hash"],
        run["run_id"],
        item["build_mode"],
        PROJECT_ROOT / path,
    )
    print(f"Attestation created: {PROJECT_ROOT / path}")
    print(attestation["artifact_hash"])


if __name__ == "__main__":
    main()
