# dendrobium_succ

Reproducible succinylation site prediction for *Dendrobium officinale*
(orchid) using [RLSuccSite](https://github.com/Zhangqingchao-Ch/RLSuccSite) — a
reinforcement learning-based succinyllysine site predictor. This harness wraps
RLSuccSite inference into a clean, end-to-end pipeline you can run on any
protein FASTA.

## What This Does

Given a protein FASTA, predicts which lysine (K) residues are likely
succinylated using RLSuccSite's trained ensemble (ProtT5 + TPEMPPS_CCP), then
optionally scores predictions against wet-lab ground truth.

```
NCBI Assembly → fetch FASTA → extract 33-mers → ProtT5-XL (GPU) → ensemble predict → evaluate
```

## Quick Start

```bash
# 1. Install
uv sync

# 2. Authenticate with Modal (one-time)
uv tool install modal && modal setup

# 3. One-time: cache ProtT5-XL on Modal Volume (~2.8 GB)
uv run dendrobium-succ download-model

# 4. Run the full pipeline
uv run dendrobium-succ run \
    --accession GCF_001605985.2 \
    --output-csv data/processed/predictions.csv \
    --skip-model-download
```

## How It Works

The pipeline has four stages, each a separate CLI command (or run them all with
`dendrobium-succ run`):

| Stage | What it does | Where it runs |
|-------|--------------|---------------|
| `fetch` | Download protein FASTA from NCBI Datasets v2 API | Local (HTTP) |
| `extract` | Extract 33-mer fragments centered on each K residue | Local (CPU) |
| `embed` | Compute ProtT5-XL center-residue embeddings (1024-D) | Modal (GPU) |
| `predict` | RLSuccSite ensemble (ProtT5 + TPEMPPS_CCP models) | Local (CPU) |
| `evaluate` | Score predictions against wet-lab ground truth (F1, MCC, AUC) | Local (CPU) |

ProtT5-XL is a 3B-parameter transformer (~2.8 GB) — too large to run on CPU at
scale, so only the embedding step uses GPU. Everything else runs locally. See
[docs/architecture.md](docs/architecture.md) for the full design rationale.

## Evaluation

After generating predictions, score them against the wet-lab test set (Feng et
al. 2017, 314 succinylation sites on *D. officinale*):

```bash
uv run dendrobium-succ evaluate \
    --predictions-csv data/processed/predictions.csv \
    --test-csv data/wetlab/test.csv \
    --protein-fasta data/wetlab/protein.faa \
    --output-dir data/wetlab/results
```

Outputs `matches.csv` (per-site predictions vs ground truth), `metrics.json`
(aggregate metrics: precision, recall, F1, MCC, AUC-ROC, AUC-PR), and
`pr_curve.png` (precision-recall curve). The evaluation also generates 1:1
same-protein synthetic negatives for fair precision/F1/MCC computation.

## CLI Commands

| Command | Description |
|---------|-------------|
| `fetch` | Download protein FASTA from NCBI Datasets API (by accession or organism) |
| `extract` | Extract 33-mer fragments around each K (CPU, local) |
| `download-model` | One-time: cache ProtT5-XL on Modal Volume |
| `embed` | Embed fragments with ProtT5-XL on Modal GPU |
| `predict` | Run RLSuccSite ensemble prediction (CPU, local) |
| `run` | Full pipeline: fetch → extract → embed → predict |
| `evaluate` | Score predictions against wet-lab ground truth (F1, MCC, AUC) |

See [docs/cli-reference.md](docs/cli-reference.md) for full flag details.

## Prerequisites

- **uv** — [install](https://docs.astral.sh/uv/getting-started/installation/)
- **modal** — `uv tool install modal && modal setup`
- **A Python venv with `torch`, `torchrl`, `tensordict`, `protlearn`** for the
  predict step. The harness auto-detects `../RLSuccSite/.venv` if present,
  else falls back to the local `.venv`. See
  [docs/architecture.md](docs/architecture.md#design-decisions) for the
  rationale.

The model weights are bundled in `models/rlsuccsite/`. No sibling RLSuccSite
repo is required.

## Demo

```bash
bash scripts/demo.sh    # uses shipped mini dataset (1000 fragments, 4MB)
```

Runs `extract` + `predict` on pre-computed ProtT5 features. Verifies the
pipeline end-to-end without your own data or a GPU run.

## Output Format

```csv
SequenceID,Sequence,PositiveProbability,PredictedLabel
>XP_020671682.1|pos_19,RSDNLAFAARRCFRNSKIQTFSSRSFISTAADP,0.8723,1
>XP_020671682.1|pos_49,ADPTAGERNDDDAQSSKPLADDLFRSPPRSGGY,0.1234,0
```

## Documentation

- [**PLAN.md**](PLAN.md) — step-by-step reproduction recipe
- [**docs/architecture.md**](docs/architecture.md) — system design + design decisions
- [**docs/cli-reference.md**](docs/cli-reference.md) — full CLI command reference

## Project Structure

```
dendrobium_succ/
├── pyproject.toml                # uv project
├── README.md                     # this file
├── PLAN.md                       # reproduction recipe
├── docs/                         # detailed documentation
├── src/dendrobium_succ/          # Python package
│   ├── cli.py                    # Typer CLI (7 commands)
│   ├── fetch.py                  # NCBI Datasets v2 API
│   ├── extract.py                # 33-mer fragment extraction
│   ├── embed.py                  # Modal client wrapper
│   ├── predict.py                # RLSuccSite Predict.py wrapper
│   ├── evaluate.py               # wet-lab evaluation
│   ├── pipeline.py               # full-pipeline orchestration
│   └── logging_config.py         # rich + JSON logging
├── modal/prott5_embed.py         # Modal GPU app
├── models/rlsuccsite/            # bundled RLSuccSite models
├── data/
│   ├── input/                    # your protein FASTAs (gitignored)
│   ├── processed/                # pipeline outputs (gitignored)
│   └── wetlab/                   # test.csv, protein.faa, mini dataset
├── tests/                        # pytest tests
└── scripts/demo.sh               # end-to-end demo
```
