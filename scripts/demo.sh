#!/usr/bin/env sh
set -eu
IMAGE=${1:-assets/sample_input.jpg}
IMAGE_URL=${2:?pass a public image URL}
OUT=${3:-runs/run1}
python -m src.pipeline run --image "$IMAGE" --image-url "$IMAGE_URL" --out "$OUT" --network local
python -m src.pipeline verify --receipt "$OUT/receipt.json"
