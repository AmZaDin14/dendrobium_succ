# Deepwork: Repo Rename + Folder Restructure

## Task
> Suggest changing repo name and restructure the folders

**Status**: Executing — name = `dendrobium_succ` (CLI: `dendrobium-succ`)

---

## Species correction (from user)

**Corrected understanding**:
- The species is **Dendrobium officinale** (= *Dendrobium catenatum*), an **orchid**
- The current repo name `d_officinale_succ` is **correct** — refers to *Dendrobium officinale*
- NCBI assembly GCF_001605985.2 = *Dendrobium catenatum* (verified via NCBI API)
- **Bug in `fetch.py:17-18`**: says "*Daucus catenatum* is NOT a valid NCBI Taxonomy name" — this is wrong. The valid name is *Dendrobium catenatum* (orchid genus), not *Daucus catenatum* (carrot genus). The current code's NCBI search would fail if a user tried `--organism` mode.
- The original RLSuccSite paper used *D. catenatum* (the orchid, same as our pipeline)

**Implications for the plan**:
- The misleading "Daucus" comments in `fetch.py` must be fixed (not "D. officinale is invalid" but rather "fetch.py defaults assume accession-based search since D. catenatum search may return multiple orchids")
- The pyproject description "Daucus officinale" is also wrong (should be "Dendrobium officinale")
- README.md, PLAN.md, and code comments have similar genus confusion to clean up

## User feedback (reconciled)
- `rlsuccsite` is the upstream model name (Zhangqingchao-Ch/RLSuccSite) — must NOT use
- User wants a different name, not yet chosen
- "Just plan first, some things need changing"
- `compare_results.py`: delete

---

## Oracle Review (reconciled)

**Verdict** (subject to name revision): Restructure = Option 2 (clean dead code only, no subpackages — YAGNI).

