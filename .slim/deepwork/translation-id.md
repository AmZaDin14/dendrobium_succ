# Deepwork: Indonesian Documentation Translation

## Task
> Create separate docs for indonesian version

**Status**: Setting up; exploring current English docs

---

## Goal

Create Indonesian (Bahasa Indonesia) translations of the existing English
documentation, maintaining the same structure and depth. The Indonesian
versions should serve the same 4 audiences (new users, researchers,
contributors, maintainers) as the English versions.

---

## Current state (to be confirmed)

### English docs (source for translation)
- `README.md` — 149 lines
- `PLAN.md` — 467 lines (largest, most detailed)
- `docs/architecture.md` — 305 lines
- `docs/cli-reference.md` — 357 lines

### Total translation scope
~1,278 lines of English to translate to Indonesian.

---

## Translation considerations

### What to translate
- All prose, headings, descriptions
- Docstrings and inline comments in code (user-facing only)
- Error messages and help text
- Table contents, lists

### What NOT to translate
- Code blocks (commands, file paths, variable names)
- CLI flag names (`--accession`, `--organism`, etc.)
- Technical terms with no Indonesian equivalent (ProtT5, Modal, RLSuccSite)
- URLs and external links
- Git commit messages (when shown)
- File names and directory paths

### Technical term glossary (draft)

| English | Indonesian | Notes |
|---------|-----------|-------|
| protein | protein | No translation, standard term |
| lysine | lisin | Scientific name, commonly kept as "lisin" |
| succinylation | suksinilasi | Biochemical process |
| K-site | situs K | The K refers to the amino acid code |
| fragment | fragmen | Standard term |
| residue | residu | Standard term |
| embedding | embedding | No standard translation, keep English |
| prediction | prediksi | Standard term |
| evaluation | evaluasi | Standard term |
| ensemble | ansambel | Standard ML term |
| pipeline | pipeline | No standard translation, keep English |
| orchestrator | orkestrator | Standard term |
| ground truth | ground truth | ML term, keep English |
| precision | presisi | Standard term |
| recall | recall / perolehan kembali | ML metric |
| F1 score | skor F1 | Standard term |
| MCC (Matthews Correlation Coefficient) | MCC | Keep abbreviation |
| AUC-ROC | AUC-ROC | Keep abbreviation |
| AUC-PR | AUC-PR | Keep abbreviation |
| threshold | ambang batas | Standard term |
| organism | organisme | Standard term |
| accession | nomor aksesi | NCBI term |
| assembly | rakitan | Genomic term |
| genome | genom | Standard term |
| proteome | proteom | Standard term |
| FASTA | FASTA | File format, keep English |
| checkpoint | checkpoint | ML term, keep English |
| weights | bobot | Standard term |
| GPU | GPU | Keep abbreviation |
| VRAM | VRAM | Keep abbreviation |
| volume | volume | Keep English for Modal context |
| orchestrator | orkestrator | Standard term |
| command | perintah | Standard term |
| flag | flag / opsi | CLI term |
| argument | argumen | Standard term |
| option | opsi | Standard term |
| directory | direktori | Standard term |
| file | berkas | Standard term (more common than "file") |
| repository | repositori | Standard term |
| dependency | dependensi | Standard term |
| virtual environment | lingkungan virtual | Standard term |
| CPU | CPU | Keep abbreviation |
| RAM | RAM | Keep abbreviation |
| inference | inferensi | ML term |
| model | model | No translation |
| training | pelatihan | ML term |
| test | uji | Standard term |
| validation | validasi | Standard term |
| test set | set uji | Standard term |
| train set | set pelatihan | Standard term |
| wet-lab | wet-lab / laboratorium basah | Mixed usage |
| reproducibility | reproduksibilitas | Standard term |
| version control | kontrol versi | Standard term |
| commit | commit | Git term, keep English |
| branch | cabang | Git term |
| merge | penggabungan | Git term |
| clone | klon | Git term |
| push | push | Git term, keep English |
| pull | pull | Git term, keep English |
| fork | fork | Git term, keep English |
| issue | issue / masalah | GitHub term |
| pull request | pull request | GitHub term, keep English |

---

## File structure options

