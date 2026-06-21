# Rencana Reproduksi: Prediksi Situs Suksinilasi untuk *Dendrobium officinale*

> 🌐 **Bahasa:** [English](../../PLAN.md) | **Bahasa Indonesia**

Dokumen ini adalah resep langkah demi langkah yang dapat direproduksi untuk
menjalankan inferensi RLSuccSite pada dataset protein baru menggunakan
*tool* ini. Setiap langkah diotomasi dan dapat dilacak melalui *git
conventional commits*.

**Dokumen terkait:**
- [README.md](../../README.md) — mulai cepat + halaman arahan
- [docs/id/arsitektur.md](../arsitektur.md) — desain sistem + 24 keputusan desain (the "why")
- [docs/id/referensi-cli.md](../referensi-cli.md) — referensi lengkap perintah CLI

---

## Gambaran Arsitektur

```
                 ┌─────────────────┐
                 │  Rakitan NCBI   │  (nomor aksesi atau nama organisme)
                 └────────┬────────┘
                          │
              fetch       │   HTTP, NCBI Datasets v2 API
              Langkah 0   │   Unduh protein.faa dari rakitan genom
                          ▼
                 ┌─────────────────┐
                 │  Protein FASTA   │  (.faa)
                 └────────┬────────┘
                          │
              extract     │   CPU, lokal
              Langkah 1   │   Ekstrak fragmen 33-mer di sekitar setiap K
                          ▼
                 ┌─────────────────┐
                 │ Fragmen FASTA   │  (>id|pos_N, seq 33-karakter)
                 └────────┬────────┘
                          │
              embed       │   GPU, Modal
              Langkah 2   │   Embedding center-residue ProtT5-XL
                          ▼
                 ┌─────────────────┐
                 │  features.pt     │  ({'ids': [...], 'features': [N,1024]})
                 └────────┬────────┘
                          │
              predict     │   CPU, lokal (subprocess ke RLSuccSite)
              Langkah 3   │   Ansambel: model ProtT5 + model TPEMPPS_CCP
                          ▼
                 ┌─────────────────┐
                 │ predictions.csv  │  (SequenceID, Sequence, Prob, Label)
                 └────────┬────────┘
                          │
              evaluate    │   CPU, lokal
              Langkah 4   │   Nilai terhadap ground truth wet-lab
                          ▼
                 ┌─────────────────┐
                 │ matches.csv      │  (prediksi per situs vs kebenaran)
                 │ metrics.json     │  (F1, MCC, AUC-ROC, AUC-PR)
                 │ pr_curve.png     │  (plot precision-recall)
                 └─────────────────┘
```

**Mengapa Modal hanya untuk Langkah 2?** ProtT5-XL adalah transformer
dengan 3 miliar parameter (~2.8 GB). Pada CPU, *embedding* 1000 fragmen
memakan waktu ~30 menit; pada GPU L40S, ~30 detik. Langkah 0, 1, 3, dan 4
adalah operasi CPU/HTTP yang ringan. Lihat
[docs/id/arsitektur.md](../arsitektur.md) untuk rationale desain lengkap.

---

## Prasyarat

### 1. Alat Sistem

| Alat | Versi | Instalasi |
|------|-------|-----------|
| Python | ≥ 3.11 | `uv python install 3.11` |
| uv | ≥ 0.4 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| git | ≥ 2.40 | *package manager* sistem |
| modal | ≥ 0.64 | `pip install modal` atau `uv tool install modal` |

### 2. Model RLSuccSite (Disertakan)

Bobot model sudah disertakan dalam `models/rlsuccsite/`. Tidak memerlukan
repositori *sibling*. Tahap prediksi dapat menggunakan model lokal secara
langsung; lihat `src/dendrobium_succ/predict.py` untuk logika resolusi.
Tahap prediksi *memang* membutuhkan interpreter Python dengan `torch`,
`torchrl`, `tensordict`, dan `protlearn` terinstal — ini biasanya disediakan
oleh *sibling* `../RLSuccSite/.venv` (jika ada), dengan *fallback* ke
`.venv` lokal.

