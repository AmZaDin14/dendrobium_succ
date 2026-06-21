# Architecture

This document describes how `dendrobium_succ` is put together and *why* each
piece exists. For a step-by-step reproduction recipe, see [PLAN.md](../PLAN.md).
For command-line details, see [cli-reference.md](cli-reference.md).

---

## System Overview

```
                 ┌─────────────────┐
                 │  NCBI Assembly   │  (accession or organism name)
                 └────────┬────────┘
                          │
              fetch       │   HTTP, NCBI Datasets v2 API
                          ▼
                 ┌─────────────────┐
                 │  Protein FASTA   │  (.faa)
                 └────────┬────────┘
                          │
              extract     │   CPU, local
                          ▼
                 ┌─────────────────┐
                 │ Fragments FASTA  │  (>id|pos_N, 33-char seq)
                 └────────┬────────┘
                          │
              embed       │   GPU, Modal
                          ▼
                 ┌─────────────────┐
                 │  features.pt     │  ({'ids': [...], 'features': [N,1024]})
                 └────────┬────────┘
                          │
              predict     │   CPU, local (subprocess to RLSuccSite)
                          ▼
                 ┌─────────────────┐
                 │ predictions.csv  │  (SequenceID, Sequence, Prob, Label)
                 └────────┬────────┘
                          │
              evaluate    │   CPU, local
                          ▼
                 ┌─────────────────┐
                 │ matches.csv      │
                 │ metrics.json     │  (F1, MCC, AUC-ROC, AUC-PR)
                 │ pr_curve.png     │
                 └─────────────────┘
```

---

## Components

Each of the 9 source modules has a single, well-defined role. Module names
mirror CLI command names where applicable.

### `fetch.py` — NCBI Datasets v2 API client
Downloads protein FASTA from NCBI by assembly accession (e.g.
`GCF_001605985.2`) or by organism name. Two endpoints:
- `GET /genome/taxon/{name}/dataset_report` — search by organism
- `GET /genome/accession/{acc}/download` — download ZIP, extract `protein.faa`

### `extract.py` — 33-mer fragment extractor
For each lysine (K) residue in each protein, writes a 33-character fragment
centered on the K. Fragments near termini are padded with 'X'. Output format:
```
>XP_123456.1|pos_19
RSDNLAFAARRCFRNSKIQTFSSRSFISTAADP
```

### `embed.py` — Modal GPU client
Subprocess wrapper that calls `modal run modal/prott5_embed.py::embed`. Sends
the fragments FASTA to a GPU container, receives a `.pt` file with
`{'ids': list[str], 'features': Tensor[N, 1024]}`.

### `modal/prott5_embed.py` — Modal GPU app
Loads ProtT5-XL (3B params, ~2.8 GB) from a cached Modal Volume, tokenizes
each 33-mer, runs the T5 encoder, and extracts the center-residue (index 16)
embedding — a 1024-D vector per fragment.

### `predict.py` — RLSuccSite ensemble wrapper
Subprocess wrapper around `models/rlsuccsite/Models/Predict.py`. Computes
hand-crafted features (TPEMPPS 528-D + CCP 462-D = 990-D) on-the-fly from
the fragments FASTA, loads both trained PPO models, and produces a 50/50
ensemble prediction.

### `evaluate.py` — wet-lab evaluation
Self-contained module that scores predictions against the Feng et al. 2017
wet-lab test set. Generates 1:1 same-protein synthetic negatives, joins
predictions to ground truth, computes precision/recall/F1/MCC/AUC-ROC/AUC-PR.
Outputs `matches.csv`, `metrics.json`, `pr_curve.png`.

### `pipeline.py` — full-pipeline orchestration
Chains `fetch` → `extract` → `embed` → `predict` into a single command.
Implements the `dendrobium-succ run` CLI command.

### `cli.py` — Typer CLI
7 commands: `fetch`, `extract`, `download-model`, `embed`, `predict`, `run`,
`evaluate`. Module name = command name convention.

### `logging_config.py` — rich + JSON logging
Structured logging: rich console output for humans, JSON file at
`data/processed/run.log` for machine parsing. Logger namespace:
`"dendrobium_succ"`.

---

## Data Flow

1. **Input**: Protein FASTA (fetched from NCBI or user-supplied)
2. **Extract**: One fragment per K residue (33 chars, centered)
3. **Embed**: One 1024-D vector per fragment (ProtT5-XL center residue)
4. **Predict**: One probability per fragment (ensemble of ProtT5 + TPEMPPS_CCP)
5. **Output**: CSV with 4 columns: `SequenceID`, `Sequence`,
   `PositiveProbability`, `PredictedLabel`
