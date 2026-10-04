# QUORUM Setup Guide

## 1. Requirements

- Windows 10/11
- Python 3.11+
- Internet access only if you want to load a public GitHub repository

Docker is not required for the hackathon demo.

## 2. Start

Run:

```powershell
START_QUORUM.bat
```

The first launch creates `.venv` and installs `requirements.txt`.

## 3. Use the dashboard

1. Open `http://127.0.0.1:5000/`.
2. Upload a source ZIP or load a public GitHub repository.
3. Confirm `SOURCE READY`.
4. Click `BUILD & VERIFY SOURCE`.
5. Review Builder A/B/C results.
6. Review the 2-of-3 quorum decision.
7. Open Audit Trail.

## 4. Important behavior

QUORUM will **not** verify a built-in sample project. No source submission means `SOURCE REQUIRED` and no acceptance decision.

Each verification run rebuilds the active source snapshot in separate builder workspaces and creates fresh Ed25519 attestations bound to the source snapshot hash.

## 5. Package builds

Python projects with packaging metadata are built with `python -m build --wheel --no-isolation` when build metadata is present.

For source projects without Python packaging metadata, QUORUM uses a deterministic source-bundle artifact. This is deliberately explicit in the builder result as `build_mode = source-bundle`.

## 6. Demo failure mode

After a source is loaded, use `Simulate 2-builder failure` to show:

```text
Builder A = VERIFIED
Builder B = FAILED
Builder C = FAILED
1 verified / 2 required
REJECT
```

Then click `BUILD & VERIFY SOURCE` again to return to the actual source result.
