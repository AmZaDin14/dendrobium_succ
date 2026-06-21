# Arsitektur

> 🌐 **Bahasa:** [English](../architecture.md) | **Bahasa Indonesia**

Dokumen ini menjelaskan bagaimana `dendrobium_succ` disusun dan *mengapa*
setiap bagian ada. Untuk resep reproduksi langkah demi langkah, lihat
[PLAN.md](../../PLAN.md). Untuk detail perintah CLI, lihat
[referensi-cli.md](referensi-cli.md).

---

## Gambaran Sistem

```
                 ┌─────────────────┐
                 │  NCBI Assembly   │  (nomor aksesi atau nama organisme)
                 └────────┬────────┘
                          │
              fetch       │   HTTP, NCBI Datasets v2 API
                          ▼
                 ┌─────────────────┐
                 │  Protein FASTA   │  (.faa)
                 └────────┬────────┘
                          │
              extract     │   CPU, lokal
                          ▼
                 ┌─────────────────┐
                 │ Fragments FASTA  │  (>id|pos_N, seq 33-karakter)
                 └────────┬────────┘
                          │
              embed       │   GPU, Modal
                          ▼
                 ┌─────────────────┐
                 │  features.pt     │  ({'ids': [...], 'features': [N,1024]})
                 └────────┬────────┘
                          │
              predict     │   CPU, lokal (subprocess ke RLSuccSite)
                          ▼
                 ┌─────────────────┐
                 │ predictions.csv  │  (SequenceID, Sequence, Prob, Label)
                 └────────┬────────┘
                          │
              evaluate    │   CPU, lokal
                          ▼
                 ┌─────────────────┐
                 │ matches.csv      │
                 │ metrics.json     │  (F1, MCC, AUC-ROC, AUC-PR)
                 │ pr_curve.png     │
                 └─────────────────┘
```

---

## Komponen

Setiap dari 9 modul sumber memiliki satu peran yang terdefinisi dengan baik.
Nama modul mengikuti nama perintah CLI jika applicable.

### `fetch.py` — Klien NCBI Datasets v2 API
Mengunduh FASTA protein dari NCBI berdasarkan nomor aksesi rakitan (misalnya
`GCF_001605985.2`) atau nama organisme. Dua endpoint:
- `GET /genome/taxon/{name}/dataset_report` — cari berdasarkan organisme
- `GET /genome/accession/{acc}/download` — unduh ZIP, ekstrak `protein.faa`

### `extract.py` — Ekstraktor fragmen 33-mer
Untuk setiap residu lisin (K) di setiap protein, menulis fragmen 33-karakter
yang berpusat pada K. Fragmen yang dekat dengan terminal diberi padding
dengan 'X'. Format keluaran:
```
>XP_123456.1|pos_19
RSDNLAFAARRCFRNSKIQTFSSRSFISTAADP
```

### `embed.py` — Klien GPU Modal
Wrapper subprocess yang memanggil `modal run modal/prott5_embed.py::embed`.
Mengirim FASTA fragmen ke kontainer GPU, menerima file `.pt` dengan
`{'ids': list[str], 'features': Tensor[N, 1024]}`.

### `modal/prott5_embed.py` — Aplikasi GPU Modal
Memuat ProtT5-XL (3 miliar parameter, ~2.8 GB) dari Modal Volume yang
disimpan, melakukan tokenisasi pada setiap 33-mer, menjalankan T5 encoder,
dan mengekstrak embedding center-residue (indeks 16) — vektor 1024-D per
fragmen.

### `predict.py` — Wrapper ansambel RLSuccSite
Wrapper subprocess di sekitar `models/rlsuccsite/Models/Predict.py`.
Menghitung fitur buatan tangan (TPEMPPS 528-D + CCP 462-D = 990-D) secara
*on-the-fly* dari FASTA fragmen, memuat kedua model PPO terlatih, dan
menghasilkan prediksi ansambel 50/50.

### `evaluate.py` — Evaluasi wet-lab
Modul self-contained yang menilai prediksi terhadap set uji wet-lab Feng et
al. 2017. Menghasilkan negatif sintetik 1:1 dari protein yang sama,
menggabungkan prediksi dengan *ground truth*, dan menghitung
presisi/recall/F1/MCC/AUC-ROC/AUC-PR. Menghasilkan `matches.csv`,
`metrics.json`, `pr_curve.png`.

### `pipeline.py` — Orkestrasi pipeline lengkap
Merangkai `fetch` → `extract` → `embed` → `predict` menjadi satu perintah.
Mengimplementasikan perintah CLI `dendrobium-succ run`.

