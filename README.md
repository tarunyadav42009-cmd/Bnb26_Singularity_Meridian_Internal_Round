# QUORUM

## Multi-Builder Software Build Integrity Verification

**QUORUM** is a software supply-chain security system designed to determine whether a software build can be trusted even when one or more build environments may be compromised.

Instead of trusting a single build server, QUORUM uses **independent builder results**, **SHA-256 artifact verification**, **Ed25519 cryptographic attestations**, and a configurable **2-of-3 quorum policy** to make a final trust decision.

> **Trust should come from consensus, not from a single builder.**

---

## Problem

Modern software is often built by automated infrastructure. If a build server is compromised, a malicious or modified artifact could potentially be distributed as a legitimate build.

A traditional single-builder model looks like:

```text
Source
  ↓
Single Builder
  ↓
Artifact
  ↓
Trust
```

If that builder is compromised, the verification process itself can be compromised.

QUORUM changes the trust model:

```text
                 Source
                   ↓
        ┌──────────┼──────────┐
        ↓          ↓          ↓
     Builder A  Builder B  Builder C
        ↓          ↓          ↓
     Artifact    Artifact    Artifact
        ↓          ↓          ↓
      SHA-256    SHA-256    SHA-256
        ↓          ↓          ↓
     Ed25519    Ed25519    Ed25519
        └──────────┼──────────┘
                   ↓
              QUORUM ENGINE
                   ↓
               2 of 3
                   ↓
          ACCEPT / REJECT
                   ↓
            Audit Trail
```

---

## Core Idea

QUORUM follows the principle:

> **A software build is trusted only when the required independent builder consensus is achieved.**

With the default **2-of-3** policy:

| Builder State | Quorum | Decision |
|---|---:|---|
| A ✅ B ✅ C ✅ | 3/3 | ACCEPT |
| A ✅ B ✅ C ❌ | 2/3 | ACCEPT |
| A ✅ B ❌ C ❌ | 1/3 | REJECT |
| A ❌ B ❌ C ❌ | 0/3 | REJECT |

A successfully verified builder with a different artifact hash can also be identified as an **outlier** when another hash reaches quorum.

---

# Features

## 1. Multi-Builder Verification

QUORUM verifies results from:

- Builder A
- Builder B
- Builder C

Each builder has its own artifact and cryptographic attestation.

---

## 2. SHA-256 Artifact Integrity

Every generated artifact is hashed using SHA-256.

Example:

```text
SHA-256

4bbb0c9e5e2acb67374a42fd8720bc60010b7e69e28b3c21c3760b5c2aaa6b17
```

The verifier compares the calculated artifact hash against the attested value.

---

## 3. Ed25519 Cryptographic Attestations

Each builder signs its attestation using Ed25519.

The verifier checks:

```text
Artifact Hash
      +
Digital Signature
      ↓
Cryptographically Verified Builder
```

A builder does not participate in quorum unless its verification succeeds.

---

## 4. 2-of-3 Quorum Consensus

The core trust policy uses a configurable threshold.

Default:

```text
Required quorum = 2
Builders        = 3
Policy          = 2-of-3
```

This means a single failed or compromised builder cannot automatically determine the final result.

---

## 5. Outlier Detection

If verified builders produce different artifact hashes, QUORUM identifies builders outside the winning hash group.

Example:

```text
Builder A → HASH-X ✅
Builder B → HASH-X ✅
Builder C → HASH-Y ✅
```

Decision:

```text
Winning group → A, B
Quorum        → 2/3
Outlier       → C
Status        → ACCEPT
```

This allows the system to tolerate a single divergent builder while still identifying the disagreement.

---

## 6. Tamper-Evident Audit Trail

Every verification decision is recorded in a hash-linked audit log.

Each event contains:

```text
Timestamp
Event
Data
Previous Hash
Entry Hash
```

The chain is verified sequentially.

Conceptually:

```text
GENESIS
   ↓
ENTRY 1
   ↓
ENTRY 2
   ↓
ENTRY 3
   ↓
ENTRY 4
```

If a historical entry is modified, the chain verification detects the inconsistency.

> The audit mechanism is **tamper-evident**, not tamper-proof.

---

## 7. Live Dashboard

The QUORUM dashboard provides a security-console style interface showing:

- API connectivity
- Builder verification status
- SHA-256 results
- Signature results
- Attestation status
- Quorum strength
- Winning builder group
- Outlier builders
- Final ACCEPT / REJECT decision
- Audit-chain status
- Recent verification events

---

## 8. Failure Simulation

QUORUM includes a controlled demonstration mode for simulating two unavailable builders.

Example:

