import hashlib
import json
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_payload(matched_url, image_bytes, timestamp, similarity_score, original_bytes):
    return {
        "matched_url": matched_url.strip().rstrip("/") or "/",
        "image_sha256": sha256(image_bytes),
        "discovery_timestamp": timestamp,
        "similarity_score": round(float(similarity_score), 4),
        "original_image_sha256": sha256(original_bytes),
    }


def fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "0x" + hashlib.sha256(canonical).hexdigest()


def write_payload(path: Path, payload: dict) -> str:
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    fp = fingerprint(payload)
    path.with_name("fingerprint.txt").write_text(fp + "\n", encoding="utf-8")
    return fp
