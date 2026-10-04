# QUORUM — Hackathon Setup Guide (Windows)

This project is a local demo of multi-builder artifact integrity verification. It uses SHA-256 hashes, Ed25519 attestations, a configurable quorum decision, and a hash-chained audit log.

## Before you start

- Install Python 3.11 or newer from https://www.python.org/downloads/ (enable **Add Python to PATH**), or use the Windows `py` launcher.
- Extract the ZIP to a normal writable folder, for example `C:\\Users\\YourName\\Desktop\\Quorum`.
- Open that extracted `Quorum` folder in File Explorer. It must contain `backend`, `builders`, `data`, `frontend`, `keys`, `source`, and `requirements.txt`.

## One-time installation

1. Open the extracted `Quorum` folder in File Explorer.
2. Click the address bar, type `powershell`, and press Enter.
3. Run these commands one at a time:

```powershell
py --version
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

If PowerShell blocks activation, you can skip the activation command and use `.venv`'s Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If `py` is not recognized, reinstall Python and enable the Python Launcher, or replace `py` with `python` if that command works.

## Start the dashboard

In the same PowerShell window, from the `Quorum` project folder, run:

```powershell
py -m backend.app
```

Keep that terminal open. Open your browser at **http://127.0.0.1:5000/**. The dashboard is served by Flask and calls the real local verification API; no separate frontend server is needed.

Click **Run verification**. With the provided artifacts and attestations unchanged, the expected result is `ACCEPT`, 3/3 verified builders, and required quorum 2. A verification run appends an event to `data/audit/audit.log`.

## Useful checks

Open these URLs while the server is running:

- `http://127.0.0.1:5000/api/health` — backend health
- `http://127.0.0.1:5000/api/builders` — current verification results (read-only; does not append an audit event)
- `http://127.0.0.1:5000/api/audit/status` — audit-chain integrity
- `http://127.0.0.1:5000/api/audit/entries` — recent audit entries

Command-line verification:

```powershell
py -m backend.verifier.verify_attestation
```

## Hackathon demo flow

1. Open the dashboard and explain the three independent builder attestations.
2. Run verification and show the individual hash/signature checks.
3. Change required quorum from 2 to 3 and verify again to show the configurable policy (the provided clean sample passes both).
4. Show the audit trail and open `/api/audit/status` to demonstrate hash-chain validation.
5. If you want to demonstrate tamper detection, use the provided `backend/demo/tamper_demo.py` from the terminal and follow its output. Do not edit the wheel manually. Run it only when no other verification/demo is running, then rerun verification after it restores the artifact.

## Troubleshooting

- **Page does not open:** confirm the terminal still shows Flask running and the URL is exactly `http://127.0.0.1:5000/`.
- **`ModuleNotFoundError`:** activate `.venv` or install requirements using `.venv\\Scripts\\python.exe -m pip install -r requirements.txt`.
- **Builder reports `untrusted_public_key`:** the trusted public key in `keys/<builder>-public.key` does not match the key embedded in that builder's attestation. Do not regenerate keys casually; that changes the trust identity. Restore the matching project files or deliberately regenerate and re-sign attestations as a coordinated operation.
- **Artifact hash mismatch:** a wheel changed after its attestation was created. Restore the original artifact or rebuild and regenerate its attestation in a controlled workflow.
- **Port 5000 is in use:** stop the other local Flask process before starting this project.

## Security notes

This app is intended for a local hackathon demonstration. Keep it bound to `127.0.0.1`; do not expose Flask's development server to the public internet. Never use real production signing keys in a demo ZIP. The bundled sample keys/attestations are demonstration trust material, not production credentials. The audit chain is tamper-evident, not an immutable external ledger.