```text
Builder A → VERIFIED
Builder B → FAILED
Builder C → FAILED

Verified builders → 1/3
Required quorum   → 2

RESULT → REJECT
```

The simulation does not intentionally corrupt the real cryptographic keys or artifacts.

---

# Source Input

The dashboard provides a **Source Input** section where a software project can be supplied as:

```text
Source ZIP
```

or through a:

```text
Public GitHub Repository URL
```

A supplied source package can be stored in the submission workspace and assigned a SHA-256 source-package hash.

### Current implementation note

The current cryptographic verification demo is based on the configured `six` project build artifacts already present in the repository. The source-ingestion interface is implemented separately from the existing fixed demo-builder pipeline.

A production-ready version should connect the submitted source snapshot directly to isolated Builder A/B/C build environments before generating fresh attestations.

---

# Security Architecture

```text
                    USER SOURCE
                         │
                         ▼
               SOURCE SNAPSHOT
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
     BUILDER A       BUILDER B       BUILDER C
          │              │              │
       BUILD            BUILD            BUILD
          │              │              │
       ARTIFACT        ARTIFACT        ARTIFACT
          │              │              │
       SHA-256          SHA-256          SHA-256
          │              │              │
       Ed25519          Ed25519          Ed25519
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                  VERIFICATION
                         │
                         ▼
                  QUORUM ENGINE
                         │
                    2 OF 3 POLICY
                         │
                  ┌──────┴──────┐
                  ▼             ▼
               ACCEPT         REJECT
                  │
                  ▼
             AUDIT LOG
                  │
                  ▼
              DASHBOARD
```

---

# Project Structure

```text
Quorum/
│
├── backend/
│   ├── app.py
│   │
│   ├── attestation/
│   │   ├── __init__.py
│   │   ├── create_attestation.py
│   │   ├── signer.py
│   │   └── test_signer.py
│   │
│   ├── audit/
│   │   ├── __init__.py
│   │   └── audit_log.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── hashing.py
│   │   └── quorum.py
│   │
│   ├── demo/
│   │   ├── __init__.py
│   │   ├── tamper_demo.py
│   │   └── two_fail_demo.py
│   │
│   └── verifier/
│       ├── __init__.py
│       ├── verification.py
│       └── verify_attestation.py
│
├── builders/
│   ├── __init__.py
│   ├── build.py
│   ├── builder_b.py
│   └── builder_c.py
│
├── data/
│   ├── artifacts/
│   ├── attestations/
│   ├── audit/
│   └── submissions/
│
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
│
├── keys/
│   ├── builder-a-public.key
│   ├── builder-b-public.key
│   └── builder-c-public.key
│
├── source/
│
├── requirements.txt
├── README_QUICKSTART.md
├── SETUP_GUIDE.md
└── START_QUORUM.bat
```

---

# Technology Stack

### Backend

- Python
- Flask
- Cryptography
- Ed25519
- SHA-256

### Frontend

- HTML5
- CSS3
- JavaScript

### Build System

- Python build tooling
- Python wheel artifacts

### Integrity and Trust

- SHA-256
- Ed25519 digital signatures
- 2-of-3 quorum consensus
- Hash-linked audit trail

---

# Requirements

Recommended environment:

```text
Python 3.11+
```

Install dependencies manually:

```powershell
python -m pip install -r requirements.txt
```

The repository also includes an automated launcher:

```text
START_QUORUM.bat
```

---

# Quick Start

## Option 1 — Start with the batch file

From the project directory:

```text
START_QUORUM.bat
```

The launcher:

1. Detects Python
2. Creates `.venv` if required
3. Installs dependencies
4. Starts the Flask backend

---

## Option 2 — Start manually

```powershell
cd C:\Quorum
python backend\app.py
```

The dashboard is available at:

```text
http://127.0.0.1:5000/
```

---

# API Endpoints

## Health

```http
GET /api/health
```

Checks whether the backend is online.

---

## Verification

```http
GET /api/verify
```

or:

```http
POST /api/verify
```

Runs the actual builder verification and quorum evaluation.

---

## Builder Status

```http
GET /api/builders
```

Returns normalized Builder A/B/C verification information.

---

## Reject Demonstration

```http
POST /api/demo/reject
```

Simulates:

```text
A → VERIFIED
B → FAILED
C → FAILED
```

and demonstrates quorum rejection.

---

## Audit Status

```http
GET /api/audit/status
```

Checks audit-chain integrity.

---

## Audit Entries

```http
GET /api/audit/entries?limit=10
```

Returns recent audit events.

---

## Source Upload

```http
POST /api/source/upload
```

Accepts a ZIP source package and stores the extracted source snapshot in the submission workspace.

