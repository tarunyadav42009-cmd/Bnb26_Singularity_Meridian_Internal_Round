"""Runtime source -> builder -> artifact -> attestation pipeline for QUORUM."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

try:
    from backend.attestation.signer import generate_key_pair, sign_data
except ImportError:
    from attestation.signer import generate_key_pair, sign_data


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
SUBMISSIONS_DIR = DATA_DIR / "submissions"
CURRENT_SUBMISSION_DIR = SUBMISSIONS_DIR / "current"
CURRENT_SOURCE_DIR = CURRENT_SUBMISSION_DIR / "source"
RUNS_DIR = DATA_DIR / "runs"
CURRENT_RUN_DIR = RUNS_DIR / "current"
KEY_DIR = PROJECT_ROOT / "keys"

BUILDERS = ("builder-a", "builder-b", "builder-c")
DETERMINISTIC_EPOCH = 1704067200

EXCLUDED_NAMES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "build",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_source_files(source_dir: Path):
    for path in sorted(source_dir.rglob("*")):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(source_dir).parts
        if any(part in EXCLUDED_NAMES for part in relative_parts):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        if path.name.endswith("-private.key"):
            continue
        yield path


def source_tree_hash(source_dir: Path) -> str:
    """Hash relative file names + file bytes deterministically."""
    digest = hashlib.sha256()
    files = list(iter_source_files(source_dir))
    for path in files:
        relative = path.relative_to(source_dir).as_posix().encode("utf-8")
        content_hash = sha256_file(path).encode("ascii")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(content_hash)
    return digest.hexdigest()


def source_file_count(source_dir: Path) -> int:
    return sum(1 for _ in iter_source_files(source_dir))


def _fixed_zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name)
    info.date_time = (2024, 1, 1, 0, 0, 0)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def create_deterministic_source_bundle(source_dir: Path, output_path: Path) -> Path:
    """Create identical source artifacts for non-package projects."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in iter_source_files(source_dir):
            relative = path.relative_to(source_dir).as_posix()
            info = _fixed_zip_info(relative)
            archive.writestr(info, path.read_bytes())
    return output_path


def _has_python_packaging(source_dir: Path) -> bool:
    return any((source_dir / name).exists() for name in ("pyproject.toml", "setup.py", "setup.cfg"))


def _clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _copy_source(source_dir: Path, destination: Path) -> None:
    _clean_dir(destination)
    for path in iter_source_files(source_dir):
        relative = path.relative_to(source_dir)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def ensure_builder_keys(builder_id: str):
    private_path = KEY_DIR / f"{builder_id}-private.key"
    public_path = KEY_DIR / f"{builder_id}-public.key"
    KEY_DIR.mkdir(parents=True, exist_ok=True)

    if private_path.exists():
        private_key = Ed25519PrivateKey.from_private_bytes(private_path.read_bytes())
        public_key = private_key.public_key()
        public_path.write_bytes(public_key.public_bytes_raw())
        return private_key, public_key

    private_key, public_key = generate_key_pair()
    private_path.write_bytes(private_key.private_bytes_raw())
    public_path.write_bytes(public_key.public_bytes_raw())
    return private_key, public_key


