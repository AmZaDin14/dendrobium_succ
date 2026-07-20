#!/usr/bin/env bash
# scripts/fetch_genome.sh
#
# Download a Dendrobium genome + annotation from Figshare and extract
# its predicted proteome — three-step one-liner.
#
# Usage:
#   bash scripts/fetch_genome.sh D8
#   bash scripts/fetch_genome.sh D8 --figshare-article 26342338
#   bash scripts/fetch_genome.sh D8 --file-id 49420159
#
# What it does:
#   1. Looks up the file ID for <SPECIES>.zip via Figshare API (or use --file-id)
#   2. Downloads and extracts the ZIP
#   3. Runs scripts/gff_to_protein.py to translate GFF → protein FASTA
#   4. Replaces '.' with 'X' (ambiguous codons from EVM predictions)
#
# Output directory: data/genomes/d_<species_code>/
#   <species_code>.zip
#   <species_code>.genome.fasta
#   <species_code>.protein.best.gff
#   <species_code>.protein.faa         (raw from gff_to_protein.py)
#   <species_code>.protein_clean.faa   ('.' -> 'X', ready for pipeline)
#   Readme.txt
#
# Prerequisites:
#   uv sync  (installs pyfaidx)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# ── Config ──────────────────────────────────────────────────────────
FIGSHARE_ARTICLE="${FIGSHARE_ARTICLE:-26342338}"
FILE_ID=""
# ── Parse args ──────────────────────────────────────────────────────
usage() {
    echo "Usage: $0 <SPECIES_CODE> [options]"
    echo ""
    echo "Download a Dendrobium genome + extract proteome from Figshare."
    echo ""
    echo "Arguments:"
    echo "  SPECIES_CODE          Species code (e.g., D8 for D. crumenatum)"
    echo ""
    echo "Options:"
    echo "  --figshare-article ID  Figshare article ID (default: 26342338)"
    echo "  --file-id ID           Skip API query, use this file ID directly"
    echo "  --output-dir DIR       Output directory (default: data/genomes/d_<code>)"
    echo ""
    echo "Environment:"
    echo "  FIGSHARE_ARTICLE       Override default article ID"
    echo ""
    echo "Examples:"
    echo "  bash $0 D8"
    echo "  bash $0 D5 --file-id 49420158"
    echo "  bash $0 D13 --figshare-article 26342338"
    exit 0
}

# Detect help flag before any positional parsing
for _arg in "$@"; do
    case "$_arg" in -h|--help) usage ;; esac
done

SPECIES="${1:-}"
if [ -z "$SPECIES" ]; then
    echo "ERROR: missing SPECIES_CODE"
    usage
fi
shift

while [[ $# -gt 0 ]]; do
    case "$1" in
        --figshare-article) FIGSHARE_ARTICLE="$2"; shift 2 ;;
        --file-id) FILE_ID="$2"; shift 2 ;;
        --output-dir) OUTDIR="$2"; shift 2 ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

# ── Paths ───────────────────────────────────────────────────────────
SPECIES_LC="${SPECIES,,}"
OUTDIR="${OUTDIR:-$PROJECT_DIR/data/genomes/d_${SPECIES_LC}}"
ZIP_PATH="$OUTDIR/${SPECIES}.zip"
GENOME_FASTA="$OUTDIR/${SPECIES}.genome.fasta"
GFF_PATH="$OUTDIR/${SPECIES}.protein.best.gff"
PROTEIN_RAW="$OUTDIR/${SPECIES}.protein.faa"
PROTEIN_CLEAN="$OUTDIR/${SPECIES}.protein_clean.faa"

mkdir -p "$OUTDIR"

# ── Step 1: Resolve file ID ─────────────────────────────────────────
echo "═══ Step 1/3: Locate ${SPECIES}.zip ═══"

if [ -n "$FILE_ID" ]; then
    echo "  Using provided file ID: ${FILE_ID}"
elif [ -f "$ZIP_PATH" ]; then
    echo "  ${ZIP_PATH} already exists — skipping download step"
    FILE_ID="present"
