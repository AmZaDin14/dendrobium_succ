# Referensi CLI

> 🌐 **Bahasa:** [English](../cli-reference.md) | **Bahasa Indonesia**

Referensi lengkap untuk semua perintah `dendrobium-succ`. Untuk *rationale*
desain di balik perintah-perintah ini, lihat [arsitektur](arsitektur.md).
Untuk resep reproduksi, lihat [PLAN.md](../../PLAN.md).

> **Tips**: Jalankan perintah apa pun dengan `--help` untuk detail flag
> terkini:
> ```bash
> uv run dendrobium-succ <perintah> --help
> ```

---

## Opsi Global

Opsi ini berlaku untuk **semua** perintah dan dikonfigurasi di tingkat CLI
(bukan pada perintah individual).

| Flag | Tipe | Default | Deskripsi |
|------|------|---------|-----------|
| `--log-level` | `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL` | `INFO` | Tingkat log minimum |
| `--log-file` | PATH | `data/processed/run.log` | Path *file* log JSON |

```bash
# Contoh: log level debug ke file kustom
uv run dendrobium-succ --log-level DEBUG --log-file /tmp/run.log fetch --accession GCF_001605985.2
```

---

## `fetch` — Mengunduh FASTA Protein

Mengunduh FASTA protein dari NCBI Datasets v2 API. Salah satu dari
`--accession` atau `--organism` wajib diisi.

| Flag | Tipe | Default | Deskripsi |
|------|------|---------|-----------|
| `--output-fasta` / `-o` | PATH | `data/input/proteins.faa` | Path *output* FASTA protein |
| `--accession` / `-a` | TEXT | (tidak ada) | Nomor aksesi rakitan NCBI (misalnya `GCF_001605985.2`) |
| `--organism` | TEXT | (tidak ada) | Nama organisme untuk dicari di NCBI (misalnya `Dendrobium catenatum`) |

**Contoh:**

```bash
# Berdasarkan nomor aksesi (direkomendasikan — andal, rakitan tunggal)
uv run dendrobium-succ fetch --accession GCF_001605985.2 -o data/input/proteins.faa

# Berdasarkan organisme (mengambil hasil RefSeq pertama — mungkin bukan rakitan yang Anda inginkan)
uv run dendrobium-succ fetch --organism "Dendrobium catenatum" -o data/input/proteins.faa

# Dengan API key untuk rate limit lebih tinggi (10 req/s vs 5 req/s)
NCBI_API_KEY=xxx uv run dendrobium-succ fetch --accession GCF_001605985.2
```

**Keluaran:** `data/input/proteins.faa` (~19 MB, 34.389 protein untuk
GCF_001605985.2).

---

## `extract` — Mengekstrak Fragmen 33-mer

Mengekstrak jendela panjang tetap yang berpusat pada setiap residu lisin (K)
dari FASTA protein. Fragmen yang dekat dengan terminal diberi *padding*
dengan `X`.

| Flag | Tipe | Default | Deskripsi |
|------|------|---------|-----------|
| `--input-fasta` / `-i` | PATH | *(wajib)* | FASTA protein masukan (.faa / .fasta) |
| `--output-fasta` / `-o` | PATH | *(wajib)* | Path *output* FASTA fragmen |
| `--window-size` / `-w` | INT | `33` | Ukuran jendela fragmen (harus ganjil) |

**Contoh:**

```bash
# Jendela default (33, sesuai dengan masukan yang diharapkan RLSuccSite)
uv run dendrobium-succ extract -i data/input/proteins.faa -o data/processed/fragments.fasta

# Jendela kustom (misalnya 21 untuk konteks lebih pendek)
uv run dendrobium-succ extract -i proteins.faa -o fragments.fasta --window-size 21
```

**Format keluaran:**
```
>XP_123456.1|pos_19
RSDNLAFAARRCFRNSKIQTFSSRSFISTAADP
>XP_123456.1|pos_49
ADPTAGERNDDDAQSSKPLADDLFRSPPRSGGY
```

K selalu berada pada indeks 16 (0-based) dari fragmen 33-karakter.

---

## `download-model` — Sekali Saja: Simpan ProtT5-XL

Mengunduh `Rostlab/prot_t5_xl_uniref50` (~2.8 GB) ke Modal Volume untuk
digunakan kembali di semua run berikutnya. **Jalankan ini sekali** sebelum
`embed` pertama Anda.

**Tidak ada flag.**

**Contoh:**

```bash
# Pengaturan pertama kali
uv run dendrobium-succ download-model

# Verifikasi: seharusnya menampilkan file cache HuggingFace
modal volume ls prott5-model
```

**Biaya:** ~$0.01 (beberapa menit waktu kontainer).

---

## `embed` — Menghitung Embedding ProtT5-XL

