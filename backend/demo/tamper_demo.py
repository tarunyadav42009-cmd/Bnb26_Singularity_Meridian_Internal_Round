"""CLI demonstration: tamper with Builder-C's current artifact and verify rejection/invalidity."""
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.pipeline.source_pipeline import CURRENT_SOURCE_DIR, run_pipeline
from backend.verifier.verification import verify_all_builders


def main():
    if not CURRENT_SOURCE_DIR.exists() or not any(CURRENT_SOURCE_DIR.rglob("*")):
        print("ERROR: Submit source before running the tamper demo.")
        return 1

    run_pipeline(CURRENT_SOURCE_DIR)
    current_run = ROOT / "data" / "runs" / "current"
    artifact = next((current_run / "builders" / "builder-c" / "artifact").glob("*"), None)
    if artifact is None:
        print("ERROR: Builder-C artifact was not generated.")
        return 1

    backup = artifact.with_suffix(artifact.suffix + ".backup")
    shutil.copy2(artifact, backup)

    try:
        data = bytearray(artifact.read_bytes())
        if not data:
            print("ERROR: Artifact is empty.")
            return 1
        data[-1] ^= 1
        artifact.write_bytes(data)

        print("=" * 60)
        print("          QUORUM - TAMPER DEMO")
        print("=" * 60)

        for result in verify_all_builders():
            print(
                f"{result['builder_id']}: "
                f"{'VERIFIED' if result['verified'] else 'FAILED'} "
                f"(hash={'VALID' if result['hash_valid'] else 'INVALID'}, "
                f"signature={'VALID' if result['signature_valid'] else 'INVALID'})"
            )

    finally:
        shutil.move(str(backup), str(artifact))
        print("Original Builder-C artifact restored.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
