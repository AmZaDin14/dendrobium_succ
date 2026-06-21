#!/usr/bin/env bash
#
# End-to-end demo: predict succinylation sites on a small example dataset.
#
# Uses the shipped mini dataset (1000 fragments from D. catenatum) to verify
# the full pipeline works without needing your own protein FASTA or GPU run.
#
# Prerequisites:
#   1. uv sync                       — install harness dependencies
#   2. A Python venv with torch, torchrl, tensordict, protlearn installed
#      (either the local .venv or a sibling RLSuccSite .venv — predict.py
#       will auto-detect; see src/dendrobium_succ/predict.py)
#
# Usage:
#   bash scripts/demo.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MINI_DIR="$PROJECT_DIR/data/wetlab/mini"
OUT_DIR="$PROJECT_DIR/data/processed/demo"

echo "═══════════════════════════════════════════════════════════════"
echo "  dendrobium_succ — Demo with shipped mini dataset"
echo "═══════════════════════════════════════════════════════════════"

# ── Verify mini dataset is present ─────────────────────────────────
for f in extracted_sites_mini.fasta features_K_site_mini.pt; do
    if [ ! -f "$MINI_DIR/$f" ]; then
        echo "ERROR: $MINI_DIR/$f not found"
        echo "       The mini dataset should ship with the repo. Did you"
        echo "       run 'git lfs pull' or is your checkout incomplete?"
        exit 1
    fi
done

# ── Setup output directory ─────────────────────────────────────────
mkdir -p "$OUT_DIR"

# ── Step 1: Fragments ─────────────────────────────────────────────
echo ""
echo "── Step 1: Fragments ──"
echo "  The mini dataset ships pre-extracted 33-mer fragments."
echo "  (In a real run, you'd use: dendrobium-succ extract -i proteins.faa -o fragments.fasta)"
cp "$MINI_DIR/extracted_sites_mini.fasta" "$OUT_DIR/fragments.fasta"
echo "  ✓ Fragments: $(grep -c '^>' "$OUT_DIR/fragments.fasta") sites"

# ── Step 2: ProtT5 embedding ──────────────────────────────────────
echo ""
echo "── Step 2: ProtT5 embedding ──"
echo "  Skipped Modal GPU step — using pre-computed mini features."
echo "  (In a real run, you'd use: dendrobium-succ embed -f fragments.fasta -o features.pt)"
cp "$MINI_DIR/features_K_site_mini.pt" "$OUT_DIR/features.pt"
echo "  ✓ Features: $OUT_DIR/features.pt"

# ── Step 3: RLSuccSite prediction ──────────────────────────────────
echo ""
echo "── Step 3: RLSuccSite ensemble prediction ──"
echo "  Requires: torch, torchrl, tensordict, protlearn"
echo "  (auto-detects: local .venv → sibling ../RLSuccSite/.venv)"
echo ""
uv run dendrobium-succ predict \
    --prott5-pt "$OUT_DIR/features.pt" \
    --fragments-fasta "$OUT_DIR/fragments.fasta" \
    --output-csv "$OUT_DIR/predictions.csv"

# ── Summary ────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Demo complete!"
echo "  Predictions: $OUT_DIR/predictions.csv"
echo "═══════════════════════════════════════════════════════════════"
head -5 "$OUT_DIR/predictions.csv"
