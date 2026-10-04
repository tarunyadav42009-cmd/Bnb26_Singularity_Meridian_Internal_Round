from pathlib import Path
import hashlib
import json
import shutil
import sys
import urllib.request
import zipfile

from flask import Flask, jsonify, request, send_from_directory


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from core.quorum import evaluate_quorum
from audit.audit_log import AuditLog
from verifier.verification import verify_all_builders


# ============================================================
# CONFIG
# ============================================================

FRONTEND_DIR = PROJECT_ROOT / "frontend"

DATA_DIR = PROJECT_ROOT / "data"

SUBMISSIONS_DIR = DATA_DIR / "submissions"

CURRENT_SUBMISSION_DIR = SUBMISSIONS_DIR / "current"

CURRENT_SOURCE_DIR = CURRENT_SUBMISSION_DIR / "source"

AUDIT_FILE = DATA_DIR / "audit" / "audit.log"

REQUIRED_QUORUM = 2

MAX_SOURCE_ZIP_SIZE = 50 * 1024 * 1024


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = MAX_SOURCE_ZIP_SIZE


audit_log = AuditLog(
    str(AUDIT_FILE)
)


# ============================================================
# CORS
# Allows dashboard to work even when opened from another
# local development server.
# ============================================================

@app.after_request
def add_cors_headers(response):

    response.headers["Access-Control-Allow-Origin"] = "*"

    response.headers["Access-Control-Allow-Methods"] = (
        "GET, POST, OPTIONS"
    )

    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Accept"
    )

    return response


# ============================================================
# SAFE ZIP EXTRACTION
# ============================================================

def safe_extract_zip(
    archive_path: Path,
    destination: Path
):

    if destination.exists():

        shutil.rmtree(destination)

    destination.mkdir(
        parents=True,
        exist_ok=True
    )

    file_count = 0

    with zipfile.ZipFile(
        archive_path,
        "r"
    ) as archive:

        destination_root = (
            destination
            .resolve()
        )

        for member in archive.infolist():

            member_name = member.filename

            if not member_name:
                continue

            member_path = Path(
                member_name
            )

            if member_path.is_absolute():

                raise ValueError(
                    "Unsafe absolute ZIP path detected."
                )

            target = (
                destination
                / member_path
            ).resolve()

            try:

                target.relative_to(
                    destination_root
                )

            except ValueError:

                raise ValueError(
                    "Unsafe ZIP path detected."
                )

            if member.is_dir():

                target.mkdir(
                    parents=True,
                    exist_ok=True
                )

                continue

            target.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            with archive.open(
                member,
                "r"
            ) as source:

                with target.open(
                    "wb"
                ) as output:

                    shutil.copyfileobj(
                        source,
                        output
                    )

            file_count += 1

    return file_count


# ============================================================
# SHA-256
# ============================================================

def sha256_file(
    file_path: Path
):

    digest = hashlib.sha256()

    with file_path.open(
        "rb"
    ) as file:

        for chunk in iter(
            lambda: file.read(
                1024 * 1024
            ),
            b""
        ):

            digest.update(
                chunk
            )

    return digest.hexdigest()


# ============================================================
# SOURCE INFORMATION
# ============================================================

def count_source_files(
    source_dir: Path
):

    if not source_dir.exists():
        return 0

    return sum(
        1
        for path in source_dir.rglob("*")
        if path.is_file()
    )


def clear_current_submission():

    if CURRENT_SUBMISSION_DIR.exists():

        shutil.rmtree(
            CURRENT_SUBMISSION_DIR
        )

    CURRENT_SOURCE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


# ============================================================
# SOURCE ZIP UPLOAD
# ============================================================

