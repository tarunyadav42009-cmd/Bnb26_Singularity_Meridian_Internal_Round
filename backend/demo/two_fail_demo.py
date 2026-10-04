import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.verifier.verification import verify_all


def flip_last_byte(path: Path):
    data = bytearray(path.read_bytes())
    data[-1] ^= 0x01
    path.write_bytes(data)


def main():
    artifacts = [
        ROOT / "data" / "artifacts" / "builder-b" / "six-1.17.0-py2.py3-none-any.whl",
        ROOT / "data" / "artifacts" / "builder-c" / "six-1.17.0-py2.py3-none-any.whl",
    ]
    backups = [p.with_suffix(p.suffix + ".quorum-backup") for p in artifacts]

    if any(not p.exists() for p in artifacts):
        print("ERROR: Builder-B or Builder-C artifact is missing.")
        return 1

    for src, dst in zip(artifacts, backups):
        shutil.copy2(src, dst)

    try:
        for path in artifacts:
            flip_last_byte(path)

        print("=" * 60)
        print("       QUORUM - TWO BUILDER FAILURE DEMO")
        print("=" * 60)

        report = verify_all()
        for result in report["builders"]:
            print(
                f"{result['builder_id']}: "
                f"{'VERIFIED' if result['verified'] else 'FAILED'}"
            )

        decision = report["decision"]
        print()
        print(f"Verified quorum : {decision['quorum']}/3")
        print(f"Required quorum : {decision['required_quorum']}")
        print(f"STATUS          : {decision['status']}")
        return 0 if decision["status"] == "ACCEPT" else 1

    finally:
        for backup, target in zip(backups, artifacts):
            shutil.move(str(backup), str(target))
        print("Original Builder-B and Builder-C artifacts restored.")


if __name__ == "__main__":
    raise SystemExit(main())
