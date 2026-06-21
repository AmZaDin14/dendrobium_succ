# d_officinale_succ

Reproducible succinylation site prediction harness for *Daucus officinale*
(carrot) using [RLSuccSite](https://github.com/RLSuccSite) — a reinforcement
learning-based succinyllysine site predictor.

## What This Does

Given a protein FASTA, predicts which lysine (K) residues are likely
succinylated using RLSuccSite's trained ensemble (ProtT5 + TPEMPPS_CCP).

```
Protein FASTA → extract 33-mer fragments → ProtT5-XL embedding (GPU) → ensemble prediction → CSV
```

## Quick Start

```bash
# 1. Install harness dependencies
uv sync

# 2. One-time: cache ProtT5-XL on Modal (~2.8 GB)
uv run d-officinale-succ download-model

# 3. Run the full pipeline
uv run d-officinale-succ run \
    --input-fasta data/input/proteins.faa \
    --output-csv data/processed/predictions.csv \
    --skip-model-download
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `extract` | Extract 33-mer fragments around each K (CPU, local) |
| `download-model` | One-time: cache ProtT5-XL on Modal Volume |
| `embed` | Embed fragments with ProtT5-XL on Modal GPU |
| `predict` | Run RLSuccSite ensemble prediction (CPU, local) |
| `run` | Full pipeline: extract → embed → predict |

```bash
# Individual steps
uv run d-officinale-succ extract -i data/input/proteins.faa -o data/processed/fragments.fasta
uv run d-officinale-succ embed -f data/processed/fragments.fasta -o data/processed/features.pt
uv run d-officinale-succ predict --prott5-pt data/processed/features.pt -f data/processed/fragments.fasta -o data/processed/predictions.csv
```

## Prerequisites

- **uv** — [install](https://docs.astral.sh/uv/getting-started/installation/)
- **modal** — `uv tool install modal && modal setup`
- **RLSuccSite** at `../RLSuccSite` with `.venv` configured (`cd ../RLSuccSite && uv sync`)

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
src/d_officinale_succ/    # Python package (CLI, extract, embed, predict, pipeline)
modal/prott5_embed.py     # Modal GPU app for ProtT5-XL embedding
data/input/               # your protein FASTAs (gitignored)
data/processed/           # outputs: fragments, features, predictions (gitignored)
tests/                    # pytest tests for fragment extraction
scripts/demo.sh           # end-to-end demo
```