@app.post("/api/source/upload")
def upload_source():

    try:

        uploaded_file = request.files.get(
            "source"
        )

        if uploaded_file is None:

            return jsonify({
                "application": "QUORUM",
                "status": "ERROR",
                "message": "Source ZIP file is required."
            }), 400

        filename = (
            uploaded_file.filename
            or ""
        ).strip()

        if not filename:

            return jsonify({
                "application": "QUORUM",
                "status": "ERROR",
                "message": "No source file selected."
            }), 400

        if not filename.lower().endswith(".zip"):

            return jsonify({
                "application": "QUORUM",
                "status": "ERROR",
                "message": "Only ZIP source packages are supported."
            }), 400

        SUBMISSIONS_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        package_path = (
            SUBMISSIONS_DIR
            / "current_source.zip"
        )

        uploaded_file.save(
            package_path
        )

        source_hash = sha256_file(
            package_path
        )

        clear_current_submission()

        file_count = safe_extract_zip(
            package_path,
            CURRENT_SOURCE_DIR
        )

        return jsonify({

            "application": "QUORUM",

            "status": "READY",

            "message":
                "Source package loaded successfully.",

            "filename":
                filename,

            "type":
                "ZIP SOURCE PACKAGE",

            "file_count":
                file_count,

            "source_hash":
                source_hash,

            "workspace":
                str(
                    CURRENT_SOURCE_DIR.relative_to(
                        PROJECT_ROOT
                    )
                )

        }), 200

    except zipfile.BadZipFile:

        return jsonify({

            "application": "QUORUM",

            "status": "ERROR",

            "message":
                "The uploaded file is not a valid ZIP archive."

        }), 400

    except Exception as error:

        return jsonify({

            "application": "QUORUM",

            "status": "ERROR",

            "message":
                "Source upload failed.",

            "error":
                str(error)

        }), 500


# ============================================================
# GITHUB SOURCE
# ============================================================

def parse_github_url(url):

    cleaned = (
        url.strip()
        .rstrip("/")
    )

    prefix = "https://github.com/"

    if not cleaned.startswith(prefix):

        raise ValueError(
            "Only public GitHub repository URLs are supported."
        )

    path = cleaned[len(prefix):]

    parts = [
        part
        for part in path.split("/")
        if part
    ]

    if len(parts) < 2:

        raise ValueError(
            "Invalid GitHub repository URL."
        )

    owner = parts[0]

    repo = parts[1]

    if repo.endswith(".git"):

        repo = repo[:-4]

    return owner, repo


@app.post("/api/source/github")
def github_source():

    try:

        payload = request.get_json(
            silent=True
        ) or {}

        url = (
            payload.get("url")
            or ""
        ).strip()

        if not url:

            return jsonify({
                "application": "QUORUM",
                "status": "ERROR",
                "message": "GitHub repository URL is required."
            }), 400

        owner, repo = parse_github_url(
            url
        )

        SUBMISSIONS_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        package_path = (
            SUBMISSIONS_DIR
            / "current_github.zip"
        )

        download_url = (
            f"https://api.github.com/repos/"
            f"{owner}/{repo}/zipball"
        )

        request_obj = urllib.request.Request(
            download_url,
            headers={
                "User-Agent":
                    "QUORUM-Build-Integrity-Demo",
                "Accept":
                    "application/vnd.github+json"
            }
        )

        with urllib.request.urlopen(
            request_obj,
            timeout=20
        ) as response:

            package_path.write_bytes(
                response.read()
            )

        source_hash = sha256_file(
            package_path
        )

        clear_current_submission()

        temporary_extract = (
            CURRENT_SUBMISSION_DIR
            / "_github_extract"
        )

        file_count = safe_extract_zip(
            package_path,
            temporary_extract
        )

        extracted_directories = [
            item
            for item in temporary_extract.iterdir()
            if item.is_dir()
        ]

        extracted_files = [
            item
            for item in temporary_extract.iterdir()
            if item.is_file()
        ]

        source_root = (
            extracted_directories[0]
            if len(extracted_directories) == 1
            and not extracted_files
            else temporary_extract
        )

        if source_root != CURRENT_SOURCE_DIR:

            if CURRENT_SOURCE_DIR.exists():

                shutil.rmtree(
                    CURRENT_SOURCE_DIR
                )

            shutil.copytree(
                source_root,
                CURRENT_SOURCE_DIR
            )

            shutil.rmtree(
                temporary_extract,
                ignore_errors=True
            )

        actual_file_count = count_source_files(
            CURRENT_SOURCE_DIR
        )

        return jsonify({

            "application":
                "QUORUM",

            "status":
                "READY",

            "message":
                "GitHub repository loaded successfully.",

            "filename":
                f"{owner}/{repo}",

            "type":
                "PUBLIC GITHUB REPOSITORY",

            "file_count":
                actual_file_count
                or file_count,

            "source_hash":
                source_hash,

            "workspace":
                str(
                    CURRENT_SOURCE_DIR.relative_to(
                        PROJECT_ROOT
                    )
                )

        }), 200

    except Exception as error:

        return jsonify({

            "application":
                "QUORUM",

            "status":
                "ERROR",

            "message":
                "GitHub repository could not be loaded.",

            "error":
                str(error)

        }), 400