else
    echo "  Querying Figshare article ${FIGSHARE_ARTICLE}..."
    API_RESPONSE=$(curl -sS -w "\n%{http_code}" \
        "https://api.figshare.com/v2/articles/${FIGSHARE_ARTICLE}/files")
    HTTP_CODE=$(echo "$API_RESPONSE" | tail -1)
    API_BODY=$(echo "$API_RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" != "200" ]; then
        echo "ERROR: Figshare API returned HTTP ${HTTP_CODE}"
        echo "       Try again or use --file-id to specify the download ID directly."
        exit 1
    fi

    # Parse JSON — find the file whose name matches <SPECIES>.zip
    FILE_ID=$(echo "$API_BODY" | python3 -c "
import json, sys
files = json.load(sys.stdin)
target = sys.argv[1] + '.zip'
for f in files:
    if f['name'] == target:
        print(f['id'])
        sys.exit(0)
sys.exit(1)
" "$SPECIES" 2>/dev/null || echo "")

    if [ -z "$FILE_ID" ]; then
        echo "ERROR: No file named ${SPECIES}.zip in article ${FIGSHARE_ARTICLE}"
        echo ""
        echo "Available species:"
        echo "$API_BODY" | python3 -c "
import json, sys
files = json.load(sys.stdin)
for f in files:
    if f['name'].endswith('.zip'):
        n = f['name'].replace('.zip', '')
        print(f'  {n}  (file {f[\"id\"]})')" 2>/dev/null || true
        exit 1
    fi
    echo "  ✓ Found: file ID ${FILE_ID}"
fi

# ── Step 2: Download + extract ──────────────────────────────────────
echo ""
echo "═══ Step 2/3: Download and extract ═══"

if [ -f "$GENOME_FASTA" ] && [ -f "$GFF_PATH" ]; then
    echo "  Genome FASTA and GFF already present — skipping download"
else
    if [ ! -f "$ZIP_PATH" ] && [ "$FILE_ID" != "present" ]; then
        DOWNLOAD_URL="https://ndownloader.figshare.com/files/${FILE_ID}"
        echo "  Downloading from Figshare..."
        curl -sL -o "$ZIP_PATH" "$DOWNLOAD_URL"
        echo "  ✓ Downloaded: $(du -h "$ZIP_PATH" | cut -f1)"
    fi

    echo "  Extracting ${SPECIES} files..."
    unzip -o "$ZIP_PATH" -d "$OUTDIR" \
        "${SPECIES}.genome.fasta" \
        "${SPECIES}.protein.best.gff" \
        "Readme.txt" 2>/dev/null || true
    echo "  ✓ Extracted to ${OUTDIR}"
fi

# ── Step 3: GFF → protein translation + clean ───────────────────────
echo ""
echo "═══ Step 3/3: Translate GFF → protein FASTA ═══"

if [ -f "$PROTEIN_CLEAN" ]; then
    echo "  Already done: ${PROTEIN_CLEAN}"
elif [ -f "$PROTEIN_RAW" ]; then
    echo "  Raw proteins exist — cleaning only..."
else
    uv run python "$SCRIPT_DIR/gff_to_protein.py" \
        --gff "$GFF_PATH" \
        --genome "$GENOME_FASTA" \
        --output "$PROTEIN_RAW"
fi

# ── Clean step (always runs if CLEAN doesn't exist) ─────────────────
if [ ! -f "$PROTEIN_CLEAN" ]; then
    echo ""
    echo "── Clean: replace '.' with 'X' ──"
    python3 -c "
import sys
with open('${PROTEIN_RAW}') as f:
    lines = f.readlines()
n_dots = sum(1 for l in lines if not l.startswith('>') and '.' in l)
with open('${PROTEIN_CLEAN}', 'w') as f:
    for line in lines:
        if line.startswith('>'):
            f.write(line)
        else:
            f.write(line.replace('.', 'X'))
n_prot = sum(1 for l in lines if l.startswith('>'))
if n_dots:
    print(f'  Replaced . with X in {n_dots} sequences')
print(f'  Wrote {n_prot} proteins to ${PROTEIN_CLEAN}')
"
fi

# ── Summary ─────────────────────────────────────────────────────────
N_PROTEINS=$(grep -c '^>' "$PROTEIN_CLEAN" 2>/dev/null || echo 0)
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Done: ${N_PROTEINS} proteins in ${PROTEIN_CLEAN}"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  Files in ${OUTDIR}:"
ls -lh "$ZIP_PATH" "$GENOME_FASTA" "$GFF_PATH" "$PROTEIN_RAW" "$PROTEIN_CLEAN" 2>/dev/null
echo ""
echo "  Next — run the pipeline:"
echo "    uv run dendrobium-succ run \\"
echo "      --input-fasta ${PROTEIN_CLEAN} \\"
echo "      --output-csv ${PROJECT_DIR}/data/processed/d_${SPECIES_LC}/predictions.csv \\"
echo "      --skip-model-download"
echo "═══════════════════════════════════════════════════════════════"
