# Pipeline Translasi-ke-Prediksi Frame 3

> **Apa yang terjadi ketika sekuens rDNA dipaksa melalui pipeline prediksi
> suksinilasi.** Eksperimen berbasis rasa ingin tahu yang mendokumentasikan
> setiap langkah dari DNA mentah hingga prediksi situs lisin, dengan
> 5W+1H lengkap di setiap tahap.

**Intinya:** Sekuens ITS rDNA dari *Dendrobium crumenatum*
ditranslasi secara in silico (Frame 3), diverifikasi dengan BLASTN,
lalu dimasukkan ke pipeline prediksi suksinilasi RLSuccSite. Model
menghasilkan prediksi — tetapi secara biologis tidak bermakna karena
rDNA tidak pernah ditranslasi menjadi protein dalam sel hidup.

---

## Langkah 1 — Translasi DNA

| Elemen | |
|---------|------------|
| **What** (Apa) | Menerjemahkan sekuens nukleotida mentah menjadi asam amino di seluruh 6 kerangka baca (*reading frames*) |
| **Who** (Siapa) | BioPython `Seq.translate()` dengan tabel kode genetik standar |
| **When** (Kapan) | Setelah pengambilan sekuens, sebelum analisis fungsional |
| **Where** (Di mana) | Eksekusi lokal (`uv run python`) |
| **Why** (Mengapa) | Untuk menemukan kerangka baca terbuka (*open reading frames*/ORF) dan translasi kontinu terpanjang (Frame 3) |
| **How** (Bagaimana) | Dua sekuens (D7, 847 nt; D11, 1052 nt) dari `sekuensing_dendrobium.md` dibaca sebagai objek `Bio.Seq.Seq`. Masing-masing ditranslasi dalam 6 frame (3 maju, 3 komplemen-balik) menggunakan `translate(table='Standard', to_stop=False)`. Kodon stop muncul sebagai `*`. Kodon parsial di ujung sekuens memicu `BiopythonWarning` tetapi selesai normal. |

**Mengapa bukan ExPASy?** ExPASy Translate memiliki API CGI, tetapi
BioPython lebih cepat, *offline*, dapat diskrip, dan menghasilkan
keluaran identik untuk translasi standar.

---

## Langkah 2 — Identifikasi Frame 3

| Elemen | |
|---------|------------|
| **What** (Apa) | Memilih Frame 3 (`5'3' Frame +3`) sebagai ORF kontinu terpanjang |
| **Who** (Siapa) | Inspeksi manual dari keluaran translasi 6 frame |
| **When** (Kapan) | Setelah seluruh 6 frame dihasilkan |
| **Where** (Di mana) | Tinjauan keluaran terminal |
| **Why** (Mengapa) | Frame 3 tidak memiliki kodon stop internal di seluruh panjang sekuens, membentuk peptida kontinu 281 aa (D7) / 350 aa (D11). Lima frame lainnya dipenuhi kodon stop (`*`), mengonfirmasi Frame 3 sebagai satu-satunya kerangka baca yang layak. |
| **How** (Bagaimana) | Untuk setiap sekuens, 6 blok mirip-FASTA dicetak. Frame 3 adalah satu-satunya frame dengan >80% panjang sekuens sebagai kodon tanpa gangguan. Ini cocok dengan pola standar ITS rDNA: *spacer* non-kode (ITS1, ITS2) + gen 5.8S rRNA, yang secara kebetulan membentuk ORF panjang saat ditranslasi dalam satu frame tertentu. |

**Catatan biologis:** Ini adalah artefak *in silico*. ITS rDNA
ditranskripsi menjadi RNA, tidak pernah ditranslasi menjadi protein.
ORF panjang ada karena pengulangan rDNA telah berevolusi dengan
komposisi nukleotida bias yang menekan kodon stop di kerangka baca ini.

---

## Langkah 3 — Verifikasi BLASTN

