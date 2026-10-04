from __future__ import annotations

import hashlib
import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from audit.audit_log import AuditLog
from core.quorum import evaluate_quorum
from pipeline.source_pipeline import (
    CURRENT_SOURCE_DIR,
    CURRENT_SUBMISSION_DIR,
    RUNS_DIR,
    current_run,
    run_pipeline,
    source_file_count,
    source_tree_hash,
)
from verifier.verification import verify_all_builders


FRONTEND_DIR = PROJECT_ROOT / "frontend"
DATA_DIR = PROJECT_ROOT / "data"
SUBMISSIONS_DIR = DATA_DIR / "submissions"
SOURCE_META = CURRENT_SUBMISSION_DIR / "source.json"
AUDIT_FILE = DATA_DIR / "audit" / "audit.log"
REQUIRED_QUORUM = 2
MAX_SOURCE_ZIP_SIZE = 50 * 1024 * 1024

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_SOURCE_ZIP_SIZE

audit_log = AuditLog(str(AUDIT_FILE))


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept"
    return response


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_extract_zip(archive_path: Path, destination: Path) -> int:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    count = 0

    with zipfile.ZipFile(archive_path, "r") as archive:
        for member in archive.infolist():
            if not member.filename:
                continue
            member_path = Path(member.filename)
            if member_path.is_absolute():
                raise ValueError("Unsafe absolute ZIP path detected.")
            target = (destination / member_path).resolve()
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise ValueError("Unsafe ZIP path detected.") from exc

            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member, "r") as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            count += 1
    return count


def clear_source_only():
    if CURRENT_SUBMISSION_DIR.exists():
        shutil.rmtree(CURRENT_SUBMISSION_DIR)
    CURRENT_SOURCE_DIR.mkdir(parents=True, exist_ok=True)


def save_source_metadata(meta: dict):
    CURRENT_SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_META.write_text(
        json.dumps(meta, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def read_source_metadata() -> dict | None:
    if not SOURCE_META.exists():
        return None
    try:
        return json.loads(SOURCE_META.read_text(encoding="utf-8"))
    except Exception:
        return None


def source_status_payload() -> dict:
    meta = read_source_metadata()
    has_source = CURRENT_SOURCE_DIR.exists() and source_file_count(CURRENT_SOURCE_DIR) > 0
    current = current_run()
    return {
        "application": "QUORUM",
        "ready": has_source,
        "filename": meta.get("filename") if meta else None,
        "type": meta.get("type") if meta else None,
        "file_count": source_file_count(CURRENT_SOURCE_DIR) if has_source else 0,
        "source_hash": source_tree_hash(CURRENT_SOURCE_DIR) if has_source else None,
        "run_ready": current is not None,
        "run_id": current.get("run_id") if current else None,
    }


def normalize_results(results):
    normalized = []
    for result in results:
        artifact_hash = result.get("artifact_hash")
        hash_valid = bool(result.get("hash_valid", False))
        signature_valid = bool(result.get("signature_valid", False))
        source_hash_valid = bool(result.get("source_hash_valid", False))
        verified = bool(result.get("verified", False))
        artifact_valid = bool(result.get("artifact") and artifact_hash)
        attestation_valid = bool(result.get("attestation_valid", False))
        normalized.append({
            "builder_id": result.get("builder_id", "unknown"),
            "artifact": result.get("artifact"),
            "artifact_hash": artifact_hash,
            "actual_hash": result.get("actual_hash"),
            "hash_valid": hash_valid,
            "signature_valid": signature_valid,
            "source_hash_valid": source_hash_valid,
            "attestation_valid": attestation_valid,
            "verified": verified,
            "artifact_file_valid": artifact_valid,
            "artifact_valid": artifact_valid,
            "artifact_exists": artifact_valid,
            "build_mode": result.get("build_mode"),
            "error": result.get("error"),
            "reason": result.get("error") or ("All cryptographic checks passed." if verified else "Verification failed."),
            "result": "VERIFIED" if verified else "FAILED",
            "status": "VERIFIED" if verified else "FAILED",
            "source_hash": result.get("source_hash"),
        })
    return normalized


def verified_count(builders):
    return sum(1 for item in builders if item.get("verified") is True and item.get("artifact_hash"))


def perform_verification():
    if not CURRENT_SOURCE_DIR.exists() or source_file_count(CURRENT_SOURCE_DIR) == 0:
        return {
            "application": "QUORUM",
            "status": "PENDING",
            "message": "No source code has been submitted.",
            "source_required": True,
            "builders": [],
            "verified_builders": 0,
            "total_builders": 3,
            "quorum": 0,
            "required": REQUIRED_QUORUM,
            "required_quorum": REQUIRED_QUORUM,
            "winning_hash": None,
            "winning_group": [],
            "outliers": [],
            "decision": {
                "status": "PENDING",
                "quorum": 0,
                "required": REQUIRED_QUORUM,
                "required_quorum": REQUIRED_QUORUM,
                "winning_hash": None,
                "winning_group": [],
                "outliers": [],
                "message": "No source code has been submitted.",
            },
            "audit": {"valid": True, "message": "Awaiting source submission."},
        }

    run = run_pipeline(CURRENT_SOURCE_DIR)
    builders = normalize_results(verify_all_builders())
    count = verified_count(builders)
    decision = evaluate_quorum(builders, required_quorum=REQUIRED_QUORUM)

    audit_event = audit_log.append(
        event="BUILD_VERIFICATION",
        data={
            "source": {
                "source_hash": run["source_hash"],
                "file_count": run["source_file_count"],
                "run_id": run["run_id"],
            },
            "builders": builders,
            "decision": decision,
            "verified_builder_count": count,
        },
    )
    audit_valid, audit_message = audit_log.verify()

    return {
        "application": "QUORUM",
        "status": decision["status"],
        "message": decision["message"],
        "source_required": False,
        "source": {
            "filename": read_source_metadata().get("filename") if read_source_metadata() else "Submitted source",
            "type": read_source_metadata().get("type") if read_source_metadata() else "SOURCE",
            "source_hash": run["source_hash"],
            "file_count": run["source_file_count"],
            "run_id": run["run_id"],
        },
        "builders": builders,
        "verified_builders": count,
        "total_builders": len(builders),
        "quorum": decision["quorum"],
        "required": REQUIRED_QUORUM,
        "required_quorum": REQUIRED_QUORUM,
        "winning_hash": decision["winning_hash"],
        "winning_group": decision["winning_group"],
        "outliers": decision["outliers"],
        "decision": decision,
        "audit": {"valid": audit_valid, "message": audit_message},
        "audit_event": audit_event,
    }


def perform_two_fail_demo():
    if not CURRENT_SOURCE_DIR.exists() or source_file_count(CURRENT_SOURCE_DIR) == 0:
        return {
            "application": "QUORUM",
            "status": "PENDING",
            "message": "Submit source code before running the failure demo.",
            "demo": True,
            "source_required": True,
        }

    # Build and verify the real submitted source first.
    run = run_pipeline(CURRENT_SOURCE_DIR)
    builders = normalize_results(verify_all_builders())

    for builder in builders:
        if builder["builder_id"] in {"builder-b", "builder-c"}:
            builder.update({
                "verified": False,
                "hash_valid": False,
                "signature_valid": False,
                "source_hash_valid": False,
                "attestation_valid": False,
                "artifact_file_valid": False,
                "artifact_valid": False,
                "artifact_exists": False,
                "actual_hash": None,
                "result": "FAILED",
                "status": "FAILED",
                "error": "Demo simulation: builder unavailable.",
                "reason": "Demo simulation: builder unavailable.",
            })

    count = verified_count(builders)
    decision = evaluate_quorum(builders, required_quorum=REQUIRED_QUORUM)
    audit_event = audit_log.append(
        event="DEMO_TWO_BUILDER_FAILURE",
        data={
            "source_hash": run["source_hash"],
            "run_id": run["run_id"],
            "builders": builders,
            "decision": decision,
            "verified_builder_count": count,
            "demo": True,
        },
    )
    audit_valid, audit_message = audit_log.verify()
    return {
        "application": "QUORUM",
        "demo": True,
        "demo_name": "Two Builder Failure",
        "status": decision["status"],
        "message": decision["message"],
        "source_required": False,
        "source": {
            "source_hash": run["source_hash"],
            "file_count": run["source_file_count"],
            "run_id": run["run_id"],
        },
        "builders": builders,
        "verified_builders": count,
        "total_builders": 3,
        "quorum": decision["quorum"],
        "required": REQUIRED_QUORUM,
        "required_quorum": REQUIRED_QUORUM,
        "winning_hash": decision["winning_hash"],
        "winning_group": decision["winning_group"],
        "outliers": decision["outliers"],
        "decision": decision,
        "audit": {"valid": audit_valid, "message": audit_message},
        "audit_event": audit_event,
    }


@app.get("/")
def dashboard():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:filename>")
def frontend_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


@app.get("/api/health")
def health():
    return jsonify({
        "application": "QUORUM",
        "status": "healthy",
        "service": "quorum-backend",
        "message": "Backend is online.",
    })


@app.get("/api/source/status")
def source_status():
    return jsonify(source_status_payload())


@app.post("/api/source/upload")
def upload_source():
    try:
        uploaded = request.files.get("source")
        if not uploaded or not uploaded.filename:
            return jsonify({"application": "QUORUM", "status": "ERROR", "message": "Source ZIP file is required."}), 400
        if not uploaded.filename.lower().endswith(".zip"):
            return jsonify({"application": "QUORUM", "status": "ERROR", "message": "Only ZIP source packages are supported."}), 400

        SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
        package = SUBMISSIONS_DIR / "current_source.zip"
        uploaded.save(package)

        clear_source_only()
        count = safe_extract_zip(package, CURRENT_SOURCE_DIR)
        source_hash = source_tree_hash(CURRENT_SOURCE_DIR)

        meta = {
            "filename": uploaded.filename,
            "type": "ZIP SOURCE PACKAGE",
            "file_count": count,
            "source_hash": source_hash,
        }
        save_source_metadata(meta)
        if RUNS_DIR.exists() and (RUNS_DIR / "current").exists():
            shutil.rmtree(RUNS_DIR / "current")

        return jsonify({
            "application": "QUORUM",
            "status": "READY",
            "message": "Source package loaded. Build & Verify is now available.",
            **meta,
        }), 200

    except zipfile.BadZipFile:
        return jsonify({"application": "QUORUM", "status": "ERROR", "message": "Uploaded file is not a valid ZIP archive."}), 400
    except Exception as error:
        return jsonify({"application": "QUORUM", "status": "ERROR", "message": "Source upload failed.", "error": str(error)}), 500


@app.post("/api/source/github")
def github_source():
    try:
        payload = request.get_json(silent=True) or {}
        url = str(payload.get("url") or "").strip().rstrip("/")
        prefix = "https://github.com/"
        if not url.startswith(prefix):
            raise ValueError("Only public GitHub repository URLs are supported.")
        parts = [part for part in url[len(prefix):].split("/") if part]
        if len(parts) < 2:
            raise ValueError("Invalid GitHub repository URL.")
        owner, repo = parts[:2]
        repo = repo.removesuffix(".git")

        SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
        package = SUBMISSIONS_DIR / "current_github.zip"
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        api_req = urllib.request.Request(
            api_url,
            headers={
                "User-Agent": "QUORUM-Build-Integrity",
                "Accept": "application/vnd.github+json",
            },
        )
        with urllib.request.urlopen(api_req, timeout=20) as response:
            repo_info = json.loads(response.read().decode("utf-8"))

        default_branch = repo_info.get("default_branch") or "main"
        download_url = f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{default_branch}"
        req = urllib.request.Request(
            download_url,
            headers={"User-Agent": "QUORUM-Build-Integrity"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            package.write_bytes(response.read())

        clear_source_only()
        temp = CURRENT_SUBMISSION_DIR / "_github"
        safe_extract_zip(package, temp)
        roots = [x for x in temp.iterdir() if x.is_dir()]
        root = roots[0] if len(roots) == 1 else temp
        if CURRENT_SOURCE_DIR.exists():
            shutil.rmtree(CURRENT_SOURCE_DIR)
        shutil.copytree(root, CURRENT_SOURCE_DIR)
        shutil.rmtree(temp, ignore_errors=True)

        count = source_file_count(CURRENT_SOURCE_DIR)
        source_hash = source_tree_hash(CURRENT_SOURCE_DIR)
        meta = {
            "filename": f"{owner}/{repo}",
            "type": "PUBLIC GITHUB REPOSITORY",
            "file_count": count,
            "source_hash": source_hash,
        }
        save_source_metadata(meta)
        if RUNS_DIR.exists() and (RUNS_DIR / "current").exists():
            shutil.rmtree(RUNS_DIR / "current")

        return jsonify({
            "application": "QUORUM",
            "status": "READY",
            "message": "GitHub source snapshot loaded. Build & Verify is now available.",
            **meta,
        }), 200

    except Exception as error:
        return jsonify({"application": "QUORUM", "status": "ERROR", "message": "GitHub repository could not be loaded.", "error": str(error)}), 400


@app.route("/api/verify", methods=["GET", "POST"])
def verify():
    try:
        result = perform_verification()
        return jsonify(result), 200
    except Exception as error:
        return jsonify({
            "application": "QUORUM",
            "status": "ERROR",
            "message": "Source build/verification failed.",
            "error": str(error),
            "source_required": False,
        }), 500


@app.route("/api/verify-build", methods=["GET", "POST"])
def verify_build():
    return verify()


@app.get("/api/builders")
def builders():
    if current_run() is None:
        return jsonify({"application": "QUORUM", "builders": [], "count": 0, "verified": 0, "message": "No source build has been executed."}), 200
    results = normalize_results(verify_all_builders())
    return jsonify({
        "application": "QUORUM",
        "builders": results,
        "count": len(results),
        "verified": verified_count(results),
    }), 200


@app.route("/api/demo/reject", methods=["GET", "POST"])
@app.route("/api/demo/two-fail", methods=["GET", "POST"])
def two_fail_demo():
    try:
        return jsonify(perform_two_fail_demo()), 200
    except Exception as error:
        return jsonify({"application": "QUORUM", "demo": True, "status": "ERROR", "message": "Demo failed.", "error": str(error)}), 500


@app.get("/api/audit/status")
def audit_status():
    valid, message = audit_log.verify()
    entries = audit_log.entries()
    return jsonify({
        "valid": valid,
        "status": "VALID" if valid else "TAMPERED",
        "message": message,
        "events": len(entries),
        "event_count": len(entries),
    }), 200


@app.get("/api/audit/entries")
def audit_entries():
    limit = max(1, min(request.args.get("limit", 10, type=int), 100))
    entries = list(reversed(audit_log.entries()))[:limit]
    return jsonify({"application": "QUORUM", "entries": entries, "count": len(entries)}), 200


@app.get("/api/audit")
def audit():
    return audit_status()


if __name__ == "__main__":
    print()
    print("=" * 60)
    print("             QUORUM BACKEND")
    print("=" * 60)
    print("Dashboard : http://127.0.0.1:5000/")
    print("Health    : http://127.0.0.1:5000/api/health")
    print("Verify    : POST http://127.0.0.1:5000/api/verify")
    print("Source    : POST http://127.0.0.1:5000/api/source/upload")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=True)