# ============================================================
# BUILDER RESULT NORMALIZATION
# ============================================================

def normalize_builder_results(
    raw_results
):

    if isinstance(
        raw_results,
        dict
    ):

        results = raw_results.get(
            "builders",
            raw_results.get(
                "results",
                []
            )
        )

    elif isinstance(
        raw_results,
        list
    ):

        results = raw_results

    else:

        results = []

    normalized = []

    for result in results:

        artifact_hash = result.get(
            "artifact_hash"
        )

        hash_valid = bool(
            result.get(
                "hash_valid",
                False
            )
        )

        signature_valid = bool(
            result.get(
                "signature_valid",
                False
            )
        )

        verified = bool(
            result.get(
                "verified",
                False
            )
        )

        artifact_file_valid = bool(
            result.get(
                "artifact"
            )
            and artifact_hash
        )

        attestation_valid = (
            verified
            and hash_valid
            and signature_valid
        )

        normalized.append({

            "builder_id":
                result.get(
                    "builder_id",
                    "unknown"
                ),

            "artifact":
                result.get(
                    "artifact"
                ),

            "artifact_hash":
                artifact_hash,

            "hash_valid":
                hash_valid,

            "signature_valid":
                signature_valid,

            "verified":
                verified,

            "error":
                result.get(
                    "error"
                ),

            "artifact_file_valid":
                artifact_file_valid,

            "artifact_valid":
                artifact_file_valid,

            "artifact_exists":
                artifact_file_valid,

            "attestation_valid":
                attestation_valid,

            "actual_hash":
                artifact_hash
                if hash_valid
                else None,

            "expected_hash":
                artifact_hash,

            "result":
                "VERIFIED"
                if verified
                else "FAILED",

            "status":
                "VERIFIED"
                if verified
                else "FAILED",

            "reason":
                result.get(
                    "error"
                )
                or (
                    "All cryptographic checks passed."
                    if verified
                    else "Verification failed."
                )
        })

    return normalized


def get_verified_count(
    builders
):

    return sum(
        1
        for builder in builders
        if (
            builder.get("verified") is True
            and builder.get("artifact_hash")
        )
    )


# ============================================================
# REAL VERIFICATION
# ============================================================

