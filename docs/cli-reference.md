# CLI Reference

> 🌐 **Language:** **English** | [Bahasa Indonesia](id/referensi-cli.md)

Complete reference for all `dendrobium-succ` commands. For the design rationale
behind these commands, see [architecture.md](architecture.md). For a
reproduction recipe, see [PLAN.md](../PLAN.md).

> **Tip**: Run any command with `--help` for the latest flag details:
> ```bash
> uv run dendrobium-succ <command> --help
> ```

---

## Global Options

These options apply to **all** commands and are configured at the CLI level
(not on individual commands).

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--log-level` | `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL` | `INFO` | Minimum log level |
| `--log-file` | PATH | `data/processed/run.log` | JSON log file path |

```bash
# Example: debug-level logging to a custom file
uv run dendrobium-succ --log-level DEBUG --log-file /tmp/run.log fetch --accession GCF_001605985.2
```

---

## `fetch` — Download protein FASTA

Downloads protein FASTA from the NCBI Datasets v2 API. Either `--accession` or
`--organism` is required.

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--output-fasta` / `-o` | PATH | `data/input/proteins.faa` | Output protein FASTA path |
| `--accession` / `-a` | TEXT | (none) | NCBI assembly accession (e.g. `GCF_001605985.2`) |
| `--organism` | TEXT | (none) | Organism name to search NCBI (e.g. `Dendrobium catenatum`) |

**Examples:**

```bash
# By accession (recommended — reliable, single assembly)
uv run dendrobium-succ fetch --accession GCF_001605985.2 -o data/input/proteins.faa

# By organism (picks first RefSeq result — may not be the assembly you want)
uv run dendrobium-succ fetch --organism "Dendrobium catenatum" -o data/input/proteins.faa

# With API key for higher rate limit (10 req/s vs 5 req/s)
NCBI_API_KEY=xxx uv run dendrobium-succ fetch --accession GCF_001605985.2
```

**Output:** `data/input/proteins.faa` (~19 MB, 34,389 proteins for
GCF_001605985.2).

---

## `extract` — Extract 33-mer fragments

Extracts a fixed-length window centered on each lysine (K) residue from a
protein FASTA. Fragments near termini are padded with `X`.

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--input-fasta` / `-i` | PATH | *(required)* | Input protein FASTA (.faa / .fasta) |
| `--output-fasta` / `-o` | PATH | *(required)* | Output fragments FASTA path |
| `--window-size` / `-w` | INT | `33` | Fragment window size (must be odd) |

**Examples:**

```bash
# Default window (33, matches RLSuccSite's expected input)
uv run dendrobium-succ extract -i data/input/proteins.faa -o data/processed/fragments.fasta

# Custom window (e.g. 21 for shorter context)
uv run dendrobium-succ extract -i proteins.faa -o fragments.fasta --window-size 21
```

**Output format:**
```
>XP_123456.1|pos_19
RSDNLAFAARRCFRNSKIQTFSSRSFISTAADP
>XP_123456.1|pos_49
ADPTAGERNDDDAQSSKPLADDLFRSPPRSGGY
```

The K is always at index 16 (0-based) of the 33-char fragment.

---

## `download-model` — One-time: cache ProtT5-XL

Downloads `Rostlab/prot_t5_xl_uniref50` (~2.8 GB) to a Modal Volume for reuse
across all future runs. **Run this once** before your first `embed`.

**No flags.**

**Examples:**

```bash
# First-time setup
uv run dendrobium-succ download-model

# Verify: should show HuggingFace cache files
modal volume ls prott5-model
```

**Cost:** ~$0.01 (a few minutes of container time).

---

## `embed` — Compute ProtT5-XL embeddings

Sends the fragments FASTA to a Modal GPU container, which loads ProtT5-XL,
tokenizes each 33-mer, runs the T5 encoder, and extracts the center-residue
(index 16) embedding — a 1024-D vector per fragment.

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--fragments-fasta` / `-f` | PATH | *(required)* | Fragments FASTA from `extract` step |
| `--output-pt` / `-o` | PATH | *(required)* | Output `.pt` file path |
| `--batch-size` / `-b` | INT | `512` | GPU batch size (limited by VRAM) |