6. **Evaluate** (optional): Score against wet-lab ground truth, output
   `matches.csv`, `metrics.json`, `pr_curve.png`

The pipeline is **deterministic** for fixed inputs (no sampling, argmax
classification, fixed random seed for negative generation).

---

## Design Decisions

This section captures the "why" behind each major design choice. Decisions are
grouped by category. For a fuller discussion of trade-offs, see the
[git log](../) — conventional commits trace each change.

### Architecture (8)

**1. Why Modal for the GPU step only?**
ProtT5-XL is a 3B-parameter transformer (~2.8 GB). On CPU, embedding 1000
fragments takes ~30 min; on an L4 GPU, ~30 seconds. The other steps (HTTP
fetch, fragment extraction, feature computation, evaluation) are lightweight
CPU operations. Putting them all on GPU would waste money; keeping them local
keeps the pipeline portable. Modal gives us GPU-on-demand without managing
infrastructure.

**2. Why ProtT5 + TPEMPPS_CCP ensemble?**
This is what RLSuccSite uses, and it's the core of the upstream model. ProtT5
captures evolutionary context (a language model trained on UniRef50);
TPEMPPS_CCP captures hand-crafted physicochemical features (528-D + 462-D).
The 50/50 ensemble was empirically the best configuration in the RLSuccSite
paper.

**3. Why 33-mer fragments centered on K (index 16)?**
This is the format RLSuccSite's models expect. The center residue (the K of
interest) is at index 16 (0-based) of a 33-char window — 16 residues of
context on each side. Shorter windows lose context; longer windows dilute
the signal.

**4. Why fixed-length with X padding at termini?**
ML models need fixed input dimensions. 'X' is the standard placeholder for
"unknown/non-standard" amino acid in protein ML. Padding at termini (rather
than trimming) preserves the K at its true position. The K is always at
index 16 regardless of where in the protein it occurs.

**5. Why subprocess for `predict.py` (not Python import)?**
RLSuccSite's `Models/Predict.py` has its own dependency tree: `torch`,
`torchrl`, `tensordict`, `protlearn`. Importing it would bloat the harness's
`pyproject.toml` dependencies. Subprocess isolation keeps the harness lean
(only `biopython`, `modal`, `typer`, `rich`, `sklearn`, `matplotlib`,
`numpy`) and the heavy ML deps optional.

**6. Why prefer sibling venv over local venv?**
RLSuccSite's venv (`../RLSuccSite/.venv`, if present) has the heavy ML deps
installed; the local venv typically doesn't. The harness auto-detects: if
the sibling venv exists, use it; else fall back to the local venv. The
fallback path requires the user to `uv pip install torch torchrl
tensordict protlearn` manually.

**7. Why `batch_size=512` for embed but `2048` for predict?**
Different bottlenecks. Embedding is GPU-bound (VRAM limits batch — ProtT5-XL
uses ~6 GB, leaving ~42 GB for activations on a 48 GB L40S). Predict is
CPU-bound (hand-crafted feature extraction, streaming). Larger batches in
predict amortize subprocess startup; smaller batches in embed fit in VRAM.

**8. Why L40S GPU specifically?**
| GPU | VRAM | $/hr | Why not |
|-----|------|------|---------|
| T4 | 16 GB | $0.59 | Not enough VRAM for ProtT5-XL + activations |
| L4 | 24 GB | $0.80 | Budget option; may OOM on very large batches |
| A10 | 24 GB | $1.10 | More expensive than L4, same VRAM |
| L40S | 48 GB | $1.95 | ✅ Default — fits ProtT5-XL with headroom, fast throughput |

L40S is Modal's high-memory tier and the best $/perf for our workload. The
extra VRAM (vs L4) lets us handle batches up to ~1M fragments per run.

### Reproducibility (5)

**9. Why self-contained models (`models/rlsuccsite/`)?**
The project used to require a sibling `../RLSuccSite` repo. That was fragile:
clones would break if the sibling was missing or had the wrong commit. We
copied the model weights, scalers, and `Predict.py` into `models/rlsuccsite/`
so the harness works standalone. The sibling venv is still used (via auto
detection) for its pre-installed ML deps, but the models themselves ship
with the repo.

**10. Why NCBI assembly `GCF_001605985.2`?**
This is the *Dendrobium catenatum* (= *D. officinale*) RefSeq assembly used
in the RLSuccSite paper. It's the reference organism for the demo pipeline.
Searching NCBI by organism may return multiple Dendrobium assemblies; passing
`--accession` ensures a specific one.

