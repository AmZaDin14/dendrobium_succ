# Deepwork: Comprehensive Documentation

## Task
> Create comprehensive documentation that also include what and why decision

**Status**: Setting up; exploring current docs state

---

## Goal

Produce comprehensive, multi-audience documentation for the `dendrobium_succ` project that captures not just **what** the system does, but **why** each major decision was made. Documentation should serve:

1. **New users** — "How do I run this?"
2. **Researchers reproducing results** — "What were the exact steps, models, and parameters?"
3. **Contributors** — "How is the code organized? Why was it built this way?"
4. **Future maintainers** — "Why was X chosen over Y? What constraints drove this design?"

---

## Current state (to be confirmed)

### Existing docs
- `README.md` — quick-start only, ~85 lines, missing CLI ref, troubleshooting, design rationale
- `PLAN.md` — detailed reproduction recipe (393 lines), mentions old "Daucus" genus in places, hasn't been updated for evaluate command
- No `ARCHITECTURE.md`, no `DECISIONS.md`, no `docs/` directory
- `.slim/deepwork/rename-restructure.md` — internal process doc (not user-facing)

### Code as documentation
- Each module has a docstring
- `cli.py` has docstring header with usage examples
- Inline comments explain non-obvious choices (e.g., "Prefer sibling RLSuccSite venv over local venv" in `predict.py`)

### What's missing
- **Architecture overview** — system components, data flow, deployment model
- **Decision log** — why Modal, why ProtT5-XL, why 33-mer, why 1:1 negatives, why self-contained models, why the rename, why the species fix
- **CLI reference** — every command, every flag, with examples
- **Troubleshooting guide** — common failures and fixes
- **Performance/cost notes** — Modal GPU cost, embedding time, prediction time
- **Glossary** — terms like K-site, succinylation, ensemble, etc.

---

## Major decisions to document (what + why)

### Architecture decisions
1. **Modal for GPU, local for everything else** — why split?
2. **ProtT5-XL + TPEMPPS_CCP ensemble** — what is each model contributing?
3. **33-mer fragments centered on K (index 16)** — why this window?
4. **Fixed-length with X padding at termini** — why not variable-length?

### Reproducibility decisions
5. **Self-contained RLSuccSite models in `models/rlsuccsite/`** — why bundle vs sibling?
6. **NCBI assembly GCF_001605985.2 (Dendrobium catenatum)** — why this specific assembly?
7. **Seed=42 for negative sampling** — why 42?
8. **1:1 same-protein synthetic negatives** — why this ratio and policy?
9. **No git remote yet** — intentional?

### Process decisions
10. **Rename to `dendrobium_succ`** — what was wrong with old name? Why this name?
11. **Fix Daucus→Dendrobium genus bug** — what was the confusion? Why fix now?
12. **Drop `scripts/compare_results.py`** — why was it deleted?
13. **Use uv** — why uv over pip/poetry?
14. **Typer for CLI** — why typer over argparse/click?

### Code organization decisions
15. **`src/` layout** — why not flat?
16. **Flat package (no subpackages)** — why not `src/dendrobium_succ/pipeline/`?
17. **Module names = CLI command names** — convention?

---

## Audience mapping

| Doc | Audience | Depth |
|-----|----------|-------|
| `README.md` | New users, quick start | Shallow |
| `docs/quickstart.md` | First-time users, step-by-step | Medium |
| `docs/architecture.md` | Contributors, maintainers | Deep |
| `docs/decisions.md` | Maintainers, reviewers | Deep |
| `docs/cli-reference.md` | Power users | Reference |
| `docs/troubleshooting.md` | Anyone hitting errors | Shallow-Medium |
| `docs/glossary.md` | Domain newcomers | Reference |
| `PLAN.md` | Reproducibility researchers | Very deep |

---

## Phase plan (draft)

### Phase 0: Inventory + draft outline
- Confirm doc gaps
- Write the ADR skeleton
- Get @oracle review on plan

### Phase 1: Architecture doc
- `docs/architecture.md` — system diagram, component roles, data flow
- Why each component exists

### Phase 2: Decision log (ADRs)
- `docs/decisions.md` — one section per major decision
- Format: Context → Decision → Consequences

### Phase 3: README rewrite
- Top-level landing page
- Links to all other docs
- Current quick-start (fetch → extract → embed → predict → evaluate)

### Phase 4: CLI reference
- `docs/cli-reference.md` — all 7 commands documented
- Each command: purpose, all flags, examples

### Phase 5: PLAN.md refresh
- Update for current state (evaluate command, self-contained, renamed)
- Keep the reproduction recipe

### Phase 6: Supporting docs
- `docs/troubleshooting.md` — common errors
- `docs/glossary.md` — domain terms
- `docs/quickstart.md` — extended walkthrough

### Phase 7: Final validation
- Render check (no broken links, accurate paths)
- @oracle review of each phase
- Commit in conventional-commits style

---

## Open questions

