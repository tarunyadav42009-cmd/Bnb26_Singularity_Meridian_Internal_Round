import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path


# --------------------------------------------------
# QUORUM BUILDER A
# Deterministic Python Wheel Build
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SOURCE_DIR = PROJECT_ROOT / "source"

ARTIFACT_DIR = (
    PROJECT_ROOT
    / "data"
    / "artifacts"
)


def calculate_sha256(file_path):

    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:

        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b""
        ):
            sha256.update(chunk)

    return sha256.hexdigest()


def clean_old_build_files():

    folders = [
        SOURCE_DIR / "build",
        SOURCE_DIR / "dist",
        SOURCE_DIR / "six.egg-info"
    ]

    for folder in folders:

        if folder.exists():

            if folder.is_dir():
                shutil.rmtree(folder)

            else:
                folder.unlink()


def build_package():

    print("=" * 60)
    print("             QUORUM - BUILDER A")
    print("=" * 60)

    print()
    print("[1/5] Checking source code...")

    if not SOURCE_DIR.exists():

        print("ERROR: Source directory not found.")
        sys.exit(1)

    print(f"Source: {SOURCE_DIR}")

    # --------------------------------------------------
    # Fixed timestamp for reproducible builds
    # --------------------------------------------------

    print()
    print("[2/5] Setting deterministic build environment...")

    os.environ["SOURCE_DATE_EPOCH"] = "1704067200"

    print("SOURCE_DATE_EPOCH: 1704067200")

    # --------------------------------------------------
    # Build
    # --------------------------------------------------

    print()
    print("[3/5] Building Python package...")

    clean_old_build_files()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--outdir",
            str(SOURCE_DIR / "dist")
        ],
        cwd=SOURCE_DIR,
        capture_output=True,
        text=True,
        env=os.environ.copy()
    )

    if result.returncode != 0:

        print()
        print("BUILD FAILED")
        print()
        print(result.stdout)
        print(result.stderr)

        sys.exit(1)

    print("Build completed successfully.")

    # --------------------------------------------------
    # Copy artifact
    # --------------------------------------------------

    print()
    print("[4/5] Copying artifact...")

    wheels = list(
        (SOURCE_DIR / "dist").glob("*.whl")
    )

    if not wheels:

        print("ERROR: No wheel artifact found.")
        sys.exit(1)

    artifact = wheels[0]

    ARTIFACT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    destination = (
        ARTIFACT_DIR / artifact.name
    )

    shutil.copy2(
        artifact,
        destination
    )

    print(
        f"Artifact: {destination}"
    )

    # --------------------------------------------------
    # Hash
    # --------------------------------------------------

    print()
    print("[5/5] Calculating SHA-256...")

    artifact_hash = calculate_sha256(
        destination
    )

    print()
    print("=" * 60)
    print("              BUILD RESULT")
    print("=" * 60)

    print("Builder       : builder-a")
    print(f"Artifact      : {destination.name}")
    print(f"SHA-256       : {artifact_hash}")
    print("Build Status  : SUCCESS")

    print("=" * 60)


if __name__ == "__main__":
    build_package()