### 3. Akun Modal

```bash
modal setup    # autentikasi (sekali saja)
modal token new --name dendrobium-succ
```

### 4. Tool Ini

```bash
cd /home/amri/Code/python/dendrobium_succ
uv sync       # instal dependensi tool (biopython, modal, typer, rich, sklearn, matplotlib, numpy)
```

---

## Eksekusi Langkah demi Langkah

### Langkah 0 — Sekali Saja: Simpan ProtT5-XL di Modal Volume

ProtT5-XL (~2.8 GB) diunduh sekali dan disimpan di Modal Volume untuk
digunakan kembali di semua run berikutnya.

```bash
uv run dendrobium-succ download-model
# atau langsung:
modal run modal/prott5_embed.py::download_model
```

**Verifikasi:** `modal volume ls prott5-model` seharusnya menampilkan file
cache HuggingFace.

**Biaya:** ~$0.01 (beberapa menit waktu kontainer untuk unduhan).

---

### Langkah 1 — Fetch FASTA Protein dari NCBI (HTTP, lokal)

Unduh proteom lengkap (.faa) untuk rakitan genom dari NCBI Datasets v2 API.
Dua mode:

**Berdasarkan nomor aksesi (direkomendasikan — andal):**
```bash
# Rakitan D. catenatum (sama dengan dataset demo RLSuccSite)
uv run dendrobium-succ fetch \
    --accession GCF_001605985.2 \
    --output-fasta data/input/proteins.faa
```

**Berdasarkan nama organisme (mencari Taksonomi NCBI):**
```bash
uv run dendrobium-succ fetch \
    --organism "Dendrobium catenatum" \
    --output-fasta data/input/proteins.faa
```

**Cara kerjanya:**
1. (Jika `--organism`) Mencari `GET /genome/taxon/{name}/dataset_report`
   untuk rakitan RefSeq, mengambil hasil pertama
2. Mengunduh `GET /genome/accession/{acc}/download?include_annotation_type=PROT_FASTA`
   — mengembalikan ZIP
3. Mengekstrak `ncbi_dataset/data/{acc}/protein.faa` dari ZIP

**Keluaran:** `data/input/proteins.faa` (misalnya 19 MB, 34.389 protein
untuk GCF_001605985.2)

**Verifikasi:**
```bash
grep -c "^>" data/input/proteins.faa    # jumlah protein
head -2 data/input/proteins.faa          # periksa format
```

**Catatan:**
- Pencarian berdasarkan organisme mungkin mengembalikan beberapa rakitan
  Dendrobium; berikan `--accession GCF_001605985.2` untuk rakitan spesifik
  (direkomendasikan)
- Atur variabel lingkungan `NCBI_API_KEY` untuk 10 req/s (default 5 req/s)
  — opsional
- Tidak memerlukan API key; tidak perlu autentikasi

---

### Langkah 2 — Ekstrak Fragmen 33-mer (CPU, lokal)

Diberikan FASTA protein (di-fetch di atas atau milik Anda sendiri), ekstrak
jendela 33-mer yang berpusat pada setiap residu lisin (K). Fragmen yang
dekat dengan terminal diberi *padding* dengan 'X'.

```bash
uv run dendrobium-succ extract \
    --input-fasta data/input/proteins.faa \
    --output-fasta data/processed/fragments.fasta
```

**Keluaran:** `data/processed/fragments.fasta`

Format:
```
>XP_123456.1|pos_19
RSDNLAFAARRCFRNSKIQTFSSRSFISTAADP
>XP_123456.1|pos_49
ADPTAGERNDDDAQSSKPLADDLFRSPPRSGGY
```

**Verifikasi:**
```bash
grep -c "^>" data/processed/fragments.fasta    # jumlah situs K
awk 'NR%2==0 {if (length($0)!=33) print "PANJANG BURUK: "$0}' data/processed/fragments.fasta
```

---

### Langkah 3 — Embedding ProtT5-XL (GPU, Modal)

