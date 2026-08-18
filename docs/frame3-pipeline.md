# Frame 3 Translation-to-Prediction Pipeline

> **What happens when you force an rDNA sequence through a succinylation
> prediction pipeline.** A curiosity-driven experiment documenting each
> step from raw DNA to predicted lysine sites, with full 5W+1H for every
> stage.

**TL;DR:** The ITS rDNA sequence from *Dendrobium crumenatum* was
translated in silico (Frame 3), BLASTN-verified, then fed through the
RLSuccSite succinylation prediction pipeline. The model produced
predictions — but they are biologically meaningless because rDNA is
never translated into protein in living cells.

---

## Step 1 — DNA Translation

| Element | |
|---------|------------|
| **What** | Translate raw nucleotide sequences into amino acids across all 6 reading frames |
| **Who** | BioPython `Seq.translate()` with standard genetic code table |
| **When** | After sequence retrieval, before any functional analysis |
| **Where** | Local execution (`uv run python`) |
| **Why** | To find open reading frames (ORFs) and the longest continuous translation (Frame 3) |
| **How** | Two sequences (D7, 847 nt; D11, 1052 nt) from `sekuensing_dendrobium.md` are read as `Bio.Seq.Seq` objects. Each is translated in 6 frames (3 forward, 3 reverse-complement) using `translate(table='Standard', to_stop=False)`. Stop codons appear as `*`. Partial codons at sequence ends trigger a `BiopythonWarning` but complete normally. |

**Why not ExPASy?** ExPASy Translate has a CGI API, but BioPython is
faster, offline, scriptable, and produces identical output for standard
translations.

---

## Step 2 — Frame 3 Identification

| Element | |
|---------|------------|
| **What** | Select Frame 3 (`5'3' Frame +3`) as the longest continuous ORF |
| **Who** | Manual inspection of the 6-frame translation output |
| **When** | After all 6 frames are generated |
| **Where** | Terminal output review |
| **Why** | Frame 3 has no internal stop codons across the entire sequence length, forming a continuous 281 aa (D7) / 350 aa (D11) peptide. The other 5 frames are littered with stop codons (`*`), confirming Frame 3 as the only viable reading frame. |
| **How** | For each sequence, 6 FASTA-like blocks are printed. Frame 3 is the only frame with >80% of the sequence length as uninterrupted codons. This matches the standard pattern of ITS rDNA: non-coding spacers (ITS1, ITS2) + the 5.8S rRNA gene, which happen to form a long ORF by chance when translated in one particular frame. |

**Biological note:** This is an *in silico* artifact. ITS rDNA is
transcribed to RNA, never translated to protein. The long ORF exists
because rDNA repeats have evolved with biased nucleotide composition
that suppresses stop codons in this reading frame.

---

## Step 3 — BLASTN Verification

| Element | |
|---------|------------|
| **What** | Confirm the nucleotide sequence identity against the NCBI non-redundant nucleotide database |
| **Who** | NCBI BLASTN web API (via `curl`) |
| **When** | After translation, to determine whether the sequence is fungal (as initially suspected) or host-plant (Dendrobium) |
| **Where** | `https://blast.ncbi.nlm.nih.gov/Blast.cgi` — REST API submission, results retrieved as plain text |
| **Why** | The ExPASy Frame 3 translation showed a 5.8S rRNA motif and was initially misattributed to *fungal* ITS rDNA. BLASTN resolved the species origin definitively. |
| **How** | The raw DNA sequence is POSTed to the NCBI BLAST API with `PROGRAM=blastn`, `DATABASE=nt`. The API returns a Request ID (RID). The client polls `CMD=Get&RID=<RID>&FORMAT_TYPE=Text` until `Status=READY`. Top hits are parsed from the text output. |

**Results:** All top 10 hits are *Dendrobium crumenatum* ITS rDNA
(99–100% identity). No fungal matches. The 5.8S rRNA motif is conserved
across eukaryotes — it is not fungus-specific.

| Rank | Accession | Species | Identity | E-value |
|------|-----------|---------|----------|---------|
| 1 | AB593537.1 | *D. crumenatum* | 100% | 0.0 |
| 2 | PX057331.1 | *D. crumenatum* | 100% | 0.0 |
| 3 | AF521608.1 | *D. crumenatum* | 100% | 0.0 |
| 4-10 | Various | *D. crumenatum* + *D. formosum* | 98–99% | 0.0 |

---

## Step 4 — 33-mer Fragment Extraction

