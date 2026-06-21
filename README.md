# dendrobium_succ

Reproducible succinylation site prediction harness for *Dendrobium officinale*
(orchid) using [RLSuccSite](https://github.com/RLSuccSite) — a reinforcement
learning-based succinyllysine site predictor.

## What This Does

Given a protein FASTA (fetched from NCBI or your own), predicts which lysine
(K) residues are likely succinylated using RLSuccSite's trained ensemble
(ProtT5 + TPEMPPS_CCP).

```
NCBI Assembly → fetch protein FASTA → extract 33-mer fragments → ProtT5-XL embedding (GPU) → ensemble prediction → CSV
```

## Quick Start

```bash
# 1. Install harness dependencies
uv sync

# 2. One-time: cache ProtT5-XL on Modal (~2.8 GB)
uv run dendrobium-succ download-model

# 3. Run the full pipeline (fetch from NCBI → extract → embed → predict)
uv run dendrobium-succ run \
    --accession GCF_001605985.2 \
    --output-csv data/processed/predictions.csv \
    --skip-model-download
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `fetch` | Download protein FASTA from NCBI Datasets API (by accession or organism) |
| `extract` | Extract 33-mer fragments around each K (CPU, local) |
| `download-model` | One-time: cache ProtT5-XL on Modal Volume |
| `embed` | Embed fragments with ProtT5-XL on Modal GPU |
| `predict` | Run RLSuccSite ensemble prediction (CPU, local) |
| `run` | Full pipeline: fetch → extract → embed → predict |

```bash
# Individual steps
dendrobium-succ fetch --accession GCF_001605985.2 -o data/input/proteins.faa
dendrobium-succ extract -i data/input/proteins.faa -o data/processed/fragments.fasta
dendrobium-succ embed -f data/processed/fragments.fasta -o data/processed/features.pt
dendrobium-succ predict --prott5-pt data/processed/features.pt -f data/processed/fragments.fasta -o data/processed/predictions.csv
```

## Prerequisites

- **uv** — [install](https://docs.astral.sh/uv/getting-started/installation/)
- **modal** — `uv tool install modal && modal setup`

The model weights are bundled in `models/rlsuccsite/`. No sibling repo required.

## Demo

```bash
bash scripts/demo.sh    # uses RLSuccSite's mini dataset (1000 fragments)
```

## Output Format

```csv
SequenceID,Sequence,PositiveProbability,PredictedLabel
>XP_020671682.1|pos_19,RSDNLAFAARRCFRNSKIQTFSSRSFISTAADP,0.8723,1
>XP_020671682.1|pos_49,ADPTAGERNDDDAQSSKPLADDLFRSPPRSGGY,0.1234,0
```

## Documentation

- [**PLAN.md**](PLAN.md) — detailed step-by-step reproducible plan with cost estimates and troubleshooting

## Project Structure

```
src/dendrobium_succ/    # Python package (CLI, fetch, extract, embed, predict, pipeline)
modal/prott5_embed.py     # Modal GPU app for ProtT5-XL embedding
data/input/               # your protein FASTAs (gitignored)
data/processed/           # outputs: fragments, features, predictions (gitignored)
tests/                    # pytest tests for fragment extraction
scripts/demo.sh           # end-to-end demo
```