Kirim FASTA fragmen ke Modal, di mana kontainer GPU (L40S, 48 GB) memuat
ProtT5-XL, melakukan tokenisasi pada setiap 33-mer, menjalankan T5 encoder,
dan mengekstrak embedding center-residue (indeks 16) — vektor 1024-D per
fragmen.

```bash
uv run dendrobium-succ embed \
    --fragments-fasta data/processed/fragments.fasta \
    --output-pt data/processed/features.pt
```

**Apa yang terjadi:**
1. Konten FASTA dikirim ke Modal sebagai argumen string
2. Kontainer GPU mulai (atau menggunakan yang hangat), memuat ProtT5-XL dari
   Volume yang disimpan
3. Fragmen diproses dalam *batch* 512 (dapat dikonfigurasi)
4. *File* `.pt` ditulis ke Modal Volume, kemudian diunduh secara lokal

**Keluaran:** `data/processed/features.pt`

```python
# Verifikasi secara lokal (menggunakan venv lokal):
uv run python -c "
import torch
d = torch.load('data/processed/features.pt', map_location='cpu')
print(d['features'].shape)  # seharusnya [N, 1024]
print(len(d['ids']))        # seharusnya N
print(d['ids'][:3])         # 3 ID pertama
"
```

**Biaya:** ~$1.95/jam × ~2 menit = ~$0.06 untuk 10k fragmen. Berskala linier.

**Pemilihan GPU:**
| GPU | VRAM | $/jam | Terbaik untuk |
|-----|------|-------|---------------|
| L4 | 24 GB | $0.80 | Opsi hemat; mungkin OOM pada *batch* sangat besar |
| A10 | 24 GB | $1.10 | Alternatif untuk L4 |
| L40S | 48 GB | $1.95 | Default. Menangani hingga ~1 juta fragmen per run |

Untuk mengubah GPU, edit `modal/prott5_embed.py` baris `gpu="L40S"`.

---

### Langkah 4 — Prediksi Ansambel RLSuccSite (CPU, lokal)

Jalankan `Models/Predict.py` RLSuccSite melalui lingkungan virtualnya sendiri.
Ini menghitung fitur buatan tangan (TPEMPPS 528-D + CCP 462-D = 990-D)
secara *on-the-fly* dari FASTA fragmen, memuat kedua model PPO terlatih,
dan menghasilkan prediksi ansambel 50/50.

```bash
uv run dendrobium-succ predict \
    --prott5-pt data/processed/features.pt \
    --fragments-fasta data/processed/fragments.fasta \
    --output-csv data/processed/predictions.csv
```

**Keluaran:** `data/processed/predictions.csv`

| Kolom | Deskripsi |
|-------|-----------|
| SequenceID | ID fragmen (misalnya `>XP_123456.1\|pos_19`) |
| Sequence | Fragmen asam amino 33-mer |
| PositiveProbability | Float 0–1, probabilitas suksinilasi |
| PredictedLabel | 0 (negatif) atau 1 (positif) |

**Verifikasi:**
```bash
head -5 data/processed/predictions.csv
# Hitung situs prediksi positif:
awk -F',' 'NR>1 && $4==1' data/processed/predictions.csv | wc -l
```

---

### Langkah 5 — Evaluasi Wet-Lab (CPU, lokal)

Nilai prediksi terhadap set uji wet-lab Feng et al. 2017 (314 situs
suksinilasi pada *D. officinale*). Evaluator menghasilkan negatif sintetik
1:1 dari protein yang sama, menggabungkan prediksi dengan *ground truth*,
dan menghitung presisi, recall, F1, MCC, AUC-ROC, AUC-PR.

```bash
uv run dendrobium-succ evaluate \
    --predictions-csv data/processed/predictions.csv \
    --test-csv data/wetlab/test.csv \
    --protein-fasta data/wetlab/protein.faa \
    --output-dir data/wetlab/results
```

**Masukan:**
- `predictions-csv`: keluaran dari Langkah 4
- `test-csv`: 314 situs suksinilasi wet-lab Feng et al. 2017 (disertakan)
- `protein-fasta`: 19 MB proteom RefSeq (disertakan) — digunakan untuk
  menemukan situs K dari protein yang sama untuk generasi negatif sintetik

