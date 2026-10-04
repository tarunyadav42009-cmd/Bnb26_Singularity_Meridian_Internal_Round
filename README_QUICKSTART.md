# QUORUM — Multi-Builder Verifier

QUORUM compares signed artifact attestations from three builders and makes a configurable quorum decision. It includes a Flask API, a responsive dark dashboard, Ed25519 signature checks, SHA-256 artifact hashing, and a hash-chained local audit log.

## Quick start (Windows)

From the extracted project folder, open PowerShell and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m backend.app
```

Open **http://127.0.0.1:5000/** and click **Run verification**. Keep the terminal open while using the dashboard.

For the complete step-by-step setup, troubleshooting, API endpoints, and demo walkthrough, read [SETUP_GUIDE.md](SETUP_GUIDE.md).

## API

- `GET /api/health`
- `GET /api/builders`
- `POST /api/verify` with JSON such as `{"required_quorum": 2}`
- `GET /api/audit/status`
- `GET /api/audit/entries`

## Verification policy

A builder passes only when the artifact SHA-256 matches its attestation and its Ed25519 signature validates against the builder's trusted public key in `keys/`. The system accepts when at least the configured number of verified builders agree on the same artifact hash.

## Safety

This is a local demo. Do not expose the Flask development server publicly or use real private signing keys in a hackathon archive. The audit chain detects modifications to logged entries but is not an immutable external ledger.