### `cli.py` — Typer CLI
7 perintah: `fetch`, `extract`, `download-model`, `embed`, `predict`, `run`,
`evaluate`. Konvensi: nama modul = nama perintah.

### `logging_config.py` — Logging rich + JSON
Logging terstruktur: output konsol rich untuk manusia, *file* JSON di
`data/processed/run.log` untuk parsing oleh mesin. Namespace logger:
`"dendrobium_succ"`.

---

## Aliran Data

1. **Masukan**: FASTA protein (diunduh dari NCBI atau disediakan pengguna)
2. **Extract**: Satu fragmen per residu K (33 karakter, berpusat)
3. **Embed**: Satu vektor 1024-D per fragmen (center-residue ProtT5-XL)
4. **Predict**: Satu probabilitas per fragmen (ansambel ProtT5 + TPEMPPS_CCP)
5. **Keluaran**: CSV dengan 4 kolom: `SequenceID`, `Sequence`,
   `PositiveProbability`, `PredictedLabel`
6. **Evaluate** (opsional): Menilai terhadap *ground truth* wet-lab,
   menghasilkan `matches.csv`, `metrics.json`, `pr_curve.png`

*Pipeline* ini **deterministik** untuk masukan yang tetap (tanpa *sampling*,
klasifikasi argmax, *seed* acak yang tetap untuk generasi negatif).

---

## Keputusan Desain

Bagian ini menjelaskan "mengapa" di balik setiap pilihan desain utama.
Keputusan dikelompokkan berdasarkan kategori. Untuk diskusi trade-off yang
lebih lengkap, lihat git log — *conventional commits* menelusuri setiap
perubahan.

### Arsitektur (8)

**1. Mengapa Modal hanya untuk tahap GPU?**
ProtT5-XL adalah transformer 3 miliar parameter (~2.8 GB). Pada CPU,
*embedding* 1000 fragmen memakan waktu ~30 menit; pada GPU L40S, ~30 detik.
Tahap lainnya (HTTP fetch, ekstraksi fragmen, komputasi fitur, evaluasi)
adalah operasi CPU yang ringan. Menjalankan semuanya pada GPU akan
membuang uang; menjalankannya secara lokal membuat *pipeline* portabel.
Modal memberikan GPU sesuai permintaan tanpa mengelola infrastruktur.

**2. Mengapa ansambel ProtT5 + TPEMPPS_CCP?**
Inilah yang digunakan RLSuccSite, dan merupakan inti dari model *upstream*.
ProtT5 menangkap konteks evolusioner (language model yang dilatih pada
UniRef50); TPEMPPS_CCP menangkap fitur fisiko-kimia buatan tangan
(528-D + 462-D). Ansambel 50/50 adalah konfigurasi terbaik secara empiris
dalam paper RLSuccSite.

**3. Mengapa fragmen 33-mer berpusat pada K (indeks 16)?**
Inilah format yang diharapkan oleh model-model RLSuccSite. Residu pusat
(K yang menjadi perhatian) berada pada indeks 16 (0-based) dari jendela
33-karakter — 16 residu konteks di setiap sisi. Jendela yang lebih pendek
kehilangan konteks; jendela yang lebih panjang mengencerkan sinyal.

**4. Mengapa panjang tetap dengan padding 'X' di terminal?**
Model ML membutuhkan dimensi masukan yang tetap. 'X' adalah *placeholder*
standar untuk "asam amino tidak diketahui/tidak standar" dalam ML protein.
Padding di terminal (bukan trimming) mempertahankan K pada posisi sebenarnya.
K selalu berada di indeks 16 terlepas dari di mana dalam protein ia berada.

**5. Mengapa subprocess untuk `predict.py` (bukan import Python)?**
`Models/Predict.py` RLSuccSite memiliki pohon dependensi sendiri: `torch`,
`torchrl`, `tensordict`, `protlearn`. Meng-importnya akan membengkakkan
dependensi `pyproject.toml` alat. Isolasi subprocess menjaga alat tetap
ringan (hanya `biopython`, `modal`, `typer`, `rich`, `sklearn`,
`matplotlib`, `numpy`) dan dependensi ML yang berat menjadi opsional.

**6. Mengapa lebih memilih *sibling venv* daripada *local venv*?**
Venv RLSuccSite (`../RLSuccSite/.venv`, jika ada) memiliki dependensi ML
yang berat terinstal; *local venv* biasanya tidak. Alat mendeteksi otomatis:
jika *sibling venv* ada, gunakan; jika tidak, fallback ke *local venv*.
Jalur fallback mengharuskan pengguna menjalankan `uv pip install torch
torchrl tensordict protlearn` secara manual.