def create_attestation(
    builder_id: str,
    artifact_path: Path,
    source_hash: str,
    run_id: str,
    build_mode: str,
    attestation_path: Path,
) -> dict[str, Any]:
    private_key, public_key = ensure_builder_keys(builder_id)
    artifact_hash = sha256_file(artifact_path)

    signed = {
        "builder_id": builder_id,
        "artifact": artifact_path.name,
        "artifact_hash": artifact_hash,
        "source_hash": source_hash,
        "hash_algorithm": "SHA-256",
        "signature_algorithm": "Ed25519",
        "build_mode": build_mode,
        "run_id": run_id,
    }
    canonical = json.dumps(signed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = sign_data(private_key, canonical)
    attestation = {
        **signed,
        "public_key": base64.b64encode(public_key.public_bytes_raw()).decode("ascii"),
        "signature": signature,
        "created_at": utc_now(),
    }
    attestation_path.parent.mkdir(parents=True, exist_ok=True)
    attestation_path.write_text(json.dumps(attestation, indent=2, sort_keys=True), encoding="utf-8")
    return attestation


def build_builder(
    builder_id: str,
    source_dir: Path,
    run_dir: Path,
    source_hash: str,
) -> dict[str, Any]:
    builder_dir = run_dir / "builders" / builder_id
    builder_source = builder_dir / "source"
    artifact_dir = builder_dir / "artifact"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    _copy_source(source_dir, builder_source)

    env = os.environ.copy()
    env["SOURCE_DATE_EPOCH"] = str(DETERMINISTIC_EPOCH)
    env["PYTHONHASHSEED"] = "0"
    env["TZ"] = "UTC"

    build_mode = "source-bundle"
    command = None
    stdout = ""
    stderr = ""
    artifact_path: Path | None = None

    if _has_python_packaging(builder_source):
        build_mode = "python-wheel"
        dist_dir = builder_source / ".quorum-dist"
        dist_dir.mkdir(parents=True, exist_ok=True)
        command = [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(dist_dir),
        ]
        try:
            result = subprocess.run(
                command,
                cwd=builder_source,
                capture_output=True,
                text=True,
                env=env,
                timeout=180,
            )
            stdout = result.stdout[-8000:]
            stderr = result.stderr[-8000:]
            if result.returncode != 0:
                return {
                    "builder_id": builder_id,
                    "success": False,
                    "build_mode": build_mode,
                    "error": "Python wheel build failed.",
                    "stdout": stdout,
                    "stderr": stderr,
                    "command": command,
                    "source_hash": source_hash,
                }
            wheels = sorted(dist_dir.glob("*.whl"))
            if not wheels:
                return {
                    "builder_id": builder_id,
                    "success": False,
                    "build_mode": build_mode,
                    "error": "Build succeeded but produced no wheel.",
                    "stdout": stdout,
                    "stderr": stderr,
                    "command": command,
                    "source_hash": source_hash,
                }
            artifact_path = artifact_dir / wheels[0].name
            shutil.copy2(wheels[0], artifact_path)
        except subprocess.TimeoutExpired:
            return {
                "builder_id": builder_id,
                "success": False,
                "build_mode": build_mode,
                "error": "Python build timed out after 180 seconds.",
                "source_hash": source_hash,
            }
        except FileNotFoundError:
            return {
                "builder_id": builder_id,
                "success": False,
                "build_mode": build_mode,
                "error": "Python build tooling is unavailable in this environment.",
                "source_hash": source_hash,
            }
    else:
        artifact_path = artifact_dir / "source-bundle.zip"
        create_deterministic_source_bundle(builder_source, artifact_path)

    artifact_hash = sha256_file(artifact_path)
    return {
        "builder_id": builder_id,
        "success": True,
        "build_mode": build_mode,
        "artifact": artifact_path.name,
        "artifact_path": str(artifact_path),
        "artifact_hash": artifact_hash,
        "source_hash": source_hash,
        "stdout": stdout,
        "stderr": stderr,
        "command": command,
    }


def run_pipeline(source_dir: Path | None = None) -> dict[str, Any]:
    source_dir = source_dir or CURRENT_SOURCE_DIR
    if not source_dir.exists() or source_file_count(source_dir) == 0:
        raise ValueError("No source code has been submitted.")

    source_hash = source_tree_hash(source_dir)
    file_count = source_file_count(source_dir)
    run_id = uuid.uuid4().hex[:12]

    if CURRENT_RUN_DIR.exists():
        shutil.rmtree(CURRENT_RUN_DIR)
    CURRENT_RUN_DIR.mkdir(parents=True, exist_ok=True)

    run_metadata = {
        "application": "QUORUM",
        "run_id": run_id,
        "created_at": utc_now(),
        "source_hash": source_hash,
        "source_file_count": file_count,
        "builders": list(BUILDERS),
        "required_quorum": 2,
    }
    (CURRENT_RUN_DIR / "run.json").write_text(
        json.dumps(run_metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    results = []
    attestations_dir = CURRENT_RUN_DIR / "attestations"
    for builder_id in BUILDERS:
        result = build_builder(builder_id, source_dir, CURRENT_RUN_DIR, source_hash)
        if result.get("success"):
            artifact_path = Path(result["artifact_path"])
            attestation_path = attestations_dir / f"{builder_id}.json"
            create_attestation(
                builder_id,
                artifact_path,
                source_hash,
                run_id,
                result["build_mode"],
                attestation_path,
            )
            result["attestation_path"] = str(attestation_path)
        results.append(result)

    run_metadata["build_results"] = results
    run_metadata["attestations_dir"] = str(attestations_dir)
    (CURRENT_RUN_DIR / "run.json").write_text(
        json.dumps(run_metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return run_metadata


def current_run() -> dict[str, Any] | None:
    run_file = CURRENT_RUN_DIR / "run.json"
    if not run_file.exists():
        return None
    try:
        return json.loads(run_file.read_text(encoding="utf-8"))
    except Exception:
        return None