---

## GitHub Source

```http
POST /api/source/github
```

Accepts a public GitHub repository URL and loads a repository snapshot into the submission workspace.

---

# Example: Normal Verification

```text
Builder A → VERIFIED
Builder B → VERIFIED
Builder C → VERIFIED

Artifact hashes → MATCH

Quorum → 3/3
Required → 2

STATUS → ACCEPT
```

---

# Example: Builder Failure

```text
Builder A → VERIFIED
Builder B → FAILED
Builder C → FAILED

Quorum → 1/3
Required → 2

STATUS → REJECT
```

---

# Example: Single Builder Outlier

```text
Builder A → HASH-X ✅
Builder B → HASH-X ✅
Builder C → HASH-Y ✅

Winning group → A + B
Quorum        → 2/3
Outlier       → C

STATUS → ACCEPT
```

---

# Example Audit Chain

```text
ENTRY 1
previous_hash = GENESIS
entry_hash    = HASH-1

ENTRY 2
previous_hash = HASH-1
entry_hash    = HASH-2

ENTRY 3
previous_hash = HASH-2
entry_hash    = HASH-3
```

If an earlier event is altered, the chain verification can identify where the sequence no longer matches.

---

# Security Considerations

## Private Keys

Builder private keys must never be committed to a public repository.

The repository `.gitignore` excludes:

```text
keys/*-private.key
```

Only trusted public keys should be distributed for verification.

---

## Builder Independence

The current local demonstration runs Builder A/B/C from the same local machine and therefore should not be described as fully independent production infrastructure.

For stronger isolation, a production deployment should use:

```text
Builder A → isolated container/environment
Builder B → isolated container/environment
Builder C → isolated container/environment
```

Docker or another sandboxing mechanism can provide this isolation.

---

## Source Execution Safety

Untrusted source code should not be executed directly on the host machine.

A production implementation should perform builds inside isolated, resource-limited environments with:

- No unnecessary host filesystem access
- Restricted network access
- Resource limits
- Ephemeral workspaces
- Controlled dependencies

---

# Why QUORUM?

Traditional verification often asks:

> “Can I trust this builder?”

QUORUM asks:

> “Do multiple independently verified builders agree on the same artifact?”

This changes the trust model from:

```text
Single point of trust
```

to:

```text
Distributed verification
+
Cryptographic evidence
+
Majority consensus
```

A single compromised builder may be able to produce a different result, but under the default 2-of-3 policy it cannot determine the final decision by itself.

---

# Hackathon Demo Flow

Recommended presentation flow:

```text
1. Open QUORUM dashboard
          ↓
2. Show source input
          ↓
3. Run verification
          ↓
4. Builder A/B/C verified
          ↓
5. SHA-256 + Ed25519 shown
          ↓
6. 3/3 consensus
          ↓
7. ACCEPT
          ↓
8. Simulate two builder failures
          ↓
9. 1/3 verified
          ↓
10. REJECT
          ↓
11. Restore verification
          ↓
12. 3/3
          ↓
13. ACCEPT
          ↓
14. Open Audit Trail
          ↓
15. Show chained verification events
```

---

# Future Improvements

Potential production extensions include:

- Container-isolated builders
- Remote independent build nodes
- Reproducible builds
- Repository commit/branch pinning
- Signed source manifests
- Dependency lockfile verification
- SBOM generation
- Transparency logs
- Hardware-backed signing keys
- CI/CD integration
- Multi-threshold quorum policies
- Role-based access control
- Persistent distributed audit storage

---

# Project Status

### Working

- ✅ Flask verification API
- ✅ Builder A/B/C verification
- ✅ SHA-256 artifact integrity
- ✅ Ed25519 signatures
- ✅ 2-of-3 quorum evaluation
- ✅ ACCEPT / REJECT decision
- ✅ Outlier detection
- ✅ Tamper-evident audit chain
- ✅ Audit event API
- ✅ Builder status API
- ✅ Live dashboard
- ✅ Controlled builder-failure demo
- ✅ Source ZIP ingestion interface
- ✅ Public GitHub source-ingestion interface

### Development / Hardening

- 🔧 Fully isolated independent build environments
- 🔧 Direct submitted-source → A/B/C build pipeline
- 🔧 Production sandboxing
- 🔧 Persistent trusted key management
- 🔧 Remote builder infrastructure

---

# Team / Project

**Project:** QUORUM — Multi-Builder Software Build Integrity Verification

**Purpose:** Software supply-chain integrity and trusted build verification

**Core technologies:** Python · Flask · SHA-256 · Ed25519 · Quorum Consensus

---

## License

Add the appropriate project license here based on your team's repository requirements.
