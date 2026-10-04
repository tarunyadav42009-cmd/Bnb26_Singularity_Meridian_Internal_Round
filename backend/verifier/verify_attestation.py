"""CLI verifier for the current source build run."""
import json

from verifier.verification import verify_all_builders


if __name__ == "__main__":
    print(json.dumps({"builders": verify_all_builders()}, indent=2))
