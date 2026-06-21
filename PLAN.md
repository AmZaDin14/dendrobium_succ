# Reproducible Plan: Succinylation Site Prediction for *Dendrobium officinale*

This document is a step-by-step, reproducible recipe for running RLSuccSite
inference on a new protein dataset using this harness. Every step is
automated and traceable via git conventional commits.

---

## Architecture Overview

```
                    ┌─────────────────┐
                    │  NCBI Assembly   │  (accession or organism name)
                    └────────┬────────┘
                             │
                   Step 0: fetch (HTTP, NCBI Datasets v2 API)
                   Download protein.faa from genome assembly
                             │
                    ┌────────▼────────┐
                    │  Protein FASTA   │  (.faa)
                    └────────┬────────┘
                             │
                   Step 1: extract (CPU, local)
                   Extract 33-mer fragments around each K
                             │
                    ┌────────▼────────┐
                    │ Fragments FASTA  │  (>id|pos_N, 33-char seq)
                    └────────┬────────┘
                             │
                   Step 2: embed (GPU, Modal)
                   ProtT5-XL center-residue embeddings
                             │
                    ┌────────▼────────┐
                    │  features.pt     │  ({'ids': [...], 'features': [N,1024]})
                    └────────┬────────┘
                             │
                   Step 3: predict (CPU, local via RLSuccSite)
                   Ensemble: ProtT5 model + TPEMPPS_CCP model
                             │
                    ┌────────▼────────┐
                    │ predictions.csv  │  (SequenceID, Sequence, Prob, Label)
                    └─────────────────┘
```

**Why Modal for step 2 only?** ProtT5-XL is a 3B-parameter transformer
(~2.8 GB). On CPU, embedding 1000 fragments takes ~30 min; on an L4 GPU,
~30 seconds. Steps 0, 1, and 3 are lightweight CPU/HTTP operations.

---

## Prerequisites

### 1. System tools

| Tool | Version | Install |
|------|---------|---------|
| Python | ≥ 3.11 | `uv python install 3.11` |
| uv | ≥ 0.4 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| git | ≥ 2.40 | system package manager |
| modal | ≥ 0.64 | `pip install modal` or `uv tool install modal` |

### 2. RLSuccSite models (bundled)

The model weights are bundled in `models/rlsuccsite/`. No sibling
repository is required. The predict step can use the local models
directly; see `src/dendrobium_succ/predict.py` for the resolution
logic. The predict step *does* need a Python interpreter with
`torch`, `torchrl`, `tensordict`, and `protlearn` installed — this
is typically provided by the sibling `../RLSuccSite/.venv` (if
present), falling back to the local `.venv`.

### 3. Modal account

```bash
modal setup    # authenticate (one-time)
modal token new --name dendrobium-succ
```

### 4. This harness

```bash
cd /home/amri/Code/python/dendrobium_succ
uv sync       # install harness deps (biopython, modal, typer, rich)
```

---

## Step-by-Step Execution

### Step 0 — One-time: Cache ProtT5-XL on Modal Volume

ProtT5-XL (~2.8 GB) is downloaded once and stored on a Modal Volume for
reuse across all future runs.

```bash
uv run dendrobium-succ download-model
# or directly:
modal run modal/prott5_embed.py::download_model
```

**Verify:** `modal volume ls prott5-model` should show HuggingFace cache files.

**Cost:** ~$0.01 (a few minutes of container time for download).

---

### Step 1 — Fetch Protein FASTA from NCBI (HTTP, local)

Download the complete proteome (.faa) for a genome assembly from the
NCBI Datasets v2 API. Two modes:

**By accession (recommended — reliable):**
```bash
# D. catenatum assembly (same as RLSuccSite's demo dataset)
uv run dendrobium-succ fetch \
    --accession GCF_001605985.2 \
    --output-fasta data/input/proteins.faa
```

**By organism name (searches NCBI Taxonomy):**
```bash
uv run dendrobium-succ fetch \
    --organism "Dendrobium catenatum" \
    --output-fasta data/input/proteins.faa
```

**How it works:**
1. (If `--organism`) Searches `GET /genome/taxon/{name}/dataset_report` for
   RefSeq assemblies, picks the first result
2. Downloads `GET /genome/accession/{acc}/download?include_annotation_type=PROT_FASTA`
   — returns a ZIP
3. Extracts `ncbi_dataset/data/{acc}/protein.faa` from the ZIP

**Output:** `data/input/proteins.faa` (e.g. 18 MB, 34,389 proteins for GCF_001605985.2)

**Verify:**
```bash
grep -c "^>" data/input/proteins.faa    # protein count
head -2 data/input/proteins.faa          # check format
```

**Notes:**
- Searching by organism may return multiple Dendrobium assemblies; pass
  `--accession GCF_001605985.2` for a specific assembly (recommended)