Mengirim FASTA fragmen ke kontainer GPU Modal, yang memuat ProtT5-XL,
melakukan tokenisasi pada setiap 33-mer, menjalankan T5 encoder, dan
mengekstrak embedding center-residue (indeks 16) — vektor 1024-D per
fragmen.

| Flag | Tipe | Default | Deskripsi |
|------|------|---------|-----------|
| `--fragments-fasta` / `-f` | PATH | *(wajib)* | FASTA fragmen dari tahap `extract` |
| `--output-pt` / `-o` | PATH | *(wajib)* | Path *output* *file* `.pt` |
| `--batch-size` / `-b` | INT | `512` | Ukuran *batch* GPU (terbatas oleh VRAM) |

**Contoh:**

```bash
# Run standar
uv run dendrobium-succ embed -f data/processed/fragments.fasta -o data/processed/features.pt

# Batch lebih kecil (untuk GPU dengan VRAM lebih sedikit)
uv run dendrobium-succ embed -f fragments.fasta -o features.pt --batch-size 64

# Batch lebih besar (GPU sudah L40S 48 GB; flag --batch-size menyetelnya)
uv run dendrobium-succ embed -f fragments.fasta -o features.pt --batch-size 2048
```

**Keluaran:** `data/processed/features.pt` — *file* simpanan PyTorch dengan
`{'ids': list[str], 'features': Tensor[N, 1024]}`.

**Biaya:** ~$1.95/jam × ~2 menit = ~$0.06 untuk 10k fragmen. Berskala
linier.

---

## `predict` — Menjalankan Prediksi Ansambel RLSuccSite

Menjalankan ansambel RLSuccSite (model ProtT5 + model TPEMPPS_CCP) pada
fitur. Menghitung fitur buatan tangan secara *on-the-fly* dari FASTA fragmen.

| Flag | Tipe | Default | Deskripsi |
|------|------|---------|-----------|
| `--prott5-pt` | PATH | *(wajib)* | *File* `.pt` fitur ProtT5 (dari `embed`) |
| `--fragments-fasta` / `-f` | PATH | *(wajib)* | FASTA fragmen (dari `extract`) |
| `--output-csv` / `-o` | PATH | *(wajib)* | CSV prediksi keluaran |
| `--rlsuccsite-dir` | PATH | auto-detect | *Override* direktori RLSuccSite (default: `models/rlsuccsite/`) |
| `--num-workers` / `-n` | INT | `6` | Worker paralel untuk ekstraksi fitur buatan tangan |
| `--batch-size` / `-b` | INT | `2048` | Ukuran *batch* *streaming* |

**Contoh:**

```bash
# Run standar (menggunakan model yang disertakan di models/rlsuccsite/)
uv run dendrobium-succ predict \
    --prott5-pt data/processed/features.pt \
    -f data/processed/fragments.fasta \
    -o data/processed/predictions.csv

# Gunakan direktori RLSuccSite yang berbeda
uv run dendrobium-succ predict \
    --prott5-pt features.pt -f fragments.fasta -o predictions.csv \
    --rlsuccsite-dir /path/to/RLSuccSite

# Atur worker paralel untuk ekstraksi fitur yang lebih cepat
uv run dendrobium-succ predict \
    --prott5-pt features.pt -f fragments.fasta -o predictions.csv \
    --num-workers 12
```

**Keluaran:** `data/processed/predictions.csv` dengan 4 kolom:
`SequenceID`, `Sequence`, `PositiveProbability`, `PredictedLabel`.

**Persyaratan:** Interpreter Python dengan `torch`, `torchrl`,
`tensordict`, `protlearn` terinstal. Alat mendeteksi otomatis:
1. `../RLSuccSite/.venv/bin/python` (jika repositori *sibling* ada)
2. `.venv/bin/python` lokal (*fallback*)

Jika tidak ada yang berhasil, instal dependensi: `uv pip install torch
torchrl tensordict protlearn`.

---

## `run` — Pipeline Lengkap

Merangkai `fetch` → `extract` → `embed` → `predict` menjadi satu perintah.
Berikan salah satu `--input-fasta` (lewati fetch) atau
`--accession`/`--organism` (fetch dulu).

| Flag | Tipe | Default | Deskripsi |
|------|------|---------|-----------|
| `--output-csv` / `-o` | PATH | *(wajib)* | CSV prediksi keluaran |
| `--input-fasta` / `-i` | PATH | (tidak ada) | FASTA protein masukan (lewati fetch) |
| `--accession` / `-a` | TEXT | (tidak ada) | Nomor aksesi rakitan NCBI untuk di-fetch |
| `--organism` | TEXT | (tidak ada) | Nama organisme untuk dicari di NCBI |
| `--work-dir` | PATH | `<output_csv_dir>/intermediate` | Direktori untuk *file* antara |
| `--skip-model-download` | flag | `False` | Lewati unduhan ProtT5 (sudah dilakukan) |
| `--batch-size` / `-b` | INT | `512` | Ukuran *batch* GPU (dikirim ke `embed`) |
| `--num-workers` / `-n` | INT | `6` | Worker CPU (dikirim ke `predict`) |

