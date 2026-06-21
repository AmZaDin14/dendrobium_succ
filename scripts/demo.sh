#!/usr/bin/env bash
#
# End-to-end demo: predict succinylation sites on the RLSuccSite example dataset.
#
# Uses the shipped mini dataset (1000 fragments from D. catenatum) to verify
# the full pipeline works without needing your own protein FASTA.
#
# Prerequisites:
#   1. uv sync          — install harness dependencies
#   2. modal setup      — authenticate with Modal (one-time)
#   3. RLSuccSite at ../RLSuccSite with .venv already configured
#
# Usage:
#   bash scripts/demo.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
RLSUCCSITE_DIR="$(dirname "$PROJECT_DIR")/RLSuccSite"

echo "═══════════════════════════════════════════════════════════════"
echo "  d_officinale_succ — Demo with RLSuccSite mini dataset"
echo "═══════════════════════════════════════════════════════════════"

# ── Check prerequisites ────────────────────────────────────────────
if [ ! -f "$RLSUCCSITE_DIR/.venv/bin/python" ]; then
    echo "ERROR: RLSuccSite .venv not found at $RLSUCCSITE_DIR/.venv"
    echo "       Run: cd $RLSUCCSITE_DIR && uv sync"
    exit 1
fi

MINI_FASTA="$RLSUCCSITE_DIR/Dataset/d.catenatum/extracted_sites_mini.fasta"
MINI_PT="$RLSUCCSITE_DIR/Dataset/d.catenatum/features_K_site_mini.pt"

if [ ! -f "$MINI_FASTA" ] || [ ! -f "$MINI_PT" ]; then
    echo "ERROR: Mini dataset not found at $RLSUCCSITE_DIR/Dataset/d.catenatum/"
    exit 1
fi

# ── Setup output directory ─────────────────────────────────────────
OUT_DIR="$PROJECT_DIR/data/processed/demo"
mkdir -p "$OUT_DIR"

# ── Step 1: Fragments ─────────────────────────────────────────────
echo ""
echo "── Step 1: Fragments ──"
echo "  The mini dataset ships pre-extracted 33-mer fragments."
echo "  (In a real run, you'd use: d-officinale-succ extract -i proteins.faa -o fragments.fasta)"
cp "$MINI_FASTA" "$OUT_DIR/fragments.fasta"
echo "  ✓ Fragments: $(grep -c '^>' "$OUT_DIR/fragments.fasta") sites"

# ── Step 2: ProtT5 embedding ──────────────────────────────────────
echo ""
echo "── Step 2: ProtT5 embedding ──"
echo "  Skipped Modal GPU step — using pre-computed mini features."
echo "  (In a real run, you'd use: d-officinale-succ embed -f fragments.fasta -o features.pt)"
cp "$MINI_PT" "$OUT_DIR/features.pt"
echo "  ✓ Features: $OUT_DIR/features.pt"

# ── Step 3: RLSuccSite prediction ──────────────────────────────────
echo ""
echo "── Step 3: RLSuccSite ensemble prediction ──"
uv run d-officinale-succ predict \
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