**Examples:**

```bash
# Standard run
uv run dendrobium-succ embed -f data/processed/fragments.fasta -o data/processed/features.pt

# Smaller batch (for GPUs with less VRAM)
uv run dendrobium-succ embed -f fragments.fasta -o features.pt --batch-size 64

# Larger batch (GPU is already L40S 48 GB; the --batch-size flag tunes it)
uv run dendrobium-succ embed -f fragments.fasta -o features.pt --batch-size 2048
```

**Output:** `data/processed/features.pt` — a PyTorch save file with
`{'ids': list[str], 'features': Tensor[N, 1024]}`.

**Cost:** ~$0.80/hr × ~2 min = ~$0.03 for 10k fragments. Scales linearly.

---

## `predict` — Run RLSuccSite ensemble prediction

Runs the RLSuccSite ensemble (ProtT5 model + TPEMPPS_CCP model) on the
features. Computes hand-crafted features on-the-fly from the fragments FASTA.

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--prott5-pt` | PATH | *(required)* | ProtT5 features `.pt` file (from `embed`) |
| `--fragments-fasta` / `-f` | PATH | *(required)* | Fragments FASTA (from `extract`) |
| `--output-csv` / `-o` | PATH | *(required)* | Output predictions CSV |
| `--rlsuccsite-dir` | PATH | auto-detect | Override RLSuccSite directory (default: `models/rlsuccsite/`) |
| `--num-workers` / `-n` | INT | `6` | Parallel workers for hand-crafted feature extraction |
| `--batch-size` / `-b` | INT | `2048` | Streaming batch size |

**Examples:**

```bash
# Standard run (uses bundled models in models/rlsuccsite/)
uv run dendrobium-succ predict \
    --prott5-pt data/processed/features.pt \
    -f data/processed/fragments.fasta \
    -o data/processed/predictions.csv

# Use a different RLSuccSite directory
uv run dendrobium-succ predict \
    --prott5-pt features.pt -f fragments.fasta -o predictions.csv \
    --rlsuccsite-dir /path/to/RLSuccSite

# Tune parallel workers for faster feature extraction
uv run dendrobium-succ predict \
    --prott5-pt features.pt -f fragments.fasta -o predictions.csv \
    --num-workers 12
```

**Output:** `data/processed/predictions.csv` with 4 columns:
`SequenceID`, `Sequence`, `PositiveProbability`, `PredictedLabel`.

**Requirements:** A Python interpreter with `torch`, `torchrl`, `tensordict`,
`protlearn` installed. The harness auto-detects:
1. `../RLSuccSite/.venv/bin/python` (if sibling repo exists)
2. Local `.venv/bin/python` (fallback)

If neither works, install the deps: `uv pip install torch torchrl tensordict protlearn`.

---

## `run` — Full pipeline

Chains `fetch` → `extract` → `embed` → `predict` into a single command.
Provide either `--input-fasta` (skip fetch) or `--accession`/`--organism`
(fetch first).

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--output-csv` / `-o` | PATH | *(required)* | Output predictions CSV |
| `--input-fasta` / `-i` | PATH | (none) | Input protein FASTA (skip fetch) |
| `--accession` / `-a` | TEXT | (none) | NCBI assembly accession to fetch |
| `--organism` | TEXT | (none) | Organism name to search NCBI |
| `--work-dir` | PATH | `<output_csv_dir>/intermediate` | Directory for intermediate files |
| `--skip-model-download` | flag | `False` | Skip the one-time ProtT5 download |
| `--batch-size` / `-b` | INT | `512` | GPU batch size (passed to `embed`) |
| `--num-workers` / `-n` | INT | `6` | CPU workers (passed to `predict`) |

**Examples:**

```bash
# With fetch (from NCBI accession)
uv run dendrobium-succ run \
    --accession GCF_001605985.2 \
    --output-csv data/processed/predictions.csv \
    --skip-model-download

# With existing FASTA (skip fetch)
uv run dendrobium-succ run \
    --input-fasta data/input/proteins.faa \
    --output-csv data/processed/predictions.csv \
    --skip-model-download

# With organism search
uv run dendrobium-succ run \
    --organism "Dendrobium catenatum" \
    --output-csv data/processed/predictions.csv
```