**11. Why 1:1 same-protein synthetic negatives?**
Succinylation prediction is imbalanced: most K sites are not succinylated.
Without negatives, you can't compute precision/F1/MCC. The RLSuccSite-NegCtrl
policy uses 1:1 same-protein K-sites (one negative per positive, drawn from
the same protein's other K sites) — this controls for protein-level
confounders while avoiding trivial "different protein" negatives. We re-
implemented this in `evaluate.py` to avoid depending on the sibling negctrl
package.

**12. Why seed=42?**
Standard reproducibility default. The only stochastic step is random negative
sampling. Setting `seed=42` makes the evaluation deterministic.

**13. Why is `data/wetlab/protein.faa` (19 MB) committed?**
Most data is gitignored, but this reference proteome is the ground truth
for evaluation — it doesn't change between runs, and shipping it removes a
manual setup step. At 19 MB it's small enough to commit (well under GitHub's
100 MB limit). The gitignore explicitly tracks it via negation.

### Process (3)

**14. Why rename to `dendrobium_succ`?**
The original name `d_officinale_succ` was actually correct (refers to
*Dendrobium officinale*), but it didn't match the upstream model
(`rlsuccsite`) and the abbreviation was confusing. The new name:
- Disambiguates the orchid genus (*Dendrobium*) from the carrot genus
  (*Daucus*, which the old code's docstrings confused)
- Keeps the species focus (the demo organism)
- Doesn't collide with the upstream `rlsuccsite` package name

**15. Why fix the Daucus→Dendrobium genus bug?**
The old `fetch.py` and `cli.py` docstrings claimed "Daucus catenatum is NOT
a valid NCBI Taxonomy name" — this was wrong. The valid name is
*Dendrobium catenatum* (orchid); *Daucus catenatum* (carrot) doesn't exist.
The bug caused confusion about the demo organism. Now fixed.

**16. Why drop `scripts/compare_results.py`?**
It hardcoded a sibling `../RLSuccSite/results.csv` path that no longer exists
(we're self-contained). It used `pandas` (not in `pyproject.toml`). The
`evaluate.py` module is its proper replacement. Dead code removed in the
rename commit.

### Code organization (4)

**17. Why `src/` layout?**
The `src/` layout (vs flat) prevents accidental imports of the package from
the repo root. It forces tests to go through the installed package, catching
missing `__init__.py` files and import path bugs early. It's the convention
recommended by the [PyPA packaging guide](https://packaging.python.org/
en/latest/discussions/src-layout-vs-flat-layout/).

**18. Why flat package (no subpackages like `src/dendrobium_succ/pipeline/`)?**
With 9 source files, subpackages are premature nesting. Flat is easier to
navigate and keeps import paths short (`from .fetch import fetch_fasta` vs
`from .pipeline.fetch import fetch_fasta`). If we add more modules later,
we can split then.

**19. Why Typer for CLI?**
Typer is built on Click, has type-hint-driven argument parsing, generates
`--help` automatically, and renders nicely with rich. It's less boilerplate
than argparse, more modern than Click. The 7-command CLI fits Typer's sweet
spot.

**20. Why uv?**
Fast (Rust-based, 10-100x faster than pip), handles Python version
management, has a lockfile (`uv.lock`) for reproducibility, and is a single
binary. It replaces pip + venv + pip-tools + pyenv. [Astral](https://
astral.sh/) (the makers) also make `ruff`, which we don't use yet but could.

### Infrastructure (4)

**21. Why Modal Volume names `prott5-model` / `prott5-output`?**
Generic names (not `dendrobium-succ-model`) mean the volumes are reusable
across projects. If we renamed them, the ~2.8 GB of cached ProtT5 weights
would be orphaned on Modal's side. Keeping generic names is a deliberate
choice to keep infra stateless w.r.t. project name.

**22. Why Python ≥3.11?**
For `Path | None` union syntax (PEP 604) and `tomllib` (PEP 680). Python
3.11 is the minimum that has both. 3.10 has union syntax but not `tomllib`;
3.9 has neither. We pin to 3.11 for these modern features.

**23. Why `num_workers=6`?**
Matches RLSuccSite's upstream default for hand-crafted feature extraction
(see `models/rlsuccsite/Models/Predict.py`). Not tuned by us — inherited
from the model authors. Documented here so future maintainers know it's not
arbitrary.

**24. Why no git remote yet?**
The repo is local-only. When pushed, the recommended remote name matches
the project: `dendrobium-succ`. The repo is ready to push but no remote has
been configured.

---

## What This Doc Doesn't Cover

- **Step-by-step reproduction recipe** — see [PLAN.md](../PLAN.md)
- **CLI flag reference** — see [cli-reference.md](cli-reference.md)
- **Troubleshooting** — see PLAN.md §Troubleshooting
- **API reference for each module** — see docstrings in `src/dendrobium_succ/`
- **Glossary of domain terms** — not yet written (YAGNI)
