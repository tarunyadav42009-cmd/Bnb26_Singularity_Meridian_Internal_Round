import base64
import json
import sys
from pathlib import Path

# --------------------------------------------------
# IMPORT PATH SETUP
# --------------------------------------------------

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent

sys.path.insert(0, str(BACKEND_DIR))

from attestation.signer import (
    generate_key_pair,
    sign_data
)

from core.hashing import sha256_file


# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

PROJECT_ROOT = CURRENT_DIR.parent.parent

ARTIFACT_ROOT = PROJECT_ROOT / "data" / "artifacts"
ATTESTATION_DIR = PROJECT_ROOT / "data" / "attestations"
KEY_DIR = PROJECT_ROOT / "keys"


# --------------------------------------------------
# BUILDER CONFIGURATION
# --------------------------------------------------

BUILDERS = {

    "builder-a": {
        "artifact": (
            ARTIFACT_ROOT /
            "six-1.17.0-py2.py3-none-any.whl"
        )
    },

    "builder-b": {
        "artifact": (
            ARTIFACT_ROOT /
            "builder-b" /
            "six-1.17.0-py2.py3-none-any.whl"
        )
    },

    "builder-c": {
        "artifact": (
            ARTIFACT_ROOT /
            "builder-c" /
            "six-1.17.0-py2.py3-none-any.whl"
        )
    }
}


# --------------------------------------------------
# CREATE ATTESTATION
# --------------------------------------------------

def create_attestation(builder_id):

    if builder_id not in BUILDERS:

        print(
            f"ERROR: Unknown builder: {builder_id}"
        )

        sys.exit(1)

    artifact_path = BUILDERS[
        builder_id
    ]["artifact"]

    artifact_name = artifact_path.name

    print("=" * 60)
    print(
        f"       QUORUM - {builder_id.upper()} ATTESTATION"
    )
    print("=" * 60)

    # --------------------------------------------------
    # 1. Check artifact
    # --------------------------------------------------

    print()
    print("[1/5] Checking artifact...")

    if not artifact_path.exists():

        print("ERROR: Artifact not found.")
        print(f"Path: {artifact_path}")

        sys.exit(1)

    print(f"Artifact: {artifact_path}")

    # --------------------------------------------------
    # 2. Calculate SHA-256
    # --------------------------------------------------

    print()
    print("[2/5] Calculating SHA-256...")

    artifact_hash = sha256_file(
        str(artifact_path)
    )

    print(f"SHA-256: {artifact_hash}")

    # --------------------------------------------------
    # 3. Generate Ed25519 key pair
    # --------------------------------------------------

    print()
    print("[3/5] Generating Ed25519 key pair...")

    KEY_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    private_key, public_key = (
        generate_key_pair()
    )

    private_bytes = (
        private_key.private_bytes_raw()
    )

    public_bytes = (
        public_key.public_bytes_raw()
    )

    private_key_path = (
        KEY_DIR /
        f"{builder_id}-private.key"
    )

    public_key_path = (
        KEY_DIR /
        f"{builder_id}-public.key"
    )

    private_key_path.write_bytes(
        private_bytes
    )

    public_key_path.write_bytes(
        public_bytes
    )

    print(
        f"Private key: {private_key_path}"
    )

    print(
        f"Public key : {public_key_path}"
    )

    # --------------------------------------------------
    # 4. Create signature
    # --------------------------------------------------

    print()
    print("[4/5] Creating digital signature...")

    attestation_data = {

        "builder_id": builder_id,

        "artifact": artifact_name,

        "artifact_hash": artifact_hash,

        "hash_algorithm": "SHA-256",

        "signature_algorithm": "Ed25519"
    }

    canonical_data = json.dumps(
        attestation_data,
        sort_keys=True,
        separators=(",", ":")
    ).encode("utf-8")

    signature = sign_data(
        private_key,
        canonical_data
    )

    public_key_b64 = (
        base64.b64encode(
            public_bytes
        ).decode("utf-8")
    )

    # --------------------------------------------------
    # 5. Save attestation
    # --------------------------------------------------

    print()
    print("[5/5] Saving attestation...")

    ATTESTATION_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    attestation = {

        **attestation_data,

        "public_key": public_key_b64,

        "signature": signature
    }

    attestation_path = (
        ATTESTATION_DIR /
        f"{builder_id}.json"
    )

    attestation_path.write_text(
        json.dumps(
            attestation,
            indent=4
        ),
        encoding="utf-8"
    )

    print()
    print("=" * 60)
    print("          ATTESTATION CREATED")
    print("=" * 60)

    print(f"Builder       : {builder_id}")
    print(f"Artifact      : {artifact_name}")
    print(f"SHA-256       : {artifact_hash}")
    print("Signature     : CREATED")
    print()
    print(
        f"Attestation   : {attestation_path}"
    )

    print("=" * 60)


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    if len(sys.argv) != 2:

        print()
        print("Usage:")
        print(
            "python backend\\attestation\\create_attestation.py builder-a"
        )
        print(
            "python backend\\attestation\\create_attestation.py builder-b"
        )
        print(
            "python backend\\attestation\\create_attestation.py builder-c"
        )

        sys.exit(1)

    builder_id = sys.argv[1].lower()

    create_attestation(builder_id)


if __name__ == "__main__":
    main()