| Elemen | |
|---------|------------|
| **What** (Apa) | Mengonfirmasi identitas sekuens nukleotida terhadap basis data nukleotida NCBI non-redundan |
| **Who** (Siapa) | API web NCBI BLASTN (via `curl`) |
| **When** (Kapan) | Setelah translasi, untuk menentukan apakah sekuens tersebut jamur (seperti dugaan awal) atau tanaman inang (Dendrobium) |
| **Where** (Di mana) | `https://blast.ncbi.nlm.nih.gov/Blast.cgi` — pengiriman REST API, hasil diambil sebagai teks biasa |
| **Why** (Mengapa) | Translasi Frame 3 ExPASy menunjukkan motif 5.8S rRNA dan awalnya disalahartikan sebagai ITS rDNA *jamur*. BLASTN menyelesaikan asal spesies secara definitif. |
| **How** (Bagaimana) | Sekuens DNA mentah dikirim POST ke API BLAST NCBI dengan `PROGRAM=blastn`, `DATABASE=nt`. API mengembalikan ID Permintaan (RID). Klien melakukan polling `CMD=Get&RID=<RID>&FORMAT_TYPE=Text` hingga `Status=READY`. Hit teratas diurai dari keluaran teks. |

**Hasil:** Semua 10 hit teratas adalah ITS rDNA *Dendrobium crumenatum*
(99–100% identitas). Tidak ada kecocokan jamur. Motif 5.8S rRNA
terkonservasi di semua eukariota — tidak spesifik jamur.

| Peringkat | Aksesi | Spesies | Identitas | E-value |
|------|-----------|---------|----------|---------|
| 1 | AB593537.1 | *D. crumenatum* | 100% | 0.0 |
| 2 | PX057331.1 | *D. crumenatum* | 100% | 0.0 |
| 3 | AF521608.1 | *D. crumenatum* | 100% | 0.0 |
| 4-10 | Various | *D. crumenatum* + *D. formosum* | 98–99% | 0.0 |

---

## Langkah 4 — Ekstraksi Fragmen 33-mer

| Elemen | |
|---------|------------|
| **What** (Apa) | Mengekstrak jendela 33-asam amino yang berpusat pada setiap residu lisin (K) |
| **Who** (Siapa) | Perintah CLI `dendrobium-succ extract` |
| **When** (Kapan) | Setelah sekuens AA Frame 3 disimpan sebagai FASTA |
| **Where** (Di mana) | CPU lokal (`src/dendrobium_succ/extract.py`) |
| **Why** (Mengapa) | RLSuccSite membutuhkan fragmen 33-mer sebagai masukan model — situs suksinilasi (K) harus berada di posisi tengah 16 setiap fragmen |
| **How** (Bagaimana) | Sekuens AA Frame 3 ditulis ke `data/input/frame3_translations.faa`. Perintah `extract` memindai setiap protein, dan untuk setiap K, mengekstrak 16 residu di hulu + K + 16 residu di hilir. Ujung sekuens diisi dengan `X`. Keluaran: `data/processed/frame3_fragments.fasta`. |

**Keluaran:** 27 fragmen (13 dari D7, 14 dari D11).

---

## Langkah 5 — Embedding ProtT5-XL

| Elemen | |
|---------|------------|
| **What** (Apa) | Menghitung *embedding* 1024-dimensi dari model bahasa protein untuk setiap fragmen |
| **Who** (Siapa) | Perintah CLI `dendrobium-succ embed` → kontainer Modal GPU dengan ProtT5-XL |
| **When** (Kapan) | Setelah ekstraksi fragmen |
| **Where** (Di mana) | Cloud Modal (GPU L40S, 48 GB VRAM) |
| **Why** (Mengapa) | ProtT5-XL (3B parameter) menangkap konteks biofisika dan evolusi di sekitar setiap K. Fitur berbasis ProtT5 adalah salah satu bagian dari ensemble RLSuccSite. |
| **How** (Bagaimana) | FASTA fragmen dikirim ke Modal. Kontainer memuat `Rostlab/prot_t5_xl_uniref50` dari Volume yang di-cache, melakukan tokenisasi setiap 33-mer, menjalankan encoder T5, dan mengekstrak *embedding* residu pusat (indeks 16). Mengembalikan tensor PyTorch berbentuk `[27, 1024]`. |

**Biaya:** ~$0.01 (GPU L40S, ~2 menit waktu kontainer).

**Keluaran:** `data/processed/frame3_features.pt`

