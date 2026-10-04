import json
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.verifier.verification import verify_all


def main() -> int:
    report = verify_all()

    print("=" * 60)
    print("             QUORUM - MULTI BUILDER VERIFIER")
    print("=" * 60)

    for result in report["builders"]:
        builder = result["builder_id"].upper()
        print()
        print("-" * 60)
        print(f"VERIFYING {builder}")
        print("-" * 60)
        print(f"Artifact         : {result['artifact']}")
        print(f"Expected Hash    : {result['expected_hash']}")
        print(f"Actual Hash      : {result['actual_hash']}")
        print(
            f"Artifact Hash    : "
            f"{'VALID' if result['hash_valid'] else 'INVALID'}"
        )
        print(
            f"Signature        : "
            f"{'VALID' if result['signature_valid'] else 'INVALID'}"
        )
        print(
            f"Status           : "
            f"{'VERIFIED' if result['verified'] else 'FAILED'}"
        )
        if not result["verified"]:
            print(f"Reason           : {result['reason']}")

    decision = report["decision"]

    print()
    print("=" * 60)
    print("                 QUORUM DECISION")
    print("=" * 60)
    print(f"Verified Builders : {decision['quorum']}/3")
    print(f"Required Quorum   : {decision['required_quorum']}")
    print(
        f"Quorum            : "
        f"{'REACHED' if decision['quorum'] >= decision['required_quorum'] else 'NOT REACHED'}"
    )
    print(
        "Outliers          : "
        + (", ".join(decision["outliers"]) if decision["outliers"] else "NONE")
    )
    print(f"STATUS            : {decision['status']}")
    print("=" * 60)

    return 0 if decision["status"] == "ACCEPT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