**Critical items the plan forgot** (must address):
1. `logging_config.py` hardcodes logger name `"d_officinale_succ"`
2. `evaluate.py:267` plot title has "D. officinale" (now correct species, but generic wording preferred)
3. `README.md:57` has dead prerequisite (references sibling `../RLSuccSite`)
4. `scripts/demo.sh` references old CLI + sibling path for mini dataset
5. `tests/test_extract.py:13` has old import path
6. `uv.lock` has package reference (regen with `uv sync`)
7. `__pycache__` cleanup needed after rename
8. **78+ total references** to sweep — not trivial find-and-replace
9. **Modal Volume names stay** (don't orphan ~2.8GB cached ProtT5); only Modal app name renames
10. **`fetch.py` "Daucus catenatum" comment is a bug** — should be "Dendrobium catenatum"

**Phase reordering recommended by oracle**:
- Add Phase -1: baseline capture + `git tag pre-rename`
- Move dead code cleanup BEFORE rename
- Drop subpackage restructure (Option 3)
- Validation must compare against captured baseline metrics

---

## Current State (corrected)

### Repo name
- Dir: `d_officinale_succ/`
- Package: `d_officinale_succ` (in `src/`)
- CLI: `d-officinale-succ`
- pyproject description: "Reproducible succinylation site prediction harness for Daucus officinale using RLSuccSite"
  - **Bug**: should say *Dendrobium officinale*, not *Daucus officinale*

### Species (corrected)
- Pipeline organism: **Dendrobium officinale** (= *D. catenatum*), an orchid
- NCBI assembly: GCF_001605985.2 = *Dendrobium catenatum*
- Upstream paper: *D. catenatum*
- Pipeline is organism-agnostic — works on any protein FASTA
- **Bug**: `fetch.py:17-18` says "*Daucus catenatum* is NOT a valid NCBI Taxonomy name" — this confuses the orchid genus *Dendrobium* with the carrot genus *Daucus*



### Current folder layout
```
d_officinale_succ/
├── pyproject.toml             # name="d-officinale-succ"
├── PLAN.md                    # 18+ references to old name
├── README.md                  # line 57: dead sibling prerequisite
├── src/d_officinale_succ/     # package (10 files)
│   ├── __init__.py            # docstring has old name
│   ├── cli.py                 # Typer CLI
│   ├── embed.py
│   ├── evaluate.py            # line 267: plot title "D. officinale"
│   ├── extract.py
│   ├── fetch.py
│   ├── logging_config.py      # lines 74, 122: hardcoded logger name
│   ├── pipeline.py
│   ├── predict.py
│   └── negctrl/               # DEAD, gitignored
├── modal/prott5_embed.py      # app name "d-officinale-prott5-embed"
├── models/rlsuccsite/         # self-contained model weights
├── data/{input,processed,wetlab}/
├── tests/test_extract.py      # line 13: old import
├── scripts/
│   ├── compare_results.py     # DEAD: sibling path, pandas not in deps
│   └── demo.sh                # references old CLI + ../RLSuccSite
├── last_run_embedding.ipynb   # DEAD: stale scratch, gitignored
```

---

## Final Plan (after oracle review + user correction)

### Phase -1: Baseline capture
- `git tag pre-rename` — rollback safety
- `uv run pytest` — confirm tests pass (record count)
- `uv run d-officinale-succ evaluate -p data/processed/full/predictions.csv -o data/wetlab/baseline` — capture current metrics

### Phase 0: User decision (BLOCKING)
- Confirm: name = TBD (not rlsuccsite)
- Confirm: restructure = Option 2 (dead code cleanup)
- Confirm: execute now, or just produce the plan

### Phase 1: Delete dead code
- `rm -rf src/d_officinale_succ/negctrl/`
- `rm last_run_embedding.ipynb`
- `rm scripts/compare_results.py`
- Remove `src/d_officinale_succ/negctrl/` line from `.gitignore`
- Commit: `chore: remove dead code (negctrl, stale notebook, one-off script)`

### Phase 2: Rename
Files to touch (~78+ references across):
| File | Change |
|------|--------|
| `src/d_officinale_succ/` | `git mv` → `src/<new_name>/` |
| Directory `d_officinale_succ/` | rename to `<new_name>/` (mv parent) |
| `pyproject.toml` | name, scripts, hatch packages, description (fix "Daucus officinale" → "Dendrobium officinale") |
| `src/<new_name>/__init__.py` | docstring |
| `src/<new_name>/cli.py` | name, help text, docstring |
| `src/<new_name>/logging_config.py` | logger namespace `"d_officinale_succ"` → `<new_name>` |
| `src/<new_name>/evaluate.py` | docstring import example, plot title (line 267) |
| `src/<new_name>/pipeline.py` | any refs to "D. officinale" / "Daucus" |
| `src/<new_name>/fetch.py` | **bug fix**: "Daucus catenatum" → "Dendrobium catenatum" (or "Dendrobium officinale") |
| `src/<new_name>/predict.py` | comment updates |
| `modal/prott5_embed.py` | app name `"d-officinale-prott5-embed"` → `<new_name>-prott5-embed` (NOT volume names) |
| `tests/test_extract.py` | import path (line 13) |
| `scripts/demo.sh` | CLI name, banner, mini dataset path note |
| `README.md` | title, description (fix genus), CLI examples, remove dead prerequisite (line 57) |
| `PLAN.md` | full sweep (18+ refs) |
| `.gitignore` | comment update |
| `uv.lock` | regen with `uv sync` |
| `find . -name __pycache__ -exec rm -rf {} +` | stale .pyc cleanup |

Commit: `refactor: rename package d_officinale_succ → <new_name>`

### Phase 3: Validate
- `uv sync` — regen lock
- `uv run pytest` — same count as baseline
- `uv run <new_name> --help` — CLI works
- `uv run <new_name> evaluate -p data/processed/full/predictions.csv -o data/wetlab/post_rename` — diff against baseline

### Phase 4: (Optional) GitHub remote
- Create repo `<new_name>` on GitHub
- `git remote add origin <url>`
- `git push -u origin main`

---

## Risks

1. **78+ references** — careful sweep needed (logger names, imports, docstrings differ in semantics)
2. **Modal Volume orphaning** — mitigated by keeping volume names (`prott5-model`, `prott5-output`)
3. **No git remote yet** — first push is to a new repo
4. **PyPI availability** — must verify the chosen name is not taken

---

## Name Options (user rejected `rlsuccsite`)

Constraint: must NOT collide with upstream `rlsuccsite` (Zhangqingchao-Ch/RLSuccSite).

### Organism-anchored (Dendrobium-focused)
| Option | Package | CLI | Notes |
|--------|---------|-----|-------|
| `dendrobium_succ` | `dendrobium_succ` | `dendrobium-succ` | Clear, accurate, but organism-specific |
| `dendro_succ` | `dendro_succ` | `dendro-succ` | Shorter, still species-clear |
| `do_succ` | `do_succ` | `do-succ` | Abbreviation (D. officinale), but ambiguous |

### Function-anchored (succinylation-focused)
| Option | Package | CLI | Notes |
|--------|---------|-----|-------|
| `k_succ` | `k_succ` | `k-succ` | "Lysine succinylation" — short, generic, K-centered |
| `succsite` | `succsite` | `succsite` | "Succinylation site" — short, descriptive |
| `succ_k` | `succ_k` | `succ-k` | Reads "succ-K", good |

### Tool-anchored (general-purpose predictor)
| Option | Package | CLI | Notes |
|--------|---------|-----|-------|
| `succinator` | `succinator` | `succinator` | Playful but descriptive; PyPI availability TBD |
| `succinylation_predictor` | `succinylation_predictor` | `succ-pred` | Very descriptive, long package name |
| `ksite_succ` | `ksite_succ` | `ksite-succ` | Explicit "K site succinylation" |

### My recommendation
`k_succ` — short, mnemonic, organism-agnostic, doesn't collide with upstream, and `k-succ` CLI is easy to type. The "K" refers to the lysine residue being modified, which is the actual biological subject of the tool.

---

## Open Decisions for User

1. **Name choice** (from table above or custom) — BLOCKING
2. **Execute now** or just produce this plan as the deliverable?
3. **Modal Volume names** — keep as-is (`prott5-model`, `prott5-output`) confirmed; defer until after name chosen

---

## Phase Status

### Phase -1: Baseline capture ✓
- `git tag pre-rename` — done
- `uv run pytest` — **6 passed**
- Baseline metrics: F1=0.6981, MCC=0.2890, Recall=0.8605, AUC-ROC=0.6486, AUC-PR=0.6127
- Saved to `data/wetlab/baseline/` (gitignored)

### Phase 1: Delete dead code (NEXT)
- `rm -rf src/d_officinale_succ/negctrl/`
- `rm last_run_embedding.ipynb`
- `rm scripts/compare_results.py`
- Remove `src/d_officinale_succ/negctrl/` line from `.gitignore`
- Commit: `chore: remove dead code (negctrl, stale notebook, one-off script)`

### Phase 2: Rename
- TBD (waiting for Phase 1 to complete)

### Phase 3: Validate
- TBD

### Phase 4: GitHub remote
- TBD (optional)

---

## Specialist reviews
- [x] @oracle: plan review (completed ses_116427f7effeTK8iGSS4ztUV9H)
- [ ] @oracle: Phase 1 review (after dead code cleanup)
- [ ] @oracle: Phase 2 review (after rename)
- [ ] @oracle: Phase 3 review (after validation)