**7. Mengapa `batch_size=512` untuk embed tetapi `2048` untuk predict?**
*Bottleneck* yang berbeda. Embedding terikat GPU (VRAM membatasi *batch* —
ProtT5-XL menggunakan ~6 GB, menyisakan ~42 GB untuk aktivasi pada L40S
48 GB). Predict terikat CPU (ekstraksi fitur buatan tangan, *streaming*).
*Batch* yang lebih besar di predict mengamortisasi startup subprocess;
*batch* yang lebih kecil di embed muat dalam VRAM.

**8. Mengapa GPU L40S secara khusus?**
| GPU | VRAM | $/jam | Mengapa bukan |
|-----|------|-------|---------------|
| T4 | 16 GB | $0.59 | VRAM tidak cukup untuk ProtT5-XL + aktivasi |
| L4 | 24 GB | $0.80 | Opsi hemat; mungkin OOM pada *batch* besar |
| A10 | 24 GB | $1.10 | Lebih mahal dari L4, VRAM sama |
| L40S | 48 GB | $1.95 | ✅ Default — muat ProtT5-XL dengan sisa, throughput cepat |

L40S adalah tier memori tinggi Modal dan $/performa terbaik untuk beban
kami. VRAM ekstra (vs L4) memungkinkan kami menangani *batch* hingga ~1
juta fragmen per run.

### Reproduksibilitas (5)

**9. Mengapa model self-contained (`models/rlsuccsite/`)?**
Proyek ini dulu memerlukan repositori *sibling* `../RLSuccSite`. Itu
fragile: klon akan rusak jika *sibling* hilang atau memiliki *commit* yang
salah. Kami menyalin bobot model, scaler, dan `Predict.py` ke
`models/rlsuccsite/` sehingga alat bekerja secara mandiri. *Sibling venv*
masih digunakan (melalui deteksi otomatis) untuk dependensi ML yang sudah
terinstal sebelumnya, tetapi model itu sendiri disertakan dengan repositori.

**10. Mengapa rakitan NCBI `GCF_001605985.2`?**
Ini adalah rakitan RefSeq *Dendrobium catenatum* (= *D. officinale*) yang
digunakan dalam paper RLSuccSite. Ini adalah organisme referensi untuk
*pipeline* demo. Pencarian NCBI berdasarkan organisme mungkin mengembalikan
beberapa rakitan Dendrobium; memberikan `--accession` memastikan rakitan
yang spesifik.

**11. Mengapa negatif sintetik 1:1 dari protein yang sama?**
Prediksi suksinilasi tidak seimbang: sebagian besar situs K tidak
disuksinilasi. Tanpa negatif, Anda tidak dapat menghitung presisi/F1/MCC.
Kebijakan RLSuccSite-NegCtrl menggunakan situs K 1:1 dari protein yang
sama (satu negatif per positif, diambil dari situs K lain pada protein
yang sama) — ini mengontrol *confounder* tingkat protein sekaligus
menghindari negatif "protein berbeda" yang sepele. Kami mengimplementasikan
ulang ini di `evaluate.py` untuk menghindari ketergantungan pada paket
negctrl *sibling*.

**12. Mengapa seed=42?**
Default reproduksibilitas standar. Satu-satunya langkah stokastik adalah
*sampling* negatif acak. Mengatur `seed=42` membuat evaluasi deterministik.

**13. Mengapa `data/wetlab/protein.faa` (19 MB) disertakan?**
Sebagian besar data di-gitignore, tetapi proteom referensi ini adalah
*ground truth* untuk evaluasi — tidak berubah antar run, dan mengirimnya
menghilangkan langkah pengaturan manual. Pada 19 MB cukup kecil untuk
disertakan (jauh di bawah batas 100 MB GitHub). *Gitignore* secara eksplisit
melacaknya melalui negasi.

### Proses (3)

**14. Mengapa mengganti nama ke `dendrobium_succ`?**
Nama asli `d_officinale_succ` sebenarnya sudah benar (mengacu pada
*Dendrobium officinale*), tetapi tidak cocok dengan model *upstream*
(`rlsuccsite`) dan singkatan tersebut membingungkan. Nama baru:
- Memperjelas genus anggrek (*Dendrobium*) dari genus wortel (*Daucus*,
  yang membingungkan docstring kode lama)
- Mempertahankan fokus spesies (organisme demo)
- Tidak berbenturan dengan nama paket `rlsuccsite` *upstream*

**15. Mengapa memperbaiki bug genus Daucus→Dendrobium?**
Docstring `fetch.py` dan `cli.py` lama mengklaim "Daucus catenatum BUKAN
nama taksonomi NCBI yang valid" — ini salah. Nama yang valid adalah
*Dendrobium catenatum* (anggrek); *Daucus catenatum* (wortel) tidak ada.
Bug ini menyebabkan kebingungan tentang organisme demo. Sekarang sudah
diperbaiki.

**16. Mengapa menghapus `scripts/compare_results.py`?**
File ini memiliki *path* *sibling* `../RLSuccSite/results.csv` yang
di-hardcode dan tidak ada lagi (kami self-contained). Menggunakan
`pandas` (tidak ada di `pyproject.toml`). Modul `evaluate.py` adalah
pengganti yang tepat. Kode mati dihapus dalam *commit* *rename*.

### Organisasi Kode (4)

**17. Mengapa *layout* `src/`?**
*Layout* `src/` (vs datar) mencegah impor paket yang tidak disengaja dari
akar repositori. Ini memaksa tes melalui paket yang terinstal, menangkap
file `__init__.py` yang hilang dan *bug* *path* impor lebih awal. Ini
adalah konvensi yang direkomendasikan oleh [panduan *packaging* PyPA](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/).

**18. Mengapa paket datar (tanpa subpaket seperti `src/dendrobium_succ/pipeline/`)?**
Dengan 9 *file* sumber, subpaket adalah *nesting* yang prematur. Datar
lebih mudah dinavigasi dan menjaga *path* impor tetap pendek
(`from .fetch import fetch_fasta` vs
`from .pipeline.fetch import fetch_fasta`). Jika kami menambahkan lebih
banyak modul nanti, kami dapat membagi kemudian.

**19. Mengapa Typer untuk CLI?**
Typer dibangun di atas Click, memiliki *parsing* argumen berbasis *type
hint*, menghasilkan `--help` secara otomatis, dan dirender dengan baik bersama
rich. Ini lebih sedikit *boilerplate* daripada argparse, lebih modern
daripada Click. CLI 7-perintah cocok dengan *sweet spot* Typer.

**20. Mengapa uv?**
Cepat (berbasis Rust, 10-100x lebih cepat dari pip), menangani manajemen
versi Python, memiliki *lockfile* (`uv.lock`) untuk reproduksibilitas, dan
merupakan *binary* tunggal. Menggantikan pip + venv + pip-tools + pyenv.
[Astral](https://astral.sh/) (pembuatnya) juga membuat `ruff`, yang belum
kami gunakan tetapi bisa saja.

### Infrastruktur (4)

**21. Mengapa nama Modal Volume `prott5-model` / `prott5-output`?**
Nama generik (bukan `dendrobium-succ-model`) berarti *volume* dapat
digunakan kembali di seluruh proyek. Jika kami mengubah namanya, ~2.8 GB
bobot ProtT5 yang disimpan akan menjadi *orphan* di sisi Modal. Mempertahankan
nama generik adalah pilihan yang disengaja untuk menjaga infrastruktur
stateless terhadap nama proyek.

**22. Mengapa Python ≥3.11?**
Untuk sintaks union `Path | None` (PEP 604) dan `tomllib` (PEP 680).
Python 3.11 adalah minimum yang memiliki keduanya. 3.10 memiliki sintaks
union tetapi tidak `tomllib`; 3.9 tidak memiliki keduanya. Kami
*pin* ke 3.11 untuk fitur modern ini.

**23. Mengapa `num_workers=6`?**
Cocok dengan *default* *upstream* RLSuccSite untuk ekstraksi fitur buatan
tangan (lihat `models/rlsuccsite/Models/Predict.py`). Tidak di-*tune*
oleh kami — diwarisi dari penulis model. Didokumentasikan di sini agar
*maintainer* di masa depan tahu bahwa ini tidak sembarang.

**24. Mengapa belum ada *remote* git?**
Repositori bersifat lokal saja. Ketika di-*push*, nama *remote* yang
direkomendasikan cocok dengan proyek: `dendrobium-succ`. Repositori siap
untuk di-*push* tetapi belum ada *remote* yang dikonfigurasi.

---

## Apa yang Tidak Dicakup Dokumen Ini

- **Resep reproduksi langkah demi langkah** — lihat [PLAN.md](../../PLAN.md)
- **Referensi flag CLI** — lihat [referensi-cli.md](referensi-cli.md)
- **Pemecahan masalah** — lihat PLAN.md §Pemecahan Masalah
- **Referensi API untuk setiap modul** — lihat *docstring* di `src/dendrobium_succ/`
- **Glosarium istilah domain** — lihat [GLOSARIUM.md](GLOSARIUM.md)
