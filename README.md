# Faceprint — Face Identification and Blockchain Verification

> A CLI-only pipeline that detects a face, finds it on the open web via live reverse-image search, cryptographically fingerprints the discovery, anchors it on-chain, and re-verifies it on demand.

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![CLI](https://img.shields.io/badge/interface-CLI-green.svg)]()
[![Chain](https://img.shields.io/badge/chain-local_%7C_sepolia-orange.svg)]()
[![License: MIT](https://img.shields.io/badge/solidity-MIT-lightgrey.svg)](src/chain/contracts/FaceVerificationRegistry.sol)

**No hosted website. No hardcoded results. Full audit trail in `runs/<id>/`.**


---

## Table of Contents

- [What It Does](#what-it-does)
- [Features](#features)
- [How It Works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Quickstart](#quickstart)
- [Usage](#usage)
- [Blockchain Networks](#blockchain-networks)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Security, Privacy & Cost](#security-privacy--cost)
- [Failure Modes & Troubleshooting](#failure-modes--troubleshooting)
- [Limitations](#limitations)
- [Roadmap](#roadmap)

---

## What It Does

Given a single-face photo, Faceprint runs end-to-end in one command:

```
face scan → live social/web match → face re-verification → SHA-256 fingerprint → blockchain write → VERIFIED
```

1. **Detects** the face and computes a stable 512-d embedding (Facenet512).
2. **Searches** the live web with Google Lens (SerpAPI) and proves each hit is a genuine face match — not just a keyword hit — by re-embedding the candidate image.
3. **Fingerprints** the discovery event as a canonical SHA-256 hash. No raw images or personal data go on-chain.
4. **Anchors** the fingerprint on-chain (local simulation by default, Sepolia testnet for public proof).
5. **Re-verifies** on demand: recompute locally, compare to on-chain → `VERIFIED` / `TAMPERED`.

Ideal for demonstrable provenance: `input.jpg` → verified URL + similarity score + tx hash + `VERIFIED` in a single unedited screen recording.

---

## Features

- **Pure CLI** — `run`, `verify`, `face-only`, `search-only`, no web server
- **Live reverse-image search** — SerpAPI Google Lens (primary) + Google Cloud Vision Web Detection (opt-in fallback)
- **Genuine-match proof** — every candidate is downloaded, re-embedded, and cosine-compared; failures are logged and skipped
- **Tamper-evident hashing** — deterministic canonical JSON → `bytes32` SHA-256
- **Dual-chain mode** — zero-setup local JSON chain for demos/CI + real Sepolia via `web3.py`
- **Auditable runs** — `search_results.json`, `matched_image.jpg`, `payload.json`, `fingerprint.txt`, `receipt.json` per run
- **Fail-loud UX** — `[Stage1]`–`[Stage5]` prefixed logs, actionable errors, non-zero exits

---

## How It Works

```
 Input Photo (jpg/png, 1 face)
        |
        v
 Stage 1 — Face Identification (DeepFace Facenet512 + RetinaFace)
        |  bbox + 512-d normalized embedding
        v
 Stage 2 — Reverse Image Search + Face Re-Verify
        |  candidates → download → re-embed → cosine similarity → best >= threshold
        v
 Stage 3 — Fingerprint (canonical SHA-256)
        |  {matched_url, image_sha256, discovery_timestamp, similarity_score, original_image_sha256}
        v
 Stage 4 — Blockchain Write (LocalChain | SepoliaChain)
        |  receipt.json {txHash, blockNumber, fingerprint, network}
        v
 Stage 5 — Re-Verification (recompute vs on-chain → PASS/FAIL)
```

### Stage summary

| Stage | Module | Input → Output |
|-------|--------|----------------|
| 1. Face | `src/face/embed.py` | `image` → `bbox, embedding[512], model, detector` |
| 2. Search | `src/search/provider.py`, `src/search/vision_web.py` | `public image URL` → `BestMatch {url, image_url, score}` |
| 3. Hash | `src/hashing/fingerprint.py` | `matched_url + image bytes + timestamp + score` → `0x… (bytes32)` |
| 4. Chain | `src/chain/client.py`, `src/chain/contracts/FaceVerificationRegistry.sol` | `fingerprint, url` → `receipt.json` |
| 5. Verify | `src/pipeline.py:verify()` | `receipt.json + payload.json` → `VERIFIED / TAMPERED` |

Example stdout for a successful run:

```text
[Stage1] Face detected bbox=(112,342,298,528) embedding_dim=512 model=Facenet512 detector=retinaface
[Stage2] SerpAPI Lens: 7 candidates, 2 passed face check. Best https://en.wikipedia.org/wiki/Elon_Musk score=0.9626
[Stage2] Verified image saved to runs/run1/matched_image.jpg
[Stage3] Canonical payload -> fingerprint 0xa93421a3d1375fc79a133b370a10dc62e340c11b6aefa37668d41ad89a918806
[Stage4] Network local tx 0x21f7730d74a5a… confirmed in block 1
[Stage5] Recomputed 0xa93421a3… == On-chain 0xa93421a3… => VERIFIED
```

---

## Prerequisites

- **Python 3.12+** (verified) + `pip` + `venv`
- **SerpAPI key** (free tier, ~100 searches/mo) — required for Stage 2
- A **publicly reachable URL** of the input image — Google Lens requires a URL, not a local file
- Optional for Sepolia: Alchemy/Infura `RPC_URL` + funded `PRIVATE_KEY` + Sepolia ETH
- Optional for fallback: Google Cloud Vision credentials + billing
- Windows / macOS / Linux. Node.js is **not** required.

> Use only images you own or that are public-domain / CC-licensed (e.g. Wikimedia Commons). A well-indexed frontal face gives reliable Lens hits; a random private selfie will typically return zero matches.

---

## Installation

```powershell
# 1. Clone and enter
git clone <your-repo-url> Faceprint
cd Faceprint

# 2. Virtualenv
python -m venv .venv
.\.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux

# 3. Dependencies
pip install -r requirements.txt

# 4. Environment
copy .env.example .env      # Windows
# cp .env.example .env      # macOS/Linux
```

Then fill `.env` (see below) and place your input:

```powershell
# assets/sample_input.jpg must be a clear single-face jpg/png
```

---

## Configuration

`.env` (never commit — already in `.gitignore`):

| Variable | Required for | Description |
|----------|--------------|-------------|
| `SERPAPI_KEY` | Stage 2 (Lens) | SerpAPI key from serpapi.com |
| `RPC_URL` | Sepolia only | Alchemy/Infura Sepolia HTTPS endpoint |
| `PRIVATE_KEY` | Sepolia only | Deployer/sender key (no `0x` prefix needed by `eth_account`) |
| `CONTRACT_ADDRESS` | Sepolia only | Printed by `scripts/deploy.py` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Vision fallback | Path to GCP service-account JSON |

Minimal local-only `.env`:

```ini
SERPAPI_KEY=your_key_here
RPC_URL=
PRIVATE_KEY=
CONTRACT_ADDRESS=
```

---

## Quickstart

```powershell
# End-to-end on local chain (zero funds, offline-verifiable)
python -m src.pipeline run --image assets/sample_input.jpg --image-url https://example.com/input.jpg --out runs/run1 --network local

# Re-verify later from receipt + payload
python -m src.pipeline verify --receipt runs/run1/receipt.json

# One-liner demo (run + verify)
.\scripts\demo.ps1 -Image assets/sample_input.jpg -ImageUrl https://example.com/input.jpg -Out runs/run1
# ./scripts/demo.sh assets/sample_input.jpg https://example.com/input.jpg runs/run1  # bash
```

> `--image-url` must be publicly reachable. Upload the same file to an image host or any public HTTPS URL.

---

## Usage

### `run` — full pipeline

```powershell
python -m src.pipeline run --image <local-path> --image-url <public-url> --out <dir> --network <local|sepolia> --threshold <float> --vision-fallback
```

| Flag | Default | Notes |
|------|---------|-------|
| `--image` | (required) | Local jpg/png with one clear frontal face |
| `--image-url` | (required) | Public URL of the same image for Lens |
| `--out` | `runs/run1` | Run directory for all artifacts |
| `--threshold` | `0.6` | Cosine **similarity** cutoff (higher = stricter). ≈ `1 − distance`; `0.6` ≈ Facenet distance `0.40` |
| `--network` | `local` | `local` = persistent JSON simulation; `sepolia` = public testnet |
| `--vision-fallback` | off | If SerpAPI fails, retry with Google Vision Web Detection |

What `run` does: detect → Lens search → download each candidate (10 s timeout, browser UA) → re-embed → keep `score >= threshold` → pick best → write `matched_image.jpg` → canonicalize + hash → store on-chain → save receipt → immediate `verify`.

Per-run artifacts (`runs/<id>/`):

| File | Contents |
|------|----------|
| `search_results.json` | Raw Lens candidates `[{url, image_url, title, source}]` |
| `matched_image.jpg` | Winning candidate bytes |
| `payload.json` | Canonical fields (see below) |
| `fingerprint.txt` | `0x…` SHA-256 fingerprint |
| `receipt.json` | `{fingerprint, url, txHash, blockNumber, network, …}` |
| `chain.json` | Local-chain store (local mode only) |

`payload.json` shape:

```json
{
  "discovery_timestamp": "2026-09-04T07:44:47Z",
  "image_sha256": "3938a9f3…",
  "matched_url": "https://en.wikipedia.org/wiki/Elon_Musk",
  "original_image_sha256": "81241856…",
  "similarity_score": 0.9626
}
```

### `verify` — re-verification

```powershell
python -m src.pipeline verify --receipt runs/run1/receipt.json
python -m src.pipeline verify --receipt runs/run1/receipt.json --payload runs/run1/payload.json
```

Recomputes `SHA256(canonical(payload.json))` and compares to the on-chain record:

```text
[Stage5] Recomputed 0xa934… == On-chain 0xa934… => VERIFIED
[Stage5] Recomputed 0xdead… != On-chain 0xa934… => TAMPERED
```

Tamper demo: edit one character in `payload.json` (or swap `matched_image.jpg`) and re-run `verify` → `TAMPERED`, exit `1`.

### `face-only` — debug Stage 1

```powershell
python -m src.pipeline face-only --image assets/sample_input.jpg
```

### `search-only` — debug Stage 2

```powershell
python -m src.pipeline search-only --image assets/sample_input.jpg --image-url https://example.com/input.jpg
```

---

## Blockchain Networks

|  | **Local (default)** | **Sepolia (public proof)** |
|---|---|---|
| Backend | `LocalChain` — persistent `chain.json` in run dir | `FaceVerificationRegistry.sol` via `web3.py` |
| Setup | None | `python scripts/deploy.py`, set `.env`, fund with Sepolia ETH |
| Cost | Zero | Testnet gas (faucet) |
| Explorer | Logs only | `sepolia.etherscan.io/tx/<txHash>` |
| Use when | Offline demo, CI, recording rehearsal | Final “real blockchain” evidence |

Deploy once for Sepolia:

```powershell
python scripts/deploy.py
# → {"contractAddress": "0x…", "txHash": "0x…", "chainId": 11155111}
```

Copy `contractAddress` into `.env` as `CONTRACT_ADDRESS`, then:

```powershell
python -m src.pipeline run --image assets/sample_input.jpg --image-url https://example.com/input.jpg --out runs/sepolia1 --network sepolia
```

Solidity registry (`src/chain/contracts/FaceVerificationRegistry.sol`):

```solidity
mapping(bytes32 => Record) public records;
event Stored(bytes32 indexed fingerprint, address indexed submitter, uint64 timestamp, string matchedUrl);
function storeRecord(bytes32 fp, string calldata url) external;
function getRecord(bytes32 fp) external view returns (Record memory);
```

Only the `bytes32` fingerprint + URL string are stored. Images and embeddings never leave your machine except for the Lens query itself.

---

## Project Structure

```text
Faceprint/
├── src/
│   ├── pipeline.py                 # CLI orchestrator: run / verify / face-only / search-only
│   ├── face/embed.py               # FaceEngine (DeepFace Facenet512 + RetinaFace), cosine_similarity
│   ├── search/provider.py          # Candidate dataclass, SerpApiLens, save_candidates
│   ├── search/vision_web.py        # VisionWebDetection fallback
│   ├── hashing/fingerprint.py      # canonical_payload, fingerprint, write_payload
│   └── chain/
│       ├── client.py               # LocalChain (JSON) + SepoliaChain (web3.py)
│       └── contracts/FaceVerificationRegistry.sol
├── scripts/
│   ├── deploy.py                   # Compile (solc 0.8.20) + deploy registry
│   ├── demo.ps1 / demo.sh          # run + verify one-liners
├── tests/
│   ├── test_hash.py                # determinism + tamper-evidence
│   ├── test_chain.py               # local persistence
│   └── test_verify.py              # tampered payload fails
├── assets/sample_input.jpg         # Curated indexed single-face image (replace legally)
├── runs/                           # gitignored per-run artifacts
├── requirements.txt / pyproject.toml
└── .env.example
```

Tech stack: Python 3.12, `deepface`, `opencv-python`, `numpy`, `Pillow`, `requests`, `web3`, `eth-account`, `py-solc-x`, `google-cloud-vision`, `pytest`.

Key design choices: DeepFace over `face_recognition` (avoids `dlib` builds on Windows); SerpAPI Lens over scraping (real Lens semantics, cheap); `py-solc-x` over Foundry/Hardhat (pure-pip); hash-of-hashes over raw bytes (cheap, private).

---

## Testing

```powershell
python -m pytest -q
```

- `test_hash` — same payload → same fingerprint; JSON round-trip stable; mutated URL → different hash.
- `test_chain` — `LocalChain.store/get` persists across instances via `chain.json`.
- `test_verify` — tampered `matched_url` no longer matches stored fingerprint.

All tests run offline. Live Lens / Sepolia paths are manual (require keys + funds).

---

## Security, Privacy & Cost

- **On-chain:** only `fingerprint (bytes32)` + `matchedUrl (string)`. No images, embeddings, or PII.
- **Secrets:** `.env` is gitignored. Never log or commit `SERPAPI_KEY`, `PRIVATE_KEY`, `RPC_URL`. The Lens query inherently uploads the image to SerpAPI/Google — use only images you may share.
- **Cost:** SerpAPI free ~100/mo; Vision ~$1/1k; Sepolia gas via faucet; local mode free.
- **Abuse guards:** 10 s download timeout, browser UA, per-candidate skip-and-log, no silent fallbacks.

---



