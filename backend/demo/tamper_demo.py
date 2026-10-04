import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.verifier.verification import verify_all


def main():
    artifact = ROOT / "data" / "artifacts" / "builder-c" / "six-1.17.0-py2.py3-none-any.whl"
    backup = artifact.with_suffix(artifact.suffix + ".quorum-backup")

    if not artifact.exists():
        print(f"ERROR: Builder-C artifact not found: {artifact}")
        return 1

    print("=" * 60)
    print("          QUORUM - BUILDER C TAMPER DEMO")
    print("=" * 60)
    print("The original Builder-C artifact will be restored automatically.")

    shutil.copy2(artifact, backup)

    try:
        data = bytearray(artifact.read_bytes())
        if not data:
            print("ERROR: Artifact is empty.")
            return 1

        data[-1] ^= 0x01
        artifact.write_bytes(data)

        print()
        print("Tamper simulation applied to Builder-C.")
        print()

        report = verify_all()
        for result in report["builders"]:
            print(
                f"{result['builder_id']}: "
                f"{'VERIFIED' if result['verified'] else 'FAILED'} "
                f"(hash={'VALID' if result['hash_valid'] else 'INVALID'}, "
                f"signature={'VALID' if result['signature_valid'] else 'INVALID'})"
            )

        decision = report["decision"]
        print()
        print(f"Verified quorum : {decision['quorum']}/3")
        print(f"Required quorum : {decision['required_quorum']}")
        print(f"Outliers        : {', '.join(decision['outliers']) or 'NONE'}")
        print(f"STATUS          : {decision['status']}")
        return 0 if decision["status"] == "ACCEPT" else 1

    finally:
        shutil.move(str(backup), str(artifact))
        print()
        print("Original Builder-C artifact restored.")
        print("=" * 60)


if __name__ == "__main__":
    raise SystemExit(main())
