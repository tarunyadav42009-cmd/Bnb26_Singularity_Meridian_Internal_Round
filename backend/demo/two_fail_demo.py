"""CLI demonstration: two builders become unavailable for the submitted source."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app import perform_two_fail_demo


def main():
    report = perform_two_fail_demo()
    print("=" * 60)
    print("       QUORUM - TWO BUILDER FAILURE DEMO")
    print("=" * 60)
    if report.get("source_required"):
        print(report["message"])
        return 1
    for result in report.get("builders", []):
        print(
            f"{result['builder_id']}: "
            f"{'VERIFIED' if result['verified'] else 'FAILED'}"
        )
    decision = report["decision"]
    print()
    print(f"Verified quorum : {decision['quorum']}/3")
    print(f"Required quorum : {decision['required_quorum']}")
    print(f"STATUS          : {decision['status']}")
    return 0 if decision["status"] == "REJECT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
