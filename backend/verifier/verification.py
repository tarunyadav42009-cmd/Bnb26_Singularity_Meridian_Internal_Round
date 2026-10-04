import base64
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PublicKey
)


# ============================================================
# PATHS
# ============================================================

CURRENT_DIR = Path(__file__).resolve().parent

BACKEND_DIR = CURRENT_DIR.parent

PROJECT_ROOT = BACKEND_DIR.parent

ARTIFACT_ROOT = (
    PROJECT_ROOT
    / "data"
    / "artifacts"
)

ATTESTATION_DIR = (
    PROJECT_ROOT
    / "data"
    / "attestations"
)


# ============================================================
# BUILDER ARTIFACTS
# ============================================================

BUILDER_ARTIFACTS = {

    "builder-a":
        ARTIFACT_ROOT
        / "six-1.17.0-py2.py3-none-any.whl",

    "builder-b":
        ARTIFACT_ROOT
        / "builder-b"
        / "six-1.17.0-py2.py3-none-any.whl",

    "builder-c":
        ARTIFACT_ROOT
        / "builder-c"
        / "six-1.17.0-py2.py3-none-any.whl"
}


BUILDERS = [
    "builder-a",
    "builder-b",
    "builder-c"
]


# ============================================================
# SHA-256
# ============================================================

def calculate_sha256(file_path):

    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:

        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b""
        ):

            sha256.update(chunk)

    return sha256.hexdigest()


# ============================================================
# SIGNATURE VERIFICATION
# ============================================================

def verify_signature(
    public_key_b64,
    signature_b64,
    signed_data
):

    try:

        public_key_bytes = (
            base64.b64decode(
                public_key_b64
            )
        )

        signature = (
            base64.b64decode(
                signature_b64
            )
        )

        public_key = (
            Ed25519PublicKey
            .from_public_bytes(
                public_key_bytes
            )
        )

        public_key.verify(
            signature,
            signed_data
        )

        return True

    except Exception:

        return False


# ============================================================
# SINGLE BUILDER
# ============================================================

def verify_builder(builder_id):

    result = {

        "builder_id":
            builder_id,

        "artifact":
            None,

        "artifact_hash":
            None,

        "hash_valid":
            False,

        "signature_valid":
            False,

        "verified":
            False,

        "error":
            None
    }


    # --------------------------------------------------------
    # ATTESTATION
    # --------------------------------------------------------

    attestation_file = (
        ATTESTATION_DIR
        / f"{builder_id}.json"
    )

    if not attestation_file.exists():

        result["error"] = (
            "Attestation file not found."
        )

        return result


    try:

        with attestation_file.open(
            "r",
            encoding="utf-8"
        ) as file:

            attestation = json.load(file)

    except Exception as error:

        result["error"] = (
            f"Invalid attestation JSON: {error}"
        )

        return result


    # --------------------------------------------------------
    # IDENTITY
    # --------------------------------------------------------

    if (
        attestation.get("builder_id")
        != builder_id
    ):

        result["error"] = (
            "Builder identity mismatch."
        )

        return result


    artifact_name = (
        attestation.get("artifact")
    )

    expected_hash = (
        attestation.get("artifact_hash")
    )

    public_key = (
        attestation.get("public_key")
    )

    signature = (
        attestation.get("signature")
    )


    if not all([
        artifact_name,
        expected_hash,
        public_key,
        signature
    ]):

        result["error"] = (
            "Incomplete attestation."
        )

        return result


    result["artifact"] = artifact_name

    result["artifact_hash"] = (
        expected_hash
    )


    # --------------------------------------------------------
    # ARTIFACT
    # --------------------------------------------------------

    artifact_path = (
        BUILDER_ARTIFACTS
        .get(builder_id)
    )

    if artifact_path is None:

        result["error"] = (
            "Unknown builder."
        )

        return result


    if not artifact_path.exists():

        result["error"] = (
            "Artifact not found."
        )

        return result


    # --------------------------------------------------------
    # ARTIFACT NAME CHECK
    # --------------------------------------------------------

    if artifact_name != artifact_path.name:

        result["error"] = (
            "Attestation artifact name mismatch."
        )

        return result


    # --------------------------------------------------------
    # HASH
    # --------------------------------------------------------

    actual_hash = calculate_sha256(
        artifact_path
    )

    result["hash_valid"] = (
        actual_hash
        == expected_hash
    )


    # --------------------------------------------------------
    # SIGNED DATA
    # --------------------------------------------------------

    signed_data = {

        "builder_id":
            builder_id,

        "artifact":
            artifact_name,

        "artifact_hash":
            expected_hash,

        "hash_algorithm":
            attestation.get(
                "hash_algorithm"
            ),

        "signature_algorithm":
            attestation.get(
                "signature_algorithm"
            )
    }


    canonical_data = json.dumps(
        signed_data,
        sort_keys=True,
        separators=(",", ":")
    ).encode("utf-8")


    # --------------------------------------------------------
    # SIGNATURE
    # --------------------------------------------------------

    result["signature_valid"] = (
        verify_signature(
            public_key,
            signature,
            canonical_data
        )
    )


    # --------------------------------------------------------
    # FINAL BUILDER STATUS
    # --------------------------------------------------------

    result["verified"] = (
        result["hash_valid"]
        and
        result["signature_valid"]
    )


    return result


# ============================================================
# ALL BUILDERS
# ============================================================

def verify_all_builders():

    results = []

    for builder_id in BUILDERS:

        result = verify_builder(
            builder_id
        )

        results.append(
            result
        )

    return results


# ============================================================
# CLI TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("       QUORUM - VERIFICATION ENGINE")
    print("=" * 60)

    results = verify_all_builders()

    for result in results:

        print()
        print(
            result["builder_id"].upper()
        )

        print(
            "Hash      :",
            "VALID"
            if result["hash_valid"]
            else "INVALID"
        )

        print(
            "Signature :",
            "VALID"
            if result["signature_valid"]
            else "INVALID"
        )

        print(
            "Status    :",
            "VERIFIED"
            if result["verified"]
            else "FAILED"
        )

        if result["error"]:

            print(
                "Error     :",
                result["error"]
            )