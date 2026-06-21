# dendrobium_succ

> 🌐 **Bahasa:** [English](../../README.md) | **Bahasa Indonesia**

Alat prediksi situs suksinilasi (succinylation site) yang dapat direproduksi
untuk *Dendrobium officinale* (anggrek) menggunakan
[RLSuccSite](https://github.com/Zhangqingchao-Ch/RLSuccSite) — sebuah
prediktor situs suksinillisin berbasis *reinforcement learning*. Alat ini
membungkus proses inferensi RLSuccSite menjadi *pipeline* yang bersih dan
end-to-end yang dapat dijalankan pada *file* FASTA protein apa pun.

## Apa yang Dilakukan Alat Ini

Diberikan sebuah *file* FASTA protein, alat ini memprediksi residu lisin (K)
mana yang kemungkinan disuksinilasi menggunakan ansambel terlatih RLSuccSite
(ProtT5 + TPEMPPS_CCP), lalu secara opsional menilai prediksi terhadap
*ground truth* dari eksperimen *wet-lab*.

```
Rakitan NCBI → fetch FASTA → ekstrak fragmen 33-mer → ProtT5-XL (GPU) → prediksi ansambel → evaluasi
```

## Mulai Cepat

```bash
# 1. Instalasi
uv sync

# 2. Autentikasi dengan Modal (sekali saja)
uv tool install modal && modal setup

# 3. Sekali saja: simpan ProtT5-XL di Modal Volume (~2.8 GB)
uv run dendrobium-succ download-model

# 4. Jalankan pipeline lengkap
uv run dendrobium-succ run \
    --accession GCF_001605985.2 \
    --output-csv data/processed/predictions.csv \
    --skip-model-download
```

## Cara Kerja

*Pipeline* ini memiliki empat tahap, masing-masing adalah perintah CLI terpisah
(atau jalankan semuanya dengan `dendrobium-succ run`):

| Tahap | Apa yang dilakukan | Tempat dijalankan |
|-------|-------------------|-------------------|
| `fetch` | Mengunduh FASTA protein dari NCBI Datasets v2 API | Lokal (HTTP) |
| `extract` | Mengekstrak fragmen 33-mer yang berpusat pada setiap residu K | Lokal (CPU) |
| `embed` | Menghitung embedding center-residue ProtT5-XL (1024-D) | Modal (GPU) |
| `predict` | Ansambel RLSuccSite (model ProtT5 + TPEMPPS_CCP) | Lokal (CPU) |
| `evaluate` | Menilai prediksi terhadap *ground truth* wet-lab (F1, MCC, AUC) | Lokal (CPU) |

ProtT5-XL adalah transformer dengan 3 miliar parameter (~2.8 GB) — terlalu
besar untuk dijalankan pada CPU dalam skala besar, sehingga hanya tahap
embedding yang menggunakan GPU. Semua tahap lainnya berjalan secara lokal.
Lihat [arsitektur](architecture.md) untuk rationale desain lengkap.

## Evaluasi

Setelah menghasilkan prediksi, nilai prediksi tersebut terhadap set uji
*wet-lab* (Feng et al. 2017, 314 situs suksinilasi pada *D. officinale*):

```bash
uv run dendrobium-succ evaluate \
    --predictions-csv data/processed/predictions.csv \
    --test-csv data/wetlab/test.csv \
    --protein-fasta data/wetlab/protein.faa \
    --output-dir data/wetlab/results
```

Menghasilkan `matches.csv` (prediksi per situs vs *ground truth*), `metrics.json`
(metrik agregat: presisi, recall, F1, MCC, AUC-ROC, AUC-PR), dan `pr_curve.png`
(kurva precision-recall). Evaluasi juga menghasilkan negatif sintetik 1:1 dari
protein yang sama, untuk perhitungan presisi/F1/MCC yang adil.

## Perintah CLI

| Perintah | Deskripsi |
|----------|-----------|
| `fetch` | Mengunduh FASTA protein dari NCBI Datasets API (berdasarkan nomor aksesi atau organisme) |
| `extract` | Mengekstrak fragmen 33-mer di sekitar setiap K (CPU, lokal) |
| `download-model` | Sekali saja: menyimpan ProtT5-XL di Modal Volume |
| `embed` | Meng-embed fragmen dengan ProtT5-XL pada GPU Modal |
| `predict` | Menjalankan prediksi ansambel RLSuccSite (CPU, lokal) |
| `run` | Pipeline lengkap: fetch → extract → embed → predict |
| `evaluate` | Menilai prediksi terhadap *ground truth* wet-lab (F1, MCC, AUC) |

Lihat [referensi CLI](cli-reference.md) untuk detail lengkap setiap flag.

## Prasyarat

- **uv** — [instal](https://docs.astral.sh/uv/getting-started/installation/)
- **modal** — `uv tool install modal && modal setup`
- **Lingkungan Python dengan `torch`, `torchrl`, `tensordict`, `protlearn`** untuk tahap prediksi. Alat ini mendeteksi otomatis `../RLSuccSite/.venv` jika ada, jika tidak maka menggunakan `.venv` lokal. Lihat [arsitektur](architecture.md#keputusan-desain) untuk rationale-nya.

Bobot model sudah disertakan dalam `models/rlsuccsite/`. Tidak memerlukan
repositori RLSuccSite terpisah.

## Demo

```bash
bash scripts/demo.sh    # menggunakan dataset mini yang disertakan (1000 fragmen, 4MB)
```

Menjalankan `extract` + `predict` pada fitur ProtT5 yang sudah dihitung
sebelumnya. Memverifikasi *pipeline* end-to-end tanpa data sendiri atau
tahap GPU.

## Format Keluaran

```csv
SequenceID,Sequence,PositiveProbability,PredictedLabel
>XP_020671682.1|pos_19,RSDNLAFAARRCFRNSKIQTFSSRSFISTAADP,0.8723,1
>XP_020671682.1|pos_49,ADPTAGERNDDDAQSSKPLADDLFRSPPRSGGY,0.1234,0
```

## Dokumentasi

- [**PLAN.md**](../../PLAN.md) — resep reproduksi langkah demi langkah
- [**docs/id/arsitektur.md**](arsitektur.md) — desain sistem + keputusan desain
- [**docs/id/referensi-cli.md**](referensi-cli.md) — referensi lengkap perintah CLI
- [**docs/id/GLOSARIUM.md**](GLOSARIUM.md) — glosarium istilah teknis

## Struktur Proyek

```
dendrobium_succ/
├── pyproject.toml                # proyek uv
├── README.md                     # file ini (English)
├── docs/id/                      # dokumentasi Bahasa Indonesia
├── PLAN.md                       # resep reproduksi
├── docs/
│   ├── architecture.md           # desain sistem + keputusan desain (English)
│   └── cli-reference.md          # referensi CLI (English)
├── src/dendrobium_succ/          # paket Python
│   ├── cli.py                    # Typer CLI (7 perintah)
│   ├── fetch.py                  # NCBI Datasets v2 API
│   ├── extract.py                # ekstraksi fragmen 33-mer
│   ├── embed.py                  # wrapper klien Modal
│   ├── predict.py                # wrapper RLSuccSite Predict.py
│   ├── evaluate.py               # evaluasi wet-lab
│   ├── pipeline.py               # orkestrasi pipeline lengkap
│   └── logging_config.py         # logging rich + JSON
├── modal/prott5_embed.py         # aplikasi GPU Modal
├── models/rlsuccsite/            # model RLSuccSite yang disertakan
├── data/
│   ├── input/                    # FASTA protein Anda (di-gitignore)
│   ├── processed/                # keluaran pipeline (di-gitignore)
│   └── wetlab/                   # test.csv, protein.faa, dataset mini
├── tests/                        # tes pytest
└── scripts/demo.sh               # demo end-to-end
```