**Output:**
- `<output_csv>` — final predictions
- `<work_dir>/proteins.faa` — fetched proteome
- `<work_dir>/fragments.fasta` — extracted fragments
- `<work_dir>/features.pt` — ProtT5 embeddings

---

## `evaluate` — Score predictions against wet-lab ground truth

Computes recall on the Feng et al. 2017 wet-lab test set plus precision, F1,
MCC, AUC-ROC, AUC-PR using 1:1 same-protein synthetic negatives (matches
RLSuccSite-NegCtrl policy).

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--predictions-csv` / `-p` | PATH | *(required)* | Predictions CSV from `predict` step |
| `--test-csv` | PATH | `data/wetlab/test.csv` | Wet-lab test sites CSV |
| `--output-dir` / `-o` | PATH | `data/wetlab/results` | Output directory |
| `--protein-fasta` | PATH | `data/wetlab/protein.faa` | RefSeq proteome (for generating negatives) |
| `--seed` | INT | `42` | Random seed for negative sampling |

**Examples:**

```bash
# Standard evaluation
uv run dendrobium-succ evaluate \
    --predictions-csv data/processed/predictions.csv \
    --test-csv data/wetlab/test.csv \
    --protein-fasta data/wetlab/protein.faa \
    --output-dir data/wetlab/results

# Custom seed (for sensitivity analysis)
uv run dendrobium-succ evaluate \
    -p predictions.csv --seed 123 -o results_seed123
```

**Outputs (in `output_dir/`):**

| File | Contents |
|------|----------|
| `matches.csv` | Per-site predictions vs ground truth (ProteinAccession, RefSeqAccession, Position, TrueLabel, Source, MatchedSequence, PositiveProbability, PredictedLabel, Status) |
| `metrics.json` | Aggregate metrics (n_total, n_scored, n_positives, n_negatives, confusion_matrix, accuracy, precision, recall, f1, mcc, auc_roc, auc_pr) |
| `pr_curve.png` | Precision-recall curve plot |

**Console output:**
```
============================================================
  Evaluation Results
============================================================
  Total sites evaluated: 602
  Positives: 301  |  Negatives: 301
  Confusion: TP=259  FP=182  TN=119  FN=42  NS=0

  Accuracy  : 0.6279
  Precision : 0.5873
  Recall    : 0.8605
  F1 Score  : 0.6981
  MCC       : 0.2890
  AUC-ROC   : 0.6486
  AUC-PR    : 0.6127
  Results written to data/wetlab/results/
============================================================
```

---

## Common Workflows

### A. First-time setup + run

```bash
# 1. Install
uv sync

# 2. Authenticate Modal
uv tool install modal && modal setup

# 3. Cache ProtT5-XL (one-time, ~3 min, ~$0.01)
uv run dendrobium-succ download-model

# 4. Run full pipeline
uv run dendrobium-succ run \
    --accession GCF_001605985.2 \
    --output-csv data/processed/predictions.csv

# 5. Evaluate
uv run dendrobium-succ evaluate -p data/processed/predictions.csv
```

### B. Re-run on your own FASTA

```bash
# Skip fetch; use your own protein FASTA
uv run dendrobium-succ run \
    --input-fasta my_proteins.faa \
    --output-csv my_predictions.csv
```

### C. Run individual steps

```bash
uv run dendrobium-succ fetch --accession GCF_001605985.2 -o proteins.faa
uv run dendrobium-succ extract -i proteins.faa -o fragments.fasta
uv run dendrobium-succ embed -f fragments.fasta -o features.pt
uv run dendrobium-succ predict --prott5-pt features.pt -f fragments.fasta -o predictions.csv
uv run dendrobium-succ evaluate -p predictions.csv
```

### D. Re-evaluate with different seed

```bash
uv run dendrobium-succ evaluate -p predictions.csv --seed 123 -o results_seed123
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Generic error (check `--log-file` for details) |
| 2 | Invalid arguments |
| 124 | Modal timeout |
| 127 | Command not found |

Use `echo $?` after a command to check its exit code.
