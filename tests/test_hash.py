import json
from src.hashing.fingerprint import canonical_payload, fingerprint


def test_fingerprint_is_deterministic_and_tamper_evident():
    payload = canonical_payload(" https://example.com/post/ ", b"image", "2026-09-03T00:00:00Z", .81234, b"original")
    assert fingerprint(payload) == fingerprint(json.loads(json.dumps(payload)))
    payload["matched_url"] = "https://example.com/changed"
    assert fingerprint(payload) != fingerprint(canonical_payload("https://example.com/post", b"image", "2026-09-03T00:00:00Z", .81234, b"original"))
