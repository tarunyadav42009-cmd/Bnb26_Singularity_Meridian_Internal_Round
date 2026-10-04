"""Verify the current submitted-source build run."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CURRENT_RUN_DIR = PROJECT_ROOT / "data" / "runs" / "current"
BUILDERS = ("builder-a", "builder-b", "builder-c")


def calculate_sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_signature(public_key_b64: str, signature_b64: str, signed_data: bytes) -> bool:
    try:
        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
        public_key.verify(base64.b64decode(signature_b64), signed_data)
        return True
    except Exception:
        return False


def verify_builder(builder_id: str, run: dict) -> dict:
    result = {
        "builder_id": builder_id,
        "artifact": None,
        "artifact_hash": None,
        "actual_hash": None,
        "hash_valid": False,
        "signature_valid": False,
        "source_hash": run.get("source_hash"),
        "source_hash_valid": False,
        "attestation_valid": False,
        "build_mode": None,
        "verified": False,
        "error": None,
    }

    build_result = next(
        (item for item in run.get("build_results", []) if item.get("builder_id") == builder_id),
        None,
    )
    if not build_result:
        result["error"] = "Builder result not found in current run."
        return result

    result["build_mode"] = build_result.get("build_mode")
    if not build_result.get("success"):
        result["error"] = build_result.get("error", "Builder failed.")
        return result

    artifact_name = build_result.get("artifact")
    artifact_path = Path(build_result.get("artifact_path", ""))
    attestation_path = Path(build_result.get("attestation_path", ""))

    result["artifact"] = artifact_name

    if not artifact_path.exists():
        result["error"] = "Builder artifact is missing."
        return result

    if not attestation_path.exists():
        result["error"] = "Builder attestation is missing."
        return result

    try:
        attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    except Exception as error:
        result["error"] = f"Invalid attestation JSON: {error}"
        return result

    if attestation.get("builder_id") != builder_id:
        result["error"] = "Builder identity mismatch."
        return result

    if attestation.get("artifact") != artifact_name:
        result["error"] = "Attestation artifact mismatch."
        return result

    if attestation.get("source_hash") != run.get("source_hash"):
        result["error"] = "Attestation belongs to a different source snapshot."
        return result

    result["source_hash_valid"] = True
    expected_hash = attestation.get("artifact_hash")
    result["artifact_hash"] = expected_hash

    actual_hash = calculate_sha256(artifact_path)
    result["actual_hash"] = actual_hash
    result["hash_valid"] = actual_hash == expected_hash

    signed = {
        "builder_id": builder_id,
        "artifact": artifact_name,
        "artifact_hash": expected_hash,
        "source_hash": attestation.get("source_hash"),
        "hash_algorithm": attestation.get("hash_algorithm"),
        "signature_algorithm": attestation.get("signature_algorithm"),
        "build_mode": attestation.get("build_mode"),
        "run_id": attestation.get("run_id"),
    }
    canonical = json.dumps(signed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    result["signature_valid"] = verify_signature(
        attestation.get("public_key", ""),
        attestation.get("signature", ""),
        canonical,
    )
    result["attestation_valid"] = (
        result["source_hash_valid"]
        and result["signature_valid"]
        and result["hash_valid"]
    )
    result["verified"] = result["attestation_valid"]
    if not result["verified"]:
        result["error"] = "Cryptographic verification failed."
    return result


def verify_all_builders() -> list[dict]:
    run_file = CURRENT_RUN_DIR / "run.json"
    if not run_file.exists():
        return [
            {
                "builder_id": builder,
                "artifact": None,
                "artifact_hash": None,
                "hash_valid": False,
                "signature_valid": False,
                "source_hash_valid": False,
                "attestation_valid": False,
                "verified": False,
                "error": "No source build has been executed yet.",
            }
            for builder in BUILDERS
        ]

    run = json.loads(run_file.read_text(encoding="utf-8"))
    return [verify_builder(builder, run) for builder in BUILDERS]


def current_run() -> dict | None:
    run_file = CURRENT_RUN_DIR / "run.json"
    if not run_file.exists():
        return None
    try:
        return json.loads(run_file.read_text(encoding="utf-8"))
    except Exception:
        return None


if __name__ == "__main__":
    print(json.dumps({"builders": verify_all_builders()}, indent=2))