1. **Single mega-doc or modular `docs/`?** — Modular is more maintainable, single is more discoverable. Diátaxis framework (tutorials/how-to/reference/explanation) is a good fit.
2. **ADRs as separate files or one DECISIONS.md?** — Separate files scale better, single file is simpler for small projects.
3. **Keep PLAN.md as a top-level doc or move to `docs/`?** — Top-level signals "this is the recipe", `docs/` is more organized.
4. **Audience priority?** — New users > Researchers > Contributors > Maintainers (based on "how do I run this" being the #1 question).

---

## Reusable sessions
- ora-1: ses_116427f7effeTK8iGSS4ztUV9H (plan review)
- ora-2: ses_1163465a5ffeqLqu2HFQbwKLjS (Phase 2 rename review)
- Both completed, can be reused for documentation plan review

---

## Phase Status

- [ ] Phase 0: Inventory + draft outline (in progress)
- [ ] Phase 1: Architecture doc
- [ ] Phase 2: Decision log
- [ ] Phase 3: README rewrite
- [ ] Phase 4: CLI reference
- [ ] Phase 5: PLAN.md refresh
- [ ] Phase 6: Supporting docs
- [ ] Phase 7: Final validation

---

## Specialist reviews
- [ ] @oracle: plan review
- [ ] @oracle: Phase 1 (architecture)
- [ ] @oracle: Phase 2 (decisions)
- [ ] @oracle: Phase 3 (README)
- [ ] @oracle: Phase 4 (CLI ref)
- [ ] @oracle: Phase 5 (PLAN.md)
- [ ] @oracle: Phase 6 (supporting docs)
- [ ] @oracle: Phase 7 (final)

---

## Oracle Review (reconciled — ses_116427f7effeTK8iGSS4ztUV9H)

**Verdict**: Plan is over-engineered for a 9-module single-developer project.
- 8 docs for 9 modules = 1:1 ratio (most projects with 10x the codebase have fewer)
- 7 phases with 7 reviews = waterfall documentation
- ADR formalism unnecessary (use "Design Decisions" section in architecture doc)

**Simplified plan (4 files, 5 phases, 2 reviews)**:
```
README.md                  # Landing page (expand to ~150 lines)
PLAN.md                    # Reproduction recipe (fix stale content)
docs/architecture.md       # System design + Design Decisions (combined)
docs/cli-reference.md      # All 7 commands with flags
```

**What to cut and why**:
- `docs/decisions.md` (standalone) → merge into `architecture.md`
- `docs/quickstart.md` → redundant with README
- `docs/troubleshooting.md` → consolidate into PLAN.md
- `docs/glossary.md` → YAGNI (add when 2nd user asks)

**Phase 0 (NEW, do first)**: Fix stale content before writing new docs
- PLAN.md: remove sibling repo requirement (§2, lines 62-79), update verify commands (211-218), update troubleshooting (331-339), update file map (372-393)
- README.md: add `evaluate` to CLI table (lines 33-42)
- demo.sh: either ship mini dataset or document sibling requirement (code bug, not just docs)

**Missing what+why decisions to add** (8 new, total 25):
- #18: Why subprocess for predict.py (not import)? — subprocess isolation for dependency management
- #19: Why prefer sibling venv over local venv? — sibling has torch/torchrl, local doesn't
- #20: Why batch_size=512 for embed but 2048 for predict? — GPU vs CPU bottlenecks
- #21: Why L4 GPU specifically? — 24GB VRAM, good $/perf, Modal default
- #22: Why Modal Volume names `prott5-model`/`prott5-output`? — generic = reusable across projects
- #23: Why Python ≥3.11? — Path|None union syntax, tomllib
- #24: Why `num_workers=6`? — matches RLSuccSite's default (inherited, not tuned)
- #25: Why `data/wetlab/protein.faa` 19MB committed? — reference proteome, ground truth for eval

**Oracle review cadence**: 2 reviews total (plan + final), not 8

---

## Revised Phase Plan

### Phase 0: Fix stale content (NEW — do first)
- Fix PLAN.md stale sections
- Fix README.md CLI table (add `evaluate`)
- Address demo.sh sibling dependency
- Commit: `docs: fix stale references to sibling RLSuccSite`

### Phase 1: Expand README.md
- Add "How It Works" section
- Add "Evaluation" section
- Update Project Structure (add evaluate.py, logging_config.py, data/wetlab/)
- Add links to docs/architecture.md and docs/cli-reference.md
- Keep under 150 lines

### Phase 2: Write docs/architecture.md
- System diagram (reuse PLAN.md's ASCII art)
- Component roles (what each module does)
- Data flow (fetch → extract → embed → predict → evaluate)
- "Design Decisions" section (all 25 decisions, grouped by category)
- Keep under 400 lines

### Phase 3: Write docs/cli-reference.md
- All 7 commands with every flag
- Consider auto-generating from typer
- One example per command minimum

### Phase 4: Refresh PLAN.md
- Add evaluate step (Step 5)
- Update file map
- Cross-link to docs/architecture.md for "why"
- Keep PLAN.md focused on "how to reproduce"

### Phase 5: Validate
- Check all internal links
- Verify every command in docs matches `--help` output
- @oracle final review for consistency, accuracy, completeness

