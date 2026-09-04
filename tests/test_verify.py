import json
from src.chain.client import LocalChain
from src.hashing.fingerprint import fingerprint


def test_tampered_payload_fails(tmp_path):
    chain = LocalChain(tmp_path / "chain.json")
    payload = {"matched_url": "https://example.com", "image_sha256": "a", "discovery_timestamp": "2026-09-03T00:00:00Z", "similarity_score": 0.8, "original_image_sha256": "b"}
    fp = fingerprint(payload)
    chain.store(fp, payload["matched_url"])
    payload["matched_url"] = "https://evil.example"
    assert fingerprint(payload) != chain.get(fp)["fingerprint"]