- Set `NCBI_API_KEY` env var for 10 req/s (default 5 req/s) — optional
- No API key required; no authentication needed

---

### Step 2 — Extract 33-mer Fragments (CPU, local)

Given a protein FASTA (fetched above or your own), extract a 33-mer
window centered on each lysine (K) residue. Fragments near termini are
padded with 'X'.

```bash
uv run dendrobium-succ extract \
    --input-fasta data/input/proteins.faa \
    --output-fasta data/processed/fragments.fasta
```

**Output:** `data/processed/fragments.fasta`

Format:
```
>XP_123456.1|pos_19
RSDNLAFAARRCFRNSKIQTFSSRSFISTAADP
>XP_123456.1|pos_49
ADPTAGERNDDDAQSSKPLADDLFRSPPRSGGY
```

**Verify:**
```bash
grep -c "^>" data/processed/fragments.fasta    # count of K sites
awk 'NR%2==0 {if (length($0)!=33) print "BAD LENGTH: "$0}' data/processed/fragments.fasta
```

---

### Step 3 — ProtT5-XL Embedding (GPU, Modal)

Send the fragments FASTA to Modal, where a GPU container (L4, 24 GB)
loads ProtT5-XL, tokenizes each 33-mer, runs the T5 encoder, and extracts
the center-residue (index 16) embedding — a 1024-D vector per fragment.

```bash
uv run dendrobium-succ embed \
    --fragments-fasta data/processed/fragments.fasta \
    --output-pt data/processed/features.pt
```

**What happens:**
1. The FASTA content is sent to Modal as a string argument
2. A GPU container starts (or reuses a warm one), loads ProtT5-XL from
   the cached Volume
3. Fragments are processed in batches of 64 (configurable)
4. The .pt file is written to a Modal Volume, then downloaded locally

**Output:** `data/processed/features.pt`

```python
# Verify locally (using the local venv):
uv run python -c "
import torch
d = torch.load('data/processed/features.pt', map_location='cpu')
print(d['features'].shape)  # should be [N, 1024]
print(len(d['ids']))        # should be N
print(d['ids'][:3])         # first 3 IDs
"
```

**Cost:** ~$0.80/hr × ~2 min = ~$0.03 for 10k fragments. Scales linearly.

**GPU selection:**
| GPU | VRAM | $/hr | Best for |
|-----|------|------|----------|
| L4 | 24 GB | $0.80 | Default. Handles up to ~500k fragments per run |
| A10 | 24 GB | $1.10 | Alternative if L4 unavailable |
| L40S | 48 GB | $1.95 | Large batches (>500k), faster throughput |

To change GPU, edit `modal/prott5_embed.py` line `gpu="L4"`.

---

### Step 4 — RLSuccSite Ensemble Prediction (CPU, local)

Run RLSuccSite's `Models/Predict.py` via its own virtual environment.
This computes hand-crafted features (TPEMPPS 528-D + CCP 462-D = 990-D)
on-the-fly from the fragments FASTA, loads both trained PPO models,
and produces a 50/50 ensemble prediction.

```bash
uv run dendrobium-succ predict \
    --prott5-pt data/processed/features.pt \
    --fragments-fasta data/processed/fragments.fasta \
    --output-csv data/processed/predictions.csv
```

**Output:** `data/processed/predictions.csv`

| Column | Description |
|--------|-------------|
| SequenceID | Fragment ID (e.g. `>XP_123456.1\|pos_19`) |
| Sequence | 33-mer amino acid fragment |
| PositiveProbability | Float 0–1, probability of succinylation |
| PredictedLabel | 0 (negative) or 1 (positive) |

**Verify:**
```bash
head -5 data/processed/predictions.csv
# Count predicted positive sites:
awk -F',' 'NR>1 && $4==1' data/processed/predictions.csv | wc -l
```

---

### Full Pipeline (All Steps at Once)

**With fetch (from NCBI accession):**
```bash
uv run dendrobium-succ run \
    --accession GCF_001605985.2 \
    --output-csv data/processed/predictions.csv \
    --skip-model-download    # if Step 0 already done
```

**With existing FASTA (skip fetch):**
```bash
uv run dendrobium-succ run \
    --input-fasta data/input/proteins.faa \
    --output-csv data/processed/predictions.csv \
    --skip-model-download
```

Intermediate files go to `data/processed/intermediate/` by default.

---

## Demo with Shipped Mini Dataset

To verify the harness works without your own data, use RLSuccSite's
example dataset (1000 fragments from *D. catenatum*):

```bash
bash scripts/demo.sh
```

This runs extract + predict using pre-computed ProtT5 features (skips
the Modal GPU step). Output: `data/processed/demo/predictions.csv`.

---

## Reproducibility Checklist

