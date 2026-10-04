"""CLI wrapper for Builder B against the active submitted source."""
import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.pipeline.source_pipeline import CURRENT_SOURCE_DIR, run_pipeline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(CURRENT_SOURCE_DIR))
    args = parser.parse_args()
    result = run_pipeline(Path(args.source))
    item = next(x for x in result["build_results"] if x["builder_id"] == "builder-b")
    print("=" * 60)
    print("             QUORUM - BUILDER B")
    print("=" * 60)
    print("Source:", args.source)
    print("Build mode:", item.get("build_mode"))
    print("Artifact:", item.get("artifact"))
    print("SHA-256:", item.get("artifact_hash"))
    print("Status:", "SUCCESS" if item.get("success") else "FAILED")
    print("=" * 60)


if __name__ == "__main__":
    main()