---

## Langkah 6 — Sanitasi Fragmen

| Elemen | |
|---------|------------|
| **What** (Apa) | Mengganti karakter kodon stop (`*`) dengan placeholder asam amino tak dikenal (`X`) |
| **Who** (Siapa) | Penggantian string Python sederhana |
| **When** (Kapan) | Setelah ekstraksi, sebelum prediksi |
| **Where** (Di mana) | Skrip lokal |
| **Why** (Mengapa) | *Encoder* fitur TPEMPPS RLSuccSite (`Feature/TPEMPPS.py`) memetakan asam amino ke bilangan bulat melalui alfabet 21 huruf (`ACDEFGHIKLMNPQRSTVWXY`). Karakter `*` tidak ada dalam alfabet ini dan menyebabkan `KeyError` saat dijalankan. `X` sudah ditangani (dipetakan ke indeks 20). |
| **How** (Bagaimana) | 10 dari 27 fragmen mengandung `*` dari kodon stop dalam translasi Frame 3. Operasi `str.replace('*', 'X')` menghasilkan `data/processed/frame3_fragments_clean.fasta`. |

**Konteks sumber TPEMPPS** (`TPEMPPS.py:20-24`):
```python
amino_acids = 'ACDEFGHIKLMNPQRSTVWXY'
# U, Z, O, B, - disubstitusi ke X; * TIDAK ditangani
protein_sequence = re.sub(r"[UZOB-]", "X", protein_sequence)
```

---

## Langkah 7 — Prediksi Ensemble RLSuccSite

| Elemen | |
|---------|------------|
| **What** (Apa) | Menjalankan ensemble RLSuccSite terlatih (model ProtT5 + model TPEMPPS_CCP) untuk memprediksi probabilitas suksinilasi per situs K |
| **Who** (Siapa) | Perintah CLI `dendrobium-succ predict` → `models/rlsuccsite/Models/Predict.py` |
| **When** (Kapan) | Setelah fragmen yang disanitasi + *embedding* ProtT5 siap |
| **Where** (Di mana) | CPU lokal (*multiprocessing* 6 pekerja) |
| **Why** (Mengapa) | Ensemble menggabungkan dua jenis fitur ortogonal: *deep learning* (ProtT5) dan fitur fisikokimia buatan tangan (TPEMPPS_CCP). Suara tertimbang 50/50 antara dua model PPO menghasilkan skor akhir. |
| **How** (Bagaimana) | `Predict.py` memuat file `.pt` ProtT5, menghitung fitur TPEMPPS secara langsung dari sekuens fragmen, memasukkan keduanya ke dua pengklasifikasi *reinforcement learning* PPO terlatih, dan merata-rata logit mereka. Keluaran adalah CSV dengan kolom: `SequenceID, Sequence, PositiveProbability, PredictedLabel`. |

**Hasil:**
- 27 situs K diproses
- 10 diprediksi positif (Prob ≥ 0.5)
- 17 diprediksi negatif
- Prediksi tertinggi: pos_278 (D7, 0.89), pos_86 (D11, 0.90)

---

## Kualifikasi Biologis

**Prediksi ini tidak bermakna secara biologis.** Translasi Frame 3
tidak sesuai dengan protein nyata:

| Masalah | Detail |
|---------|--------|
| rDNA tidak pernah ditranslasi | ITS1, 5.8S, ITS2 ditranskripsi menjadi RNA, tidak diterjemahkan |
| Kodon stop ditutupi | `*` → `X` menyembunyikan terminasi translasi |
| Bantalan X di ujung C | Fragmen di dekat ujung sekuens AA diisi dengan `X`, suatu artefak |
| Tidak ada konteks seluler | Suksinilasi adalah modifikasi pasca-translasi — membutuhkan protein nyata dalam sel hidup |
| Model hanya melihat pola | RLSuccSite memberi skor pola asam amino di sekitar K, terlepas dari asal biologis |

Eksperimen menunjukkan bahwa pipeline berjalan ujung-ke-ujung dengan
masukan AA apa pun, tetapi **prediksi hanya valid pada sekuens protein
nyata** yang benar-benar diekspresikan dan disuksinilasi secara in vivo.
