# QUORUM — Source-to-Quorum Build Integrity

QUORUM verifies a **submitted source snapshot** instead of relying on a fixed demo artifact.

## Flow

```text
Source ZIP / GitHub URL
        ↓
Source snapshot + SHA-256
        ↓
Builder A ─┐
Builder B ─┼─ independent build workspaces
Builder C ─┘
        ↓
Artifact SHA-256 + Ed25519 attestation
        ↓
2-of-3 quorum
        ↓
ACCEPT / REJECT
        ↓
Hash-linked audit trail
```

## Start

From `C:\Quorum`:

```powershell
START_QUORUM.bat
```

Or:

```powershell
python backend\app.py
```

Open:

`http://127.0.0.1:5000/`

## Source input

Use **Upload source package** to submit a ZIP of a project, or enter a public GitHub repository URL.

The dashboard will show the source snapshot hash and file count. Verification is disabled until a source snapshot is loaded.

## Build modes

If the submitted source contains `pyproject.toml`, `setup.py`, or `setup.cfg`, each builder attempts a deterministic Python wheel build.

If it is not a Python package, QUORUM creates a deterministic source bundle artifact from the same source snapshot. This keeps the verification pipeline usable for general project source while making the artifact type explicit.

## Demos

After a real source is loaded, `Simulate 2-builder failure` runs the source pipeline and then simulates Builder B and C as unavailable without modifying the source or trusted keys.

`backend\demo\tamper_demo.py` mutates the current Builder-C artifact temporarily to demonstrate hash/signature protection and restores it afterward.
