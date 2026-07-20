# *Dendrobium crumenatum* — Succinylation Prediction Pipeline

> **Language:** English
>
> Complete record of the workflow: from ITS sequencing data through to
> genome-scale succinylation site predictions for *Dendrobium crumenatum*
> (pigeon orchid) using the dendrobium-succ harness.

---

## Table of Contents

1. [Species Identification (BLAST)](#1-species-identification-blast)
2. [Why ITS Sequences Cannot Feed the Pipeline](#2-why-its-sequences-cannot-feed-the-pipeline)
3. [Genomic Resource Survey](#3-genomic-resource-survey)
4. [Figshare Dataset Exploration](#4-figshare-dataset-exploration)
5. [Genome Download and Proteome Extraction](#5-genome-download-and-proteome-extraction)
6. [Pipeline Execution: Extract → Embed → Predict](#6-pipeline-execution-extract--embed--predict)
7. [Output Summary](#7-output-summary)
8. [File Manifest](#8-file-manifest)

---

## 1. Species Identification (BLAST)

**What**: Nucleotide BLAST (BLASTn, megablast) of two Sanger-sequenced
amplicons (D7 and D11) against the NCBI non-redundant (nt) database.

**Why**: Confirm the species identity of the two samples before committing
to a reference genome and downstream analysis.

**When**: Initial discovery phase, before any genomic data acquisition.

**Where**: Samples sequenced by the user (source unspecified); BLAST
submitted to NCBI's public BLAST server at
`https://blast.ncbi.nlm.nih.gov/Blast.cgi`.

**Who**: Automated submission via Python `urllib` to the NCBI BLAST API
(`CMD=Put` → `CMD=Get` polling). Results parsed from XML format.

**How**:

1. Extract two FASTA entries from `sekuensing_dendrobium.md`:
   - **D7** — 847 nt (labeled `D. crumenantum`)
   - **D11** — 1052 nt (labeled `D. crumenantum`)
2. Submit each to NCBI BLAST via REST API with parameters:
   - `PROGRAM=blastn`, `DATABASE=nt`, `MEGABLAST=on`
   - `HITLIST_SIZE=10`, `FORMAT_TYPE=XML2`
3. Poll for results every 35 seconds until `Status=WAITING` changes to
   complete.
4. Parse top hits from XML response.

**Result**:

| Sample | Length | Top hit | Identity | Accession |
|--------|--------|---------|----------|-----------|
| D7 | 847 nt | *D. crumenatum* ITS region (18S-ITS1-5.8S-ITS2-26S) | **99.7%** (634/636) | AB593537.1 |
| D11 | 1052 nt | *D. crumenatum* ITS region (18S-ITS1-5.8S-ITS2-26S) | **99.1%** (783/790) | AB593537.1 |

**Notes**:
- The filename uses "crumenantum" which is a misspelling of the valid
  name *Dendrobium crumenatum* Sw., 1800 (Taxonomy ID 51096).
- Both samples unambiguously match *D. crumenatum*; the D7/D11 sample
  codes are local identifiers, not related to Figshare's D-species codes.
- Top hit AB593537.1 references a herbarium specimen from Japan (TBG 115833).

---

## 2. Why ITS Sequences Cannot Feed the Pipeline

**What**: The two sequences in `sekuensing_dendrobium.md` — D7 (847 nt)
and D11 (1052 nt) — are **Internal Transcribed Spacer (ITS) ribosomal
DNA** amplicons. The ITS region (ITS1–5.8S–ITS2) is a non-protein-coding
locus transcribed into rRNA, never translated into protein.

**Why**: The dendrobium-succ succinylation prediction pipeline operates
on **amino acid sequences** (proteins). It needs a protein FASTA input
containing lysine (K) residues that can be modified. Because ITS
sequences:
- Do not encode proteins (no open reading frame)
- Are transcribed into rRNA, not translated
- Contain no lysine (K) residues to evaluate
…they cannot be used as pipeline input.

**When**: After BLAST confirmed both samples as *D. crumenatum* (Section
1). At this point the sequences had served their purpose (species ID),
and a protein-level data source was needed to proceed.

**Where**: Raw sequencing reads in `sekuensing_dendrobium.md` at the repo
root.

**Who**: The user's Sanger-sequencing output (source unspecified).

**How**: The ITS locus is a standard plant DNA barcode marker — it
evolves fast enough to distinguish closely related species but has no
coding capacity. Ribosomal RNA genes are transcribed by RNA polymerase I
and processed into structural rRNAs (18S, 5.8S, 26S); they are never
exported to the cytoplasm for translation. The pipeline's *modus
operandi* (extract 33-mer windows around each K → embed with ProtT5 →
ensemble predict) cannot operate on a sequence that has no K residues.

### Could ITS sequences ever be used?

Yes, but only as a **bridge to coding sequences**, not directly:

| Scenario | How ITS helps | Then what |
|----------|---------------|-----------|
| **Transcriptome (RNA-seq)** | ITS region in raw reads helps confirm species origin of the sample | Assemble reads → predict ORFs → translate to proteins → run pipeline |
| **Whole-genome sequencing** | ITS helps confirm species before committing to assembly | Assemble genome → annotate genes → extract proteome → run pipeline |
| **Targeted gene discovery** | (Not applicable — ITS is non-coding) | Use conserved primers for specific gene families instead |

In this workflow, the ITS sequences fulfilled their role in **step 1
(species identification)**. The actual proteome used for prediction came
from the Figshare genome assembly (Sections 3–5), not from these reads.

### File reference

| File | Contents | Role in workflow |
|------|----------|------------------|
| `sekuensing_dendrobium.md` | D7 (847 nt) + D11 (1052 nt) ITS sequences | Species ID via BLAST → guided Figshare genome selection |

---

## 3. Genomic Resource Survey

**What**: Systematic search for publicly available *D. crumenatum* genomic
and proteomic data to determine suitability as input for the
dendrobium-succ pipeline.

**Why**: The dendrobium-succ pipeline requires a **protein FASTA**
(proteome) as input. ITS sequences alone (from step 1) do not encode
proteins.

**When**: After species identity was confirmed.

**Where**: Searched across NCBI Assembly, NCBI Nucleotide, NCBI Protein,
Figshare, and Google Scholar.

**Who**: Background research via web search and API queries (Exa search,
Figshare API v2).

**How**:

1. **NCBI Assembly query**: Search `datasets` CLI and web for
   "Dendrobium crumenatum" genome assembly.
2. **NCBI Taxonomy lookup**: Resolve `D. crumenatum` → txid51096.
3. **NCBI Protein query**: Query "txid51096[Organism]" for protein records.
4. **Figshare search**: Search academic repositories using terms
   "Dendrobium crumenatum genome assembly".
5. **Literature cross-reference**: Validate findings against Chen et al.
   2025 (*Nature Communications*) and Wang et al. 2026 (*Agronomy*).

**Result**:

| Resource | Available? | Details |
|----------|------------|---------|
| NCBI Assembly | ❌ **No** | No genome assembly deposited |
| NCBI RefSeq proteome | ❌ **No** | Only 53 individual protein records (targeted gene studies) |
| NCBI SRA / RNA-seq | ❌ **No** | No transcriptome data |
| Figshare (doi:10.6084/m9.figshare.26342338) | ✅ **Yes** | Chromosome-level assembly + predicted proteome; CC BY 4.0 |
| Closest RefSeq relative | ✅ | *D. catenatum* (GCF_001605985.2) — already in project |

**Decision**: Download *D. crumenatum* genome assembly from Figshare and
extract the predicted proteome, rather than using the closest relative
as a proxy.

---

## 3. Figshare Dataset Exploration

**What**: Examined the Figshare dataset
"Genome assembly and annotation of Dendrobium orchids" (Li, Zhang & Yu,
2024) to identify the correct species ZIP and understand its contents.

**Why**: The dataset contains 14+ Dendrobium genomes; the correct species
file must be identified and its internal structure understood before
downloading.

**When**: After the genomic resource survey identified Figshare as the
source.

**Where**: Figshare API v2 at `https://api.figshare.com/v2/articles/26342338`.

**Who**: Automated via `webfetch` to the Figshare API.

**How**:

1. Fetch the article metadata from the Figshare API
   (`/v2/articles/26342338`).
2. Iterate the `files` array to identify species ZIPs and their URLs.
3. Download and unzip `Readme.zip` (322 bytes) to decode species labels.
4. Map Figshare's numeric codes to species names.

**Result — species code mapping** (from `Readme.txt`):

| Code | Species | In D8.zip? |
|------|---------|------------|
| D1 | *D. Chao Praya Smile* | — |
| D3 | *D. discolor* | — |
| D5 | *D. crocatum* | — |
| D6 | *D. smilliae* | — |
| D7 | *D. leonis* | — |
| **D8** | ***D. crumenatum*** | **✅ Target** |
| D9 | *D. formosum* | — |
| D11 | *D. secundum* | — |
| D13–D21 | (other species) | — |

**Note**: The user's sample codes (D7, D11) are independent of Figshare's
coding — the BLAST identity is the reliable species ID, not the label.

**D8.zip contents**:

| File | Size | Description |
|------|------|-------------|
| `D8.genome.fasta` | 914 MB | Genome assembly (819 scaffolds) |
| `D8.protein.best.gff` | 32 MB | EVM gene predictions (GFF3 format) |
| `Readme.txt` | 27 B | "D8 refers to D. crumenatum" |

**Licence**: CC BY 4.0 — free to download, use, and redistribute with
attribution.

---

## 4. Genome Download and Proteome Extraction

**What**: Downloaded the *D. crumenatum* genome assembly and gene
annotation from Figshare, then extracted the predicted proteome (protein
FASTA).

**Why**: The pipeline needs a proteome as input; the genome assembly and
GFF annotation must be processed together to translate gene models into
protein sequences.

**When**: After confirming the Figshare dataset structure.

**Where**: Downloaded to `data/genomes/d_crumenatum/D8/`.

**Who**: Automated via `curl` download and a custom Python script plus
`gffread` for CDS→protein translation.

**How**:

### 4.1 Download

```bash
curl -sL -o D8.zip "https://ndownloader.figshare.com/files/49420159"
unzip D8.zip
```

### 4.2 GFF→Protein Translation

**Attempt 1 — Custom Python script failed.** A naive implementation
(`scripts/gff_to_protein.py`) that manually parsed GFF CDS features and
applied phase produced **72.8% proteins with internal stop codons**,
indicating incorrect phase handling.

**Attempt 2 — gffread succeeded.** The established tool `gffread`
(v0.12.7) correctly handles GFF3 phase values:

```bash
gffread \
    -g D8.genome.fasta \
    -y D8.protein.faa \
    D8.protein.best.gff
```

**Source**: Compiled from GitHub (gpertea/gffread, tag v0.12.7) since no
pre-built binary was available for the platform.

### 4.3 Sequence Cleaning

The predicted proteome contained 4,188 `.` (dot) characters — produced by
gffread when translating incomplete/ambiguous codons. These are not valid
amino acids and cause RLSuccSite's TPEMPPS feature extractor to crash
(`KeyError: '.'` in `aa_to_int` lookup).

Fix: replace `.` with `X` (standard unknown/resolution-lowering character):

```bash
python3 -c "
# Replace '.' with 'X' in sequence lines only (skip headers)
for line in content:
    if line.startswith('>'):
        result.append(line)
    else:
        result.append(line.replace('.', 'X'))
"
```

This produced `d_crumenatum_proteins_clean.faa`.

**Result**: **26,995 proteins**, 0 internal stop codons, average length
549 AA.

---

## 5. Pipeline Execution: Extract → Embed → Predict

**What**: Ran the dendrobium-succ pipeline on the *D. crumenatum* predicted
proteome to predict succinylation sites across the entire genome.

**Why**: Generate the first genome-scale succinylation site prediction for
*D. crumenatum*, enabling comparison with *D. officinale* and other
Dendrobium species.

**When**: Immediately after preparing the clean proteome.

**Where**: Local workstation (extract, predict) + Modal cloud GPU (embed).

**Who**: Automated via the `dendrobium-succ run` CLI command, which chains
all four stages.

**How**:

```bash
uv run dendrobium-succ run \
    --input-fasta data/input/d_crumenatum_proteins_clean.faa \
    --output-csv data/processed/d_crumenatum/predictions.csv \
    --skip-model-download
```

### Stage detail

| Stage | Command equivalent | Where | Time | Cost |
|-------|-------------------|-------|------|------|
| **Extract** | `dendrobium-succ extract` | Local CPU | ~2 sec | $0 |
| **Embed** | `dendrobium-succ embed` | Modal L40S GPU (48 GB) | ~29 min | ~$5–6 |
| **Predict** | `dendrobium-succ predict` | Local CPU (6 workers) | ~3.5 min | $0 |

### Stage 5a: Fragment Extraction

- **Input**: `d_crumenatum_proteins_clean.faa` (26,995 proteins, 15 MB)
- **Process**: For each lysine (K) in each protein, extract a 33-mer
  centered on the K with X-padding at termini. DNA-looking sequences
  (>100 bp, only ATGCN) are skipped.
- **Output**: `fragments.fasta` — **880,843 fragments**

### Stage 5b: ProtT5-XL Embedding (Modal GPU)

- **Input**: `fragments.fasta` (880,843 sequences)
- **Process**: Modal GPU container loads ProtT5-XL (Rostlab/prot_t5_xl_uniref50)
  from cached Volume → tokenizes each 33-mer → runs T5 encoder → extracts
  center-residue (index 16) 1024-D embedding → saves to Modal Volume.
  Non-standard AAs (U/Z/O/B) replaced with X before tokenization.
- **Batch size**: 512
- **GPU**: L40S (48 GB VRAM)
- **Output**: `features.pt` (3.5 GB, `{ids: list[str], features: Tensor[880843, 1024]}`)

### Stage 5c: RLSuccSite Ensemble Prediction

- **Input**: `features.pt` + `fragments.fasta`
- **Process**: Subprocess call to RLSuccSite's `Models/Predict.py`:
  1. Load ProtT5 embeddings (1024-D per fragment)
  2. Compute hand-crafted TPEMPPS features (528-D) + CCP features (462-D)
     on-the-fly from fragments FASTA
  3. Load two trained PPO models (ProtT5 model + TPEMPPS_CCP model)
  4. Produce 50/50 ensemble prediction
  - Multiprocessing with 6 workers, batch size 2048
- **Output**: `predictions.csv` (880,843 rows, 4 columns)

### Error encountered and resolution

| Attempt | Error | Cause | Resolution |
|---------|-------|-------|------------|
| 1st | `KeyError: '.'` in TPEMPPS.py | `.` chars in protein sequences from gffread translation of ambiguous codons | Replace `.` → `X` in proteome; re-run all 3 stages |
| 2nd | ✅ Success | Cleaned proteome | — |

---

## 6. Output Summary

**Final prediction file**: `data/processed/d_crumenatum/predictions.csv`

### Column structure

| Column | Type | Description |
|--------|------|-------------|
| `SequenceID` | `str` | Fragment identifier (`>scaffold.gene|pos_N`) |
| `Sequence` | `str` | 33-mer amino acid fragment (center = K) |
| `PositiveProbability` | `float` | Probability of succinylation (0–1) |
| `PredictedLabel` | `int` | Binary prediction: 0 = negative, 1 = positive |

### Aggregate statistics

| Metric | Value |
|--------|-------|
| Total K sites evaluated | **880,843** |
| Predicted succinylated | **215,136 (24.4%)** |
| Predicted non-succinylated | **665,707 (75.6%)** |
| Mean positive probability | **0.2754** |
| Probability range | **0.0000 – 1.0000** |

### Per-protein summary (example)

```csv
SequenceID,Sequence,PositiveProbability,PredictedLabel
>scaffold1.g00001.m1|pos_49,YSSIFNPDTELSTALPKVNVSRDDKDSMKPVEK,0.0121,0
>scaffold1.g00001.m1|pos_57,TELSTALPKVNVSRDDKDSMKPVEKNFFQKSFK,0.2856,0
>scaffold1.g00001.m1|pos_61,TALPKVNVSRDDKDSMKPVEKNFFQKSFKEVLA,0.9978,1
>scaffold1.g00001.m1|pos_65,KVNVSRDDKDSMKPVEKNFFQKSFKEVLASKGI,0.8690,1
>scaffold1.g00001.m1|pos_70,RDDKDSMKPVEKNFFQKSFKEVLASKGIAGKND,0.8803,1
```

---

## 7. File Manifest

| Path | Size | Description |
|------|------|-------------|
| `data/input/d_crumenatum_proteins.faa` | 15 MB | Raw predicted proteome (from gffread, contains `.`) |
| `data/input/d_crumenatum_proteins_clean.faa` | 15 MB | Cleaned proteome (`.` → `X`) |
| `data/genomes/d_crumenatum/D8/D8.genome.fasta` | 914 MB | Genome assembly (819 scaffolds) |
| `data/genomes/d_crumenatum/D8/D8.protein.best.gff` | 32 MB | EVM gene predictions (GFF3) |
| `data/genomes/d_crumenatum/D8/D8.protein.faa` | 15 MB | Extracted proteome (gffread output) |
| `data/genomes/d_crumenatum/D8/Readme.txt` | 27 B | "D8 refers to D. crumenatum" |
| `data/genomes/d_crumenatum/D8/D8.zip` | 241 MB | Original Figshare download |
| `data/processed/d_crumenatum/predictions.csv` | 226 MB | Final succinylation predictions |
| `data/processed/d_crumenatum/intermediate/fragments.fasta` | — | 880,843 33-mer fragments |
| `data/processed/d_crumenatum/intermediate/features.pt` | 3.5 GB | ProtT5-XL center embeddings |
| `scripts/gff_to_protein.py` | 6 KB | GFF→protein extraction helper |
| `sekuensing_dendrobium.md` | — | Original D7/D11 sequencing reads |

---

## Related documentation

| Document | Purpose |
|----------|---------|
| `PLAN.md` | Reproduction recipe for the full harness |
| `docs/architecture.md` | System design + 24 design decisions |
| `docs/cli-reference.md` | Full CLI command reference |
| `docs/agents/domain.md` | Domain doc consumer rules |

---

*Generated 2026-07-20 by the dendrobium-succ wayfinding workflow.*