### Option A: Parallel directories
```
README.md                          (English, current)
docs/architecture.md               (English, current)
docs/cli-reference.md              (English, current)
PLAN.md                            (English, current)
docs/id/README.md                  (Indonesian, new)
docs/id/architecture.md            (Indonesian, new)
docs/id/cli-reference.md           (Indonesian, new)
docs/id/PLAN.md                    (Indonesian, new)
```
Pros: Clear separation, easy to maintain, standard i18n pattern
Cons: Links between docs need to be language-aware

### Option B: Sibling files with language suffix
```
README.md
README.id.md
docs/architecture.md
docs/architecture.id.md
docs/cli-reference.md
docs/cli-reference.id.md
PLAN.md
PLAN.id.md
```
Pros: Same directory, easy to find pairs
Cons: Less clean, unusual convention

### Option C: Single i18n directory
```
docs/
├── en/
│   ├── README.md
│   ├── architecture.md
│   ├── cli-reference.md
│   └── PLAN.md
└── id/
    ├── README.md
    ├── architecture.md
    ├── cli-reference.md
    └── PLAN.md
README.md → docs/en/README.md (or keep at root?)
PLAN.md → docs/en/PLAN.md
```
Pros: Standard i18n pattern (e.g., MDN, Vue.js)
Cons: Breaks existing top-level README/PLAN location

**Recommendation**: Option A (parallel `docs/id/`). Maintains current
top-level structure, clean separation, easy to add more languages later.

---

## Phase plan (draft)

### Phase 0: Inventory + glossary finalization
- Confirm scope
- Finalize glossary (technical terms)
- Get @oracle review on plan

### Phase 1: Translate README.md
- `docs/id/README.md`
- 149 lines, ~30 min

### Phase 2: Translate docs/architecture.md
- `docs/id/architecture.md`
- 305 lines, ~60 min

### Phase 3: Translate docs/cli-reference.md
- `docs/id/cli-reference.md`
- 357 lines, ~70 min

### Phase 4: Translate PLAN.md
- `docs/id/PLAN.md`
- 467 lines, ~90 min
- Largest doc, may summarize sections if too long

### Phase 5: Cross-links and language switcher
- Add language links to English docs (e.g., "🇮🇩 Bahasa Indonesia" link)
- Indonesian docs link back to English
- README.md gets a prominent language switcher

### Phase 6: Final validation
- @oracle review of translation quality
- Spot-check technical terms
- Verify all links work

---

## Open questions

1. **Translate PLAN.md in full or summarize?** — 467 lines is a lot. Indonesian researchers may prefer a condensed version. Consider: translate Steps 0-5 in full, summarize Troubleshooting + Cost Estimate + File Map.
2. **Code comments in source files?** — translate user-facing docstrings in `src/dendrobium_succ/`? Or keep code in English (international standard)?
3. **Cultural adaptation vs literal translation?** — Indonesian docs may need to explain "what is a lysine" in more detail, since the audience may be less familiar with biochemistry.
4. **Glossary doc?** — add a `docs/id/GLOSARIUM.md` with the technical term translations?
5. **Date format, number format?** — Indonesian uses comma for decimal separator. Should we adapt?

---

## Reusable sessions
- ora-1: ses_116427f7effeTK8iGSS4ztUV9H (completed — can reuse for plan review)
- ora-2: ses_1163465a5ffeqLqu2HFQbwKLjS (completed — can reuse for plan review)

---

## Oracle Review (reconciled — ses_116427f7effeTK8iGSS4ztUV9H)

**Verdict**: Plan under-engineered on strategy, over-engineered on process.
- File structure `docs/id/` is correct (ISO 639-1 standard)
- Phasing: reduce 6 phases to 4 (batch translations)
- Glossary: expand to ~65 terms (add 15 missing, remove duplicates)
- Need explicit translation strategy (AI + human review)

**P0 — Translation strategy: AI + human review**
- AI does first pass with system prompt (glossary + formatting rules)
- Human review for terminology, naturalness, accuracy
- Spot-check with `diff` for structural parity

**P1 — Expand glossary to ~65 terms**
Add missing terms (suksinillisin, pembelajaran penguatan, asam amino, peptida, etc.). Remove duplicate "orchestrator" entry. Clarify ambiguous:
- "recall" → keep English (Indonesian ML practitioners say "recall")
- "wet-lab" → keep English (not "laboratorium basah")
- "file" → keep English (not "berkas" — "berkas" is formal but rarely used in practice)

**P2 — File structure**: `docs/id/` confirmed (ISO 639-1, not `bahasa` or `id-ID`)