- [ ] **Python version pinned**: `requires-python = ">=3.11"` in `pyproject.toml`
- [ ] **Dependencies locked**: `uv.lock` generated by `uv sync`
- [ ] **RLSuccSite version**: note the git commit of RLSuccSite used
- [ ] **Model checkpoints**: fixed filenames with metrics in name (e.g. `ACC7142`)
- [ ] **ProtT5 model**: `Rostlab/prot_t5_xl_uniref50` (HuggingFace, immutable)
- [ ] **Scalers**: `scaler_tpempps.pkl` (528-D), `scaler_ccp.pkl` (462-D)
- [ ] **Random seeds**: not relevant for inference (no sampling, argmax only)
- [ ] **Git history**: conventional commits trace every change
- [ ] **Output format**: CSV with 4 columns, deterministic given same inputs

---

## Troubleshooting

### `modal run` fails with authentication error
```bash
modal token new --name dendrobium-succ
```

### ProtT5 model download fails
The HuggingFace download (~2.8 GB) may timeout. Re-run:
```bash
modal run modal/prott5_embed.py::download_model
```
The Volume is incremental — partial downloads resume.

### Predict.py fails with `ModuleNotFoundError: No module named 'torchrl'`
The local venv is missing RLSuccSite's heavy deps (torch, torchrl,
tensordict, protlearn). Two options:
```bash
# Option A: use the sibling RLSuccSite venv (if you have it)
# predict.py auto-detects ../RLSuccSite/.venv

# Option B: install deps into the local venv
uv pip install torch torchrl tensordict protlearn
```

### Predict.py fails with `FileNotFoundError: scaler_*.pkl`
The scalers ship in `models/rlsuccsite/Models/`. If missing, Predict.py
will try to fit them from training data (which may not be present).
Verify the bundled models are intact:
```bash
ls models/rlsuccsite/Models/*.pkl
ls models/rlsuccsite/Models/*.pth
```

### Fragment count is zero
Your input FASTA may be DNA, not protein. The extractor skips sequences
that look like DNA (only ATGCN, length > 100). Verify your input is a
protein FASTA (.faa).

### GPU out of memory
Reduce batch size:
```bash
uv run dendrobium-succ embed --batch-size 16 ...
```
Or upgrade to L40S (48 GB) in `modal/prott5_embed.py`.

---

## Cost Estimate

| Step | Resource | Time (10k fragments) | Cost |
|------|----------|---------------------|------|
| Fetch | HTTP (NCBI API) | ~10 sec | $0 |
| Extract | CPU (local) | ~5 sec | $0 |
| Embed | L4 GPU (Modal) | ~2 min | ~$0.03 |
| Predict | CPU (local) | ~3 min | $0 |
| **Total** | | | **~$0.03** |

For 100k fragments: ~$0.30. For 1M fragments: ~$3.00.

---

## File Map

```
dendrobium_succ/
├── pyproject.toml                    # uv project (deps: biopython, modal, typer, rich, sklearn, matplotlib, numpy)
├── PLAN.md                           # this file — reproduction recipe
├── README.md                         # landing page + quick-start
├── docs/                             # detailed documentation
│   ├── architecture.md               # system design + design decisions
│   └── cli-reference.md              # all CLI commands
├── src/dendrobium_succ/
│   ├── __init__.py
│   ├── cli.py                        # Typer CLI: 7 commands
│   ├── logging_config.py             # rich console + JSON file logger
│   ├── fetch.py                      # Step 1: NCBI Datasets v2 API
│   ├── extract.py                    # Step 2: 33-mer fragment extraction
│   ├── embed.py                      # Step 3: Modal client wrapper
│   ├── predict.py                    # Step 4: RLSuccSite Predict.py wrapper
│   ├── evaluate.py                   # Step 5: wet-lab evaluation (F1, MCC, AUC)
│   └── pipeline.py                   # Full pipeline orchestration
├── modal/
│   └── prott5_embed.py               # Modal GPU app (ProtT5-XL embedding)
├── models/
│   └── rlsuccsite/                   # bundled RLSuccSite models (Feature/, Models/)
├── data/
│   ├── input/                        # your protein FASTAs (gitignored)
│   ├── processed/                    # fragments, features, predictions (gitignored)
│   └── wetlab/                       # Feng et al. 2017 test sites + reference proteome
│       ├── test.csv                  # 314 wet-lab succinylation sites
│       ├── test_fixture.csv          # 3-row fixture for unit tests
│       ├── protein.faa               # 19 MB RefSeq proteome (ground truth)
│       └── mini/                     # 1000-fragment mini dataset for demo.sh
├── tests/
│   └── test_extract.py               # fragment extraction tests
└── scripts/
    └── demo.sh                       # end-to-end demo with shipped mini dataset
```