| Element | |
|---------|------------|
| **What** | Extract 33-amino-acid windows centered on each lysine (K) residue |
| **Who** | `dendrobium-succ extract` CLI command |
| **When** | After Frame 3 AA sequence is saved as FASTA |
| **Where** | Local CPU (`src/dendrobium_succ/extract.py`) |
| **Why** | RLSuccSite requires 33-mer fragments as model input — the succinylation site (K) must be centered at position 16 of each fragment |
| **How** | The Frame 3 AA sequences are written to `data/input/frame3_translations.faa`. The `extract` command scans each protein, and for every K, extracts 16 residues upstream + K + 16 residues downstream. Termini are padded with `X`. Output: `data/processed/frame3_fragments.fasta`. |

**Output:** 27 fragments (13 from D7, 14 from D11).

---

## Step 5 — ProtT5-XL Embedding

| Element | |
|---------|------------|
| **What** | Compute 1024-dimensional protein-language-model embeddings for each fragment |
| **Who** | `dendrobium-succ embed` CLI command → Modal GPU container with ProtT5-XL |
| **When** | After fragment extraction |
| **Where** | Modal cloud (L40S GPU, 48 GB VRAM) |
| **Why** | ProtT5-XL (3B parameters) captures biophysical and evolutionary context around each K. ProtT5-based features are one half of the RLSuccSite ensemble. |
| **How** | Fragments FASTA is sent to Modal. The container loads `Rostlab/prot_t5_xl_uniref50` from a cached Volume, tokenizes each 33-mer, runs the T5 encoder, and extracts the center-residue (index 16) embedding. Returns a PyTorch tensor of shape `[27, 1024]`. |

**Cost:** ~$0.01 (L40S GPU, ~2 min container time).

**Output:** `data/processed/frame3_features.pt`

---

## Step 6 — Fragment Sanitization

| Element | |
|---------|------------|
| **What** | Replace stop-codon characters (`*`) with unknown-amino-acid placeholder (`X`) |
| **Who** | Simple Python string replacement |
| **When** | After extraction, before prediction |
| **Where** | Local script |
| **Why** | RLSuccSite's TPEMPPS feature encoder (`Feature/TPEMPPS.py`) maps amino acids to integers via a 21-letter alphabet (`ACDEFGHIKLMNPQRSTVWXY`). The `*` character is not in this alphabet and causes a `KeyError` at runtime. `X` is already handled (it maps to index 20). |
| **How** | 10 of 27 fragments contain `*` from stop codons in the Frame 3 translation. A `str.replace('*', 'X')` pass produces `data/processed/frame3_fragments_clean.fasta`. |

**TPEMPPS source context** (`TPEMPPS.py:20-24`):
```python
amino_acids = 'ACDEFGHIKLMNPQRSTVWXY'
# U, Z, O, B, - are substituted to X; * is NOT handled
protein_sequence = re.sub(r"[UZOB-]", "X", protein_sequence)
```

---

## Step 7 — RLSuccSite Ensemble Prediction

| Element | |
|---------|------------|
| **What** | Run the trained RLSuccSite ensemble (ProtT5 model + TPEMPPS_CCP model) to predict succinylation probability per K-site |
| **Who** | `dendrobium-succ predict` CLI command → `models/rlsuccsite/Models/Predict.py` |
| **When** | After sanitized fragments + ProtT5 embeddings are ready |
| **Where** | Local CPU (6-worker multiprocessing) |
| **Why** | The ensemble combines two orthogonal feature types: deep-learning (ProtT5) and hand-crafted physicochemical features (TPEMPPS_CCP). The 50/50 weighted vote between two PPO models produces the final score. |
| **How** | `Predict.py` loads the ProtT5 `.pt` file, computes TPEMPPS features on-the-fly from the fragment sequences, feeds both into two trained PPO reinforcement-learning classifiers, and averages their logits. Output is a CSV with columns: `SequenceID, Sequence, PositiveProbability, PredictedLabel`. |

**Result:**
- 27 K-sites processed
- 10 predicted positive (Prob ≥ 0.5)
- 17 predicted negative
- Top predictions: pos_278 (D7, 0.89), pos_86 (D11, 0.90)

---

## Biological Qualification

**These predictions are biologically meaningless.** The Frame 3
translation does not correspond to a real protein:

| Concern | Detail |
|---------|--------|
| rDNA is never translated | ITS1, 5.8S, ITS2 are transcribed into RNA, not translated |
| Stop codons masked | `*` → `X` hides translational termination |
| C-terminal X-padding | Fragments near the AA sequence end are padded with `X`, an artifact |
| No cellular context | Succinylation is a post-translational modification — it requires a real protein in a living cell |
| Model sees patterns only | RLSuccSite scores amino-acid patterns around K, regardless of biological origin |

The experiment demonstrates the pipeline runs end-to-end with any AA
input, but **predictions are only valid on real protein sequences** that
are actually expressed and succinylated in vivo.
