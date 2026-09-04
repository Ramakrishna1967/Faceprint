import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from .chain.client import LocalChain, SepoliaChain
from .face.embed import FaceEngine, FaceError, cosine_similarity
from .hashing.fingerprint import canonical_payload, fingerprint, write_payload
from .search.provider import SerpApiLens, save_candidates
from .search.vision_web import VisionWebDetection


def run(args):
    image = Path(args.image)
    out = Path(args.out)
    original = image.read_bytes()
    try:
        engine = FaceEngine()
        face = engine.detect_and_embed(image)
    except FaceError as exc:
        raise SystemExit(f"[Stage1] ERROR: {exc}")
    print(f"[Stage1] Face detected bbox={face.bbox} embedding_dim={len(face.embedding)} model={face.model} detector={face.detector}")

    if not args.image_url:
        raise SystemExit("[Stage2] ERROR: --image-url is required because Google Lens needs a publicly reachable image URL")
    try:
        candidates = SerpApiLens().search(args.image_url)
    except Exception as exc:
        if not args.vision_fallback:
            raise SystemExit(f"[Stage2] ERROR: SerpAPI failed: {exc}")
        print(f"[Stage2] SerpAPI failed; using Vision fallback ({exc})")
        candidates = VisionWebDetection().search(str(image))
    out.mkdir(parents=True, exist_ok=True)
    save_candidates(out / "search_results.json", candidates)
    best = None
    for index, candidate in enumerate(candidates, 1):
        try:
            response = requests.get(candidate.image_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            score = cosine_similarity(face.embedding, engine.embed_bytes(response.content))
            print(f"[Stage2] {index}/{len(candidates)} {candidate.url} score={score:.4f} {'PASS' if score >= args.threshold else 'REJECT'}")
            if score >= args.threshold and (best is None or score > best[0]):
                best = score, candidate, response.content
        except Exception as exc:
            print(f"[Stage2] {index}/{len(candidates)} {candidate.url} SKIP ({exc})")
    if best is None:
        raise SystemExit("[Stage2] ERROR: MATCHES_REJECTED: no candidate passed the face threshold")
    score, candidate, matched_bytes = best
    (out / "matched_image.jpg").write_bytes(matched_bytes)
    payload = canonical_payload(candidate.url, matched_bytes, datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"), score, original)
    fp = write_payload(out / "payload.json", payload)
    print(f"[Stage3] Canonical payload -> fingerprint {fp}")
    chain = LocalChain(out / "chain.json") if args.network == "local" else SepoliaChain()
    receipt = chain.store(fp, candidate.url)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(f"[Stage4] Network {receipt['network']} tx {receipt['txHash']} confirmed in block {receipt['blockNumber']}")
    verify(args, receipt_path=out / "receipt.json", quiet=False)


def verify(args, receipt_path=None, quiet=True):
    receipt_path = Path(receipt_path or args.receipt)
    receipt = json.loads(receipt_path.read_text())
    payload_path = Path(args.payload) if getattr(args, "payload", None) else receipt_path.with_name("payload.json")
    fp = fingerprint(json.loads(payload_path.read_text()))
    chain = LocalChain(receipt_path.with_name("chain.json")) if receipt.get("network") == "local" else SepoliaChain(receipt.get("contractAddress"))
    record = chain.get(receipt["fingerprint"])
    ok = record is not None and fp == record["fingerprint"]
    print(f"[Stage5] Recomputed {fp} {'==' if ok else '!='} On-chain {receipt['fingerprint']} => {'VERIFIED' if ok else 'TAMPERED'}")
    if not ok:
        raise SystemExit(1)


def face_only(args):
    try:
        face = FaceEngine().detect_and_embed(Path(args.image))
    except FaceError as exc:
        raise SystemExit(f"[Stage1] ERROR: {exc}")
    print(f"[Stage1] Face detected bbox={face.bbox} embedding_dim={len(face.embedding)} model={face.model} detector={face.detector}")


def search_only(args):
    candidates = SerpApiLens().search(args.image_url)
    for index, candidate in enumerate(candidates, 1):
        print(f"[Stage2] {index}/{len(candidates)} {candidate.url} ({candidate.image_url})")


def main():
    parser = argparse.ArgumentParser(prog="pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--image", required=True)
    run_parser.add_argument("--image-url")
    run_parser.add_argument("--out", default="runs/run1")
    run_parser.add_argument("--threshold", type=float, default=0.6)
    run_parser.add_argument("--network", choices=["local", "sepolia"], default="local")
    run_parser.add_argument("--vision-fallback", action="store_true")
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--receipt", required=True)
    verify_parser.add_argument("--payload")
    face_parser = sub.add_parser("face-only")
    face_parser.add_argument("--image", required=True)
    search_parser = sub.add_parser("search-only")
    search_parser.add_argument("--image", required=True)
    search_parser.add_argument("--image-url", required=True)
    args = parser.parse_args()
    {"run": run, "verify": verify, "face-only": face_only, "search-only": search_only}[args.command](args)


if __name__ == "__main__":
    main()