**P3 — Cross-linking strategy**:
- Top of each Indonesian doc: `> 🌐 **Bahasa:** [English](../README.md) | **Bahasa Indonesia**`
- Top of each English doc: `> 🌐 **Language:** **English** | [Bahasa Indonesia](docs/id/README.md)`
- Internal cross-links in Indonesian docs point to other Indonesian docs
- Switcher placed below title, before "What This Does" section

**P4 — Direct translation, not simplified**
- No extra introductory material (audience is already technical)
- Exception: brief parenthetical on first use of untranslatable term

**P5 — Reduced phases (4 instead of 6)**:
```
Phase 1: Finalize glossary + translation template
Phase 2: Translate README + architecture (with GLOSARIUM.md)
Phase 3: Translate cli-reference + PLAN
Phase 4: Cross-links + validation
```

**P6 — Validation checklist**:
1. Terminology consistency (grep all glossary terms)
2. Structural parity (same headings, code blocks, tables)
3. Code block preservation (no translated commands)
4. Natural phrasing (read 3 random paragraphs per doc)
5. Link validation (internal links work, external still work)

**Critical gaps filled**:
- Translation memory: spreadsheet of repeated phrases
- Translation template: header format, Note/Warning/Tip handling, examples
- Number format: keep English format (docs show code output)
- Indonesian-specific typography: italicize scientific names same as English

---

## Phase Status

- [x] Phase 1: Finalize glossary + translation template
- [x] Phase 2: Translate README + architecture + GLOSARIUM
- [x] Phase 3: Translate cli-reference + PLAN
- [x] Phase 4: Cross-links + validation

**Status**: ✅ **COMPLETE** — Indonesian documentation shipped.

---

## Final Deliverables

| File | Lines | Purpose |
|------|-------|---------|
| `docs/id/README.md` | 154 | Landing page + quick start |
| `docs/id/arsitektur.md` | 322 | Architecture + 24 design decisions |
| `docs/id/referensi-cli.md` | 365 | CLI reference (7 commands) |
| `docs/id/PLAN.md` | 483 | Reproduction recipe (Steps 0-5) |
| `docs/id/GLOSARIUM.md` | 152 | 65-term glossary (6 categories) |
| **Total** | **1,476** | |

All 5 Indonesian docs cross-linked; language switchers on all 8 docs (4 English + 4 Indonesian).

---

## Specialist reviews
- [x] @oracle: plan review (ses_116427f7effeTK8iGSS4ztUV9H)
- [x] @oracle: final review (ses_116427f7effeTK8iGSS4ztUV9H, same session)

### Final review verdict (reconciled)
**95% shippable; 2 required fixes applied.**

P0 — Chinese character "渲染" → "dirender" in `docs/id/arsitektur.md:277`
- AI translation artifact; replaced in commit `b1d8075`

P1 — 3 broken cross-links in `docs/id/README.md`
- Line 58: `architecture.md` → `arsitektur.md`
- Line 90: `cli-reference.md` → `referensi-cli.md`
- Line 96: `architecture.md#keputusan-desain` → `arsitektur.md#keputusan-desain`
- Fixed in commit `b1d8075`

P2/P3 (optional, not fixed — acceptable localizations)
- Translated awk example output "PANJANG BURUK" in PLAN.md
- Indonesian example filenames `protein_saya.faa` / `prediksi_saya.csv` in referensi-cli.md

### Validation results
- All 5 Indonesian docs: 0 missing internal links
- Structural parity: 4 doc pairs with matching heading + code block counts
- Code blocks preserved (90+ blocks, no accidental translation of commands/paths)
- Glossary terms (lisin, prediksi, ansambel) consistent across all 5 docs
- English terms (ProtT5, Modal, RLSuccSite) preserved untranslated

---

## Commits

1. `ec36b61` — docs: add language switchers to English docs; fix broken id links
2. `b1d8075` — fix(docs/id): Chinese character artifact + 3 broken cross-links

---

## User decisions captured
- File structure: parallel `docs/id/` (ISO 639-1)
- PLAN.md translated in full (not summarized)
- No code docstring translation (keep code in English)
- Separate glossary doc (`docs/id/GLOSARIUM.md`, 65 terms)
- Direct translation, not simplified (audience is already technical)
- Keep "recall", "wet-lab", "file" in English
- Keep English number format (docs show code output)
- Translation strategy: AI + human review (hybrid)