def perform_verification():

    raw_results = verify_all_builders()

    builders = normalize_builder_results(
        raw_results
    )

    verified_count = get_verified_count(
        builders
    )

    decision = evaluate_quorum(
        builders,
        required_quorum=REQUIRED_QUORUM
    )

    audit_event = audit_log.append(

        event="BUILD_VERIFICATION",

        data={
            "builders": builders,
            "decision": decision,
            "verified_builder_count":
                verified_count
        }
    )

    audit_valid, audit_message = (
        audit_log.verify()
    )

    return {

        "application":
            "QUORUM",

        "status":
            decision["status"],

        "message":
            decision["message"],

        "builders":
            builders,

        "verified_builders":
            verified_count,

        "total_builders":
            len(builders),

        "quorum":
            decision["quorum"],

        "required":
            REQUIRED_QUORUM,

        "required_quorum":
            REQUIRED_QUORUM,

        "winning_hash":
            decision["winning_hash"],

        "winning_group":
            decision["winning_group"],

        "outliers":
            decision["outliers"],

        "decision":
            decision,

        "audit": {

            "valid":
                audit_valid,

            "message":
                audit_message
        },

        "audit_event":
            audit_event
    }


# ============================================================
# REJECT DEMO
# ============================================================

def perform_two_fail_demo():

    raw_results = verify_all_builders()

    builders = normalize_builder_results(
        raw_results
    )

    for builder in builders:

        if builder["builder_id"] in (
            "builder-b",
            "builder-c"
        ):

            builder["verified"] = False

            builder["hash_valid"] = False

            builder["signature_valid"] = False

            builder["artifact_file_valid"] = False

            builder["artifact_valid"] = False

            builder["artifact_exists"] = False

            builder["attestation_valid"] = False

            builder["actual_hash"] = None

            builder["result"] = "FAILED"

            builder["status"] = "FAILED"

            builder["error"] = (
                "Demo simulation: builder unavailable."
            )

            builder["reason"] = (
                "Demo simulation: builder unavailable."
            )

    verified_count = get_verified_count(
        builders
    )

    decision = evaluate_quorum(
        builders,
        required_quorum=REQUIRED_QUORUM
    )

    audit_event = audit_log.append(

        event="DEMO_TWO_BUILDER_FAILURE",

        data={
            "builders": builders,
            "decision": decision,
            "verified_builder_count":
                verified_count,
            "demo": True
        }
    )

    audit_valid, audit_message = (
        audit_log.verify()
    )

    return {

        "application":
            "QUORUM",

        "demo":
            True,

        "demo_name":
            "Two Builder Failure",

        "status":
            decision["status"],

        "message":
            decision["message"],

        "builders":
            builders,

        "verified_builders":
            verified_count,

        "total_builders":
            len(builders),

        "quorum":
            decision["quorum"],

        "required":
            REQUIRED_QUORUM,

        "required_quorum":
            REQUIRED_QUORUM,

        "winning_hash":
            decision["winning_hash"],

        "winning_group":
            decision["winning_group"],

        "outliers":
            decision["outliers"],

        "decision":
            decision,

        "audit": {

            "valid":
                audit_valid,

            "message":
                audit_message
        },

        "audit_event":
            audit_event
    }


# ============================================================
# DASHBOARD
# ============================================================

@app.get("/")
def dashboard():

    return send_from_directory(
        FRONTEND_DIR,
        "index.html"
    )