**Keluaran (di `output-dir/`):**

| File | Isi |
|------|-----|
| `matches.csv` | Prediksi per situs vs *ground truth* |
| `metrics.json` | Metrik agregat (presisi, recall, F1, MCC, AUC-ROC, AUC-PR) |
| `pr_curve.png` | Plot kurva precision-recall |

**Apa yang dilakukan:**
1. Memetakan situs uji Feng et al. ke nomor aksesi RefSeq melalui
   pencocokan peptida
2. Menghasilkan negatif sintetik 1:1 dari protein yang sama (seed=42
   secara default)
3. Menggabungkan prediksi dengan positif + negatif
4. Menghitung TP/FP/TN/FN dan metrik agregat
5. Membuat plot kurva precision-recall

**Metrik yang diharapkan** (untuk *pipeline* demo, GCF_001605985.2):
- Recall: ~0.86 (260/301 situs wet-lab terdeteksi)
- F1: ~0.70 (dengan negatif 1:1)
- MCC: ~0.29

Untuk detail flag lengkap, lihat
[docs/id/referensi-cli.md](../referensi-cli.md#evaluate).

---

## Pipeline Lengkap (Semua Langkah Sekaligus)

**Dengan fetch (dari nomor aksesi NCBI):**
```bash
uv run dendrobium-succ run \
    --accession GCF_001605985.2 \
    --output-csv data/processed/predictions.csv \
    --skip-model-download    # jika Langkah 0 sudah dilakukan
```

**Dengan FASTA yang sudah ada (lewati fetch):**
```bash
uv run dendrobium-succ run \
    --input-fasta data/input/proteins.faa \
    --output-csv data/processed/predictions.csv \
    --skip-model-download
```

*File* antara masuk ke `data/processed/intermediate/` secara default.

---

## Demo dengan Dataset Mini yang Disertakan

Untuk memverifikasi *tool* bekerja tanpa data Anda sendiri, gunakan dataset
mini yang disertakan (1000 fragmen dari *D. catenatum*):

```bash
bash scripts/demo.sh
```

Ini menjalankan `extract` + `predict` menggunakan fitur ProtT5 yang sudah
dihitung sebelumnya (melewati tahap GPU Modal). Keluaran:
`data/processed/demo/predictions.csv`.

---

## Daftar Periksa Reproduksibilitas

- [ ] **Versi Python di-pin**: `requires-python = ">=3.11"` di `pyproject.toml`
- [ ] **Dependensi di-lock**: `uv.lock` dihasilkan oleh `uv sync`
- [ ] **Versi RLSuccSite**: catat *git commit* RLSuccSite yang digunakan
- [ ] ***Checkpoint* model**: nama *file* tetap dengan metrik dalam nama
      (misalnya `ACC7142`)
- [ ] **Model ProtT5**: `Rostlab/prot_t5_xl_uniref50` (HuggingFace, tidak
      dapat diubah)
- [ ] **Scaler**: `scaler_tpempps.pkl` (528-D), `scaler_ccp.pkl` (462-D)
- [ ] ***Seed* acak**: tidak relevan untuk inferensi (tanpa *sampling*,
      hanya argmax)
- [ ] **Riwayat Git**: *conventional commits* menelusuri setiap perubahan
- [ ] **Format keluaran**: CSV dengan 4 kolom, deterministik untuk masukan
      yang sama

---

## Pemecahan Masalah

### `modal run` gagal dengan kesalahan autentikasi
```bash
modal token new --name dendrobium-succ
```

### Unduhan model ProtT5 gagal
Unduhan HuggingFace (~2.8 GB) mungkin *timeout*. Jalankan ulang:
```bash
modal run modal/prott5_embed.py::download_model
```
Volume bersifat inkremental — unduhan parsial dilanjutkan.

### Predict.py gagal dengan `ModuleNotFoundError: No module named 'torchrl'`
Venv lokal kehilangan dependensi berat RLSuccSite (torch, torchrl,
tensordict, protlearn). Dua opsi:
```bash
# Opsi A: gunakan sibling venv RLSuccSite (jika Anda memilikinya)
# predict.py mendeteksi otomatis ../RLSuccSite/.venv

# Opsi B: instal dependensi ke venv lokal
uv pip install torch torchrl tensordict protlearn
```

### Predict.py gagal dengan `FileNotFoundError: scaler_*.pkl`
Scaler dikirim dalam `models/rlsuccsite/Models/`. Jika hilang, Predict.py
akan mencoba memasangnya dari data pelatihan (yang mungkin tidak ada).
Verifikasi model yang disertakan masih utuh:
```bash
ls models/rlsuccsite/Models/*.pkl
ls models/rlsuccsite/Models/*.pth
```

### Jumlah fragmen adalah nol
FASTA masukan Anda mungkin DNA, bukan protein. Ekstraktor melewati
urutan yang terlihat seperti DNA (hanya ATGCN, panjang > 100). Verifikasi
masukan Anda adalah FASTA protein (.faa).

### GPU kehabisan memori
Kurangi ukuran *batch*:
```bash
uv run dendrobium-succ embed --batch-size 16 ...
```
Atau tingkatkan ke L40S (48 GB) di `modal/prott5_embed.py`.

---

## Estimasi Biaya

| Langkah | Sumber Daya | Waktu (10k fragmen) | Biaya |
|---------|-------------|---------------------|-------|
| Fetch | HTTP (NCBI API) | ~10 detik | $0 |
| Extract | CPU (lokal) | ~5 detik | $0 |
| Embed | L40S GPU (Modal) | ~2 menit | ~$0.06 |
| Predict | CPU (lokal) | ~3 menit | $0 |
| Evaluate | CPU (lokal) | ~5 detik | $0 |
| **Total** | | | **~$0.06** |

Untuk 100k fragmen: ~$0.65. Untuk 1 juta fragmen: ~$6.50.

---

## Peta *File*

```
dendrobium_succ/
├── pyproject.toml                    # proyek uv (deps: biopython, modal, typer, rich, sklearn, matplotlib, numpy)
├── PLAN.md                           # file ini — resep reproduksi
├── README.md                         # halaman arahan + mulai cepat
├── docs/                             # dokumentasi detail
│   ├── architecture.md               # desain sistem + keputusan desain
│   └── cli-reference.md              # semua perintah CLI
├── src/dendrobium_succ/
│   ├── __init__.py
│   ├── cli.py                        # Typer CLI: 7 perintah
│   ├── logging_config.py             # logger rich + JSON
│   ├── fetch.py                      # Langkah 1: NCBI Datasets v2 API
│   ├── extract.py                    # Langkah 2: ekstraksi fragmen 33-mer
│   ├── embed.py                      # Langkah 3: wrapper klien Modal
│   ├── predict.py                    # Langkah 4: wrapper RLSuccSite Predict.py
│   ├── evaluate.py                   # Langkah 5: evaluasi wet-lab (F1, MCC, AUC)
│   └── pipeline.py                   # orkestrasi pipeline lengkap
├── modal/
│   └── prott5_embed.py               # aplikasi GPU Modal (embedding ProtT5-XL)
├── models/
│   └── rlsuccsite/                   # model RLSuccSite yang disertakan (Feature/, Models/)
├── data/
│   ├── input/                        # FASTA protein Anda (di-gitignore)
│   ├── processed/                    # fragmen, fitur, prediksi (di-gitignore)
│   └── wetlab/                       # situs uji Feng et al. 2017 + proteom referensi
│       ├── test.csv                  # 314 situs suksinilasi wet-lab
│       ├── test_fixture.csv          # fixture 3-baris untuk unit test
│       ├── protein.faa               # 19 MB proteom RefSeq (*ground truth*)
│       └── mini/                     # dataset mini 1000-fragmen untuk demo.sh
├── tests/
│   └── test_extract.py               # tes ekstraksi fragmen
└── scripts/
    └── demo.sh                       # demo end-to-end dengan dataset mini yang disertakan
```