**Contoh:**

```bash
# Dengan fetch (dari nomor aksesi NCBI)
uv run dendrobium-succ run \
    --accession GCF_001605985.2 \
    --output-csv data/processed/predictions.csv \
    --skip-model-download

# Dengan FASTA yang sudah ada (lewati fetch)
uv run dendrobium-succ run \
    --input-fasta data/input/proteins.faa \
    --output-csv data/processed/predictions.csv \
    --skip-model-download

# Dengan pencarian organisme
uv run dendrobium-succ run \
    --organism "Dendrobium catenatum" \
    --output-csv data/processed/predictions.csv
```

**Keluaran:**
- `<output_csv>` — prediksi akhir
- `<work_dir>/proteins.faa` — proteom yang di-fetch
- `<work_dir>/fragments.fasta` — fragmen yang diekstrak
- `<work_dir>/features.pt` — embedding ProtT5

---

## `evaluate` — Menilai Prediksi terhadap *Ground Truth* Wet-Lab

Menghitung recall pada set uji wet-lab Feng et al. 2017 ditambah presisi,
F1, MCC, AUC-ROC, AUC-PR menggunakan negatif sintetik 1:1 dari protein yang
sama (sesuai kebijakan RLSuccSite-NegCtrl).

| Flag | Tipe | Default | Deskripsi |
|------|------|---------|-----------|
| `--predictions-csv` / `-p` | PATH | *(wajib)* | CSV prediksi dari tahap `predict` |
| `--test-csv` | PATH | `data/wetlab/test.csv` | CSV situs uji wet-lab |
| `--output-dir` / `-o` | PATH | `data/wetlab/results` | Direktori keluaran |
| `--protein-fasta` | PATH | `data/wetlab/protein.faa` | Proteom RefSeq (untuk generasi negatif) |
| `--seed` | INT | `42` | *Seed* acak untuk *sampling* negatif |

**Contoh:**

```bash
# Evaluasi standar
uv run dendrobium-succ evaluate \
    --predictions-csv data/processed/predictions.csv \
    --test-csv data/wetlab/test.csv \
    --protein-fasta data/wetlab/protein.faa \
    --output-dir data/wetlab/results

# Seed kustom (untuk analisis sensitivitas)
uv run dendrobium-succ evaluate \
    -p predictions.csv --seed 123 -o results_seed123
```

**Keluaran (di `output-dir/`):**

| File | Isi |
|------|-----|
| `matches.csv` | Prediksi per situs vs *ground truth* (ProteinAccession, RefSeqAccession, Position, TrueLabel, Source, MatchedSequence, PositiveProbability, PredictedLabel, Status) |
| `metrics.json` | Metrik agregat (n_total, n_scored, n_positives, n_negatives, confusion_matrix, accuracy, precision, recall, f1, mcc, auc_roc, auc_pr) |
| `pr_curve.png` | Plot kurva precision-recall |

**Output konsol:**
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

## Alur Kerja Umum

### A. Pengaturan pertama kali + run

```bash
# 1. Instalasi
uv sync

# 2. Autentikasi Modal
uv tool install modal && modal setup

# 3. Simpan ProtT5-XL (sekali saja, ~3 menit, ~$0.01)
uv run dendrobium-succ download-model

# 4. Jalankan pipeline lengkap
uv run dendrobium-succ run \
    --accession GCF_001605985.2 \
    --output-csv data/processed/predictions.csv

# 5. Evaluasi
uv run dendrobium-succ evaluate -p data/processed/predictions.csv
```

### B. Run ulang pada FASTA Anda sendiri

```bash
# Lewati fetch; gunakan FASTA protein Anda sendiri
uv run dendrobium-succ run \
    --input-fasta my_proteins.faa \
    --output-csv my_predictions.csv
```

### C. Jalankan tahap individual

```bash
uv run dendrobium-succ fetch --accession GCF_001605985.2 -o proteins.faa
uv run dendrobium-succ extract -i proteins.faa -o fragments.fasta
uv run dendrobium-succ embed -f fragments.fasta -o features.pt
uv run dendrobium-succ predict --prott5-pt features.pt -f fragments.fasta -o predictions.csv
uv run dendrobium-succ evaluate -p predictions.csv
```

### D. Evaluasi ulang dengan seed berbeda

```bash
uv run dendrobium-succ evaluate -p predictions.csv --seed 123 -o results_seed123
```

---

## Kode Keluar

| Kode | Arti |
|------|------|
| 0 | Berhasil |
| 1 | Kesalahan umum (periksa `--log-file` untuk detail) |
| 2 | Argumen tidak valid |
| 124 | *Timeout* Modal |
| 127 | Perintah tidak ditemukan |

Gunakan `echo $?` setelah perintah untuk memeriksa kode keluar.