@app.get("/<path:filename>")
def frontend_files(
    filename
):

    return send_from_directory(
        FRONTEND_DIR,
        filename
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    return jsonify({

        "application":
            "QUORUM",

        "status":
            "healthy",

        "service":
            "quorum-backend",

        "message":
            "Backend is online."
    })


# ============================================================
# VERIFY API
# ============================================================

@app.route(
    "/api/verify",
    methods=["GET", "POST"]
)
def verify():

    try:

        return jsonify(
            perform_verification()
        ), 200

    except Exception as error:

        return jsonify({

            "application":
                "QUORUM",

            "status":
                "ERROR",

            "message":
                "Verification failed.",

            "error":
                str(error),

            "builders":
                [],

            "verified_builders":
                0,

            "total_builders":
                3,

            "quorum":
                0,

            "required":
                REQUIRED_QUORUM,

            "required_quorum":
                REQUIRED_QUORUM,

            "winning_hash":
                None,

            "winning_group":
                [],

            "outliers":
                [],

            "audit": {
                "valid":
                    False,
                "message":
                    "Verification failed."
            }

        }), 500


# ============================================================
# VERIFY ALIAS
# ============================================================

@app.route(
    "/api/verify-build",
    methods=["GET", "POST"]
)
def verify_build():

    return verify()


# ============================================================
# BUILDERS
# ============================================================

@app.get("/api/builders")
def builders():

    try:

        raw_results = verify_all_builders()

        normalized = normalize_builder_results(
            raw_results
        )

        return jsonify({

            "application":
                "QUORUM",

            "builders":
                normalized,

            "count":
                len(normalized),

            "verified":
                get_verified_count(
                    normalized
                )

        }), 200

    except Exception as error:

        return jsonify({

            "application":
                "QUORUM",

            "builders":
                [],

            "count":
                0,

            "verified":
                0,

            "error":
                str(error)

        }), 500


# ============================================================
# REJECT DEMO
# ============================================================

@app.route(
    "/api/demo/reject",
    methods=["GET", "POST"]
)
@app.route(
    "/api/demo/two-fail",
    methods=["GET", "POST"]
)
def two_fail_demo():

    try:

        return jsonify(
            perform_two_fail_demo()
        ), 200

    except Exception as error:

        return jsonify({

            "application":
                "QUORUM",

            "demo":
                True,

            "status":
                "ERROR",

            "message":
                "Demo failed.",

            "error":
                str(error)

        }), 500


# ============================================================
# AUDIT STATUS
# ============================================================

@app.get("/api/audit/status")
def audit_status():

    try:

        valid, message = (
            audit_log.verify()
        )

        event_count = 0

        if AUDIT_FILE.exists():

            event_count = len(
                [
                    line
                    for line in
                    AUDIT_FILE.read_text(
                        encoding="utf-8"
                    ).splitlines()
                    if line.strip()
                ]
            )

        return jsonify({

            "valid":
                valid,

            "status":
                "VALID"
                if valid
                else "TAMPERED",

            "message":
                message,

            "events":
                event_count,

            "event_count":
                event_count

        }), 200

    except Exception as error:

        return jsonify({

            "valid":
                False,

            "status":
                "ERROR",

            "message":
                str(error),

            "events":
                0,

            "event_count":
                0

        }), 500


# ============================================================
# AUDIT ENTRIES
# ============================================================

@app.get("/api/audit/entries")
def audit_entries():

    try:

        limit = request.args.get(
            "limit",
            default=10,
            type=int
        )

        limit = max(
            1,
            min(limit, 100)
        )

        entries = []

        if AUDIT_FILE.exists():

            lines = (
                AUDIT_FILE
                .read_text(
                    encoding="utf-8"
                )
                .splitlines()
            )

            for line in reversed(lines):

                if not line.strip():
                    continue

                try:

                    entries.append(
                        json.loads(line)
                    )

                except json.JSONDecodeError:

                    entries.append({

                        "event":
                            "CORRUPTED_ENTRY",

                        "raw":
                            line
                    })

                if len(entries) >= limit:
                    break

        return jsonify({

            "application":
                "QUORUM",

            "entries":
                entries,

            "count":
                len(entries)

        }), 200

    except Exception as error:

        return jsonify({

            "application":
                "QUORUM",

            "entries":
                [],

            "count":
                0,

            "error":
                str(error)

        }), 500


# ============================================================
# AUDIT ALIAS
# ============================================================

@app.get("/api/audit")
def audit():

    return audit_status()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("             QUORUM BACKEND")
    print("=" * 60)
    print()

    print(
        "Dashboard : http://127.0.0.1:5000/"
    )

    print(
        "Verify    : http://127.0.0.1:5000/api/verify"
    )

    print(
        "Reject    : http://127.0.0.1:5000/api/demo/reject"
    )

    print(
        "Audit     : http://127.0.0.1:5000/api/audit/status"
    )

    print()

    print("=" * 60)

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )