param(
  [string]$Image = "assets/sample_input.jpg",
  [string]$ImageUrl,
  [string]$Out = "runs/run1"
)
python -m src.pipeline run --image $Image --image-url $ImageUrl --out $Out --network local
python -m src.pipeline verify --receipt "$Out/receipt.json"
