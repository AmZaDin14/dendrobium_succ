# Glosarium

> 🌐 **Bahasa:** [English](../../README.md) | **Bahasa Indonesia**

Daftar istilah teknis yang digunakan dalam dokumentasi `dendrobium_succ`,
disertai terjemahan Bahasa Indonesia. Glosarium ini berfungsi sebagai referensi
bagi pembaca yang belum familiar dengan istilah bioinformatika dan machine
learning.

---

## Biologi & Biokimia

| Istilah Inggris | Terjemahan | Catatan |
|-----------------|-----------|---------|
| protein | protein | Tidak diterjemahkan; istilah standar |
| amino acid | asam amino | Istilah fundamental |
| residue | residu | Istilah standar |
| peptide | peptida | Rantai pendek asam amino |
| lysine | lisin | Nama ilmiah asam amino K |
| K (amino acid code) | K | Kode satu huruf standar; tidak diterjemahkan |
| K-site | situs K | Posisi lisin yang menjadi target modifikasi |
| succinylation | suksinilasi | Modifikasi pasca-translasi pada residu lisin |
| succinyllysine | suksinillisin | Hasil dari suksinilasi |
| post-translational modification | modifikasi pasca-translasi | Modifikasi protein setelah translasi |
| substrate | substrat | Protein target enzim |
| physicochemical | fisiko-kimia | Sifat fisik dan kimia |
| wet-lab | wet-lab | Eksperimen laboratorium; "wet-lab" lebih umum daripada "laboratorium basah" |

---

## Machine Learning & Statistik

| Istilah Inggris | Terjemahan | Catatan |
|-----------------|-----------|---------|
| machine learning | machine learning | Tidak diterjemahkan |
| reinforcement learning | pembelajaran penguatan | Istilah RL |
| transformer | transformer | Arsitektur neural network; tidak diterjemahkan |
| T5 encoder | encoder T5 | Komponen T5 |
| embedding | embedding | Representasi vektor; tidak diterjemahkan |
| prediction | prediksi | Output model |
| inference | inferensi | Proses menjalankan model |
| ensemble | ansambel | Kombinasi beberapa model |
| hand-crafted features | fitur buatan tangan | Fitur yang dirancang secara manual |
| training | pelatihan | Proses melatih model |
| test set | set uji | Data untuk evaluasi |
| validation | validasi | Proses verifikasi |
| ground truth | ground truth | Label sebenarnya; tidak diterjemahkan |
| precision | presisi | Metrik evaluasi |
| recall | recall | Metrik evaluasi; tidak diterjemahkan |
| F1 score | skor F1 | Rata-rata harmonik presisi dan recall |
| MCC | MCC | Matthews Correlation Coefficient; singkatan tidak diterjemahkan |
| AUC-ROC | AUC-ROC | Area Under ROC Curve |
| AUC-PR | AUC-PR | Area Under Precision-Recall Curve |
| threshold | ambang batas | Nilai batas untuk klasifikasi |
| batch | batch | Grup data; tidak diterjemahkan |
| epoch | epoch | Satu putaran pelatihan; tidak diterjemahkan |
| tensor | tensor | Struktur data ML |
| activation | aktivasi | Output neuron |
| deterministic | deterministik | Hasil dapat direproduksi |
| stochastic | stokastik | Mengandung unsur acak |
| argmax | argmax | Fungsi matematika; tidak diterjemahkan |
| scaler | scaler | Alat normalisasi fitur; tidak diterjemahkan |
| checkpoint | checkpoint | File model tersimpan; tidak diterjemahkan |
| imbalanced | tidak seimbang | Distribusi kelas tidak merata |
| confounder | pengacau | Variabel yang mengacaukan hasil |

---

## Perangkat Lunak & Rekayasa

| Istilah Inggris | Terjemahan | Catatan |
|-----------------|-----------|---------|
| pipeline | pipeline | Rangkaian proses; tidak diterjemahkan |
| workflow | alur kerja | Urutan langkah |
| command | perintah | Instruksi CLI |
| flag | flag | Opsi perintah CLI |
| argument | argumen | Nilai yang diberikan ke perintah |
| option | opsi | Sinonim untuk flag |
| output | keluaran | Hasil proses |
| input | masukan | Data yang diproses |
| file | file | Dokumen; "file" lebih umum daripada "berkas" |
| directory | direktori | Folder |
| path | path | Lokasi file/direktori |
| repository | repositori | Penyimpanan kode |
| dependency | dependensi | Ketergantungan paket |
| virtual environment | lingkungan virtual | venv |
| package | paket | Modul Python |
| module | modul | File Python |
| function | fungsi | Blok kode |
| class | kelas | Struktur OOP |
| variable | variabel | Penyimpan nilai |
| string | string | Tipe data teks |
| framework | framework | Kerangka kerja |
| library | library | Pustaka kode; tidak diterjemahkan |

---

## Platform & Alat (Tidak Diterjemahkan)

Nama platform, alat, dan basis data berikut tetap dalam bahasa Inggris sesuai
konvensi industri:

| Nama | Keterangan |
|------|-----------|
| ProtT5-XL | Model protein language model dari Rostlab |
| Modal | Platform GPU cloud |
| RLSuccSite | Model prediksi suksinilasi |
| NCBI | National Center for Biotechnology Information |
| RefSeq | Basis data referensi NCBI |
| UniProt / UniRef50 | Basis data protein |
| HuggingFace | Platform model ML |
| PyTorch | Framework deep learning |
| transformers | Library HuggingFace |
| biopython | Library bioinformatika Python |
| scikit-learn | Library ML Python |
| Modal Volume | Penyimpanan persisten di Modal |
| Typer | Library CLI Python |
| uv | Package manager Python |

---

## Organisme & Spesies

| Istilah Inggris | Terjemahan | Catatan |
|-----------------|-----------|---------|
| organism | organisme | Makhluk hidup |
| species | spesies | Klasifikasi taksonomi |
| genus | genus | Klasifikasi taksonomi |
| *Dendrobium officinale* | *Dendrobium officinale* | Nama ilmiah; dimiringkan sesuai konvensi taksonomi |
| *Dendrobium catenatum* | *Dendrobium catenatum* | Sinonim dari *D. officinale* |
| orchid | anggrek | Famili Orchidaceae |
| NCBI assembly | rakitan NCBI | Rakitan genom dari NCBI |
| accession | nomor aksesi | Pengenal unik di NCBI |

---

## Format & Angka

- **Format angka**: Tetap menggunakan format Inggris (titik untuk desimal, koma untuk pemisah ribuan). Contoh: `0.86` bukan `0,86`. Alasan: dokumentasi menampilkan output kode yang menggunakan format Inggris.
- **Format tanggal**: ISO 8601 (YYYY-MM-DD) jika diperlukan.
- **Nama ilmiah**: Dimiringkan (*italic*) sesuai konvensi taksonomi.
- **Kode satu huruf asam amino**: Kapital, tidak dimiringkan (K, R, dll.).

---

## Catatan Penggunaan

1. **Konsistensi**: Gunakan istilah yang tercantum di glosarium ini secara konsisten di seluruh dokumentasi.
2. **Pertama kali muncul**: Untuk istilah yang baru diperkenalkan, berikan terjemahan Indonesia di samping istilah Inggris, contoh: "lisin (lysine)".
3. **Istilah yang tidak diterjemahkan**: Nama platform, library, dan basis data tetap dalam bahasa Inggris (lihat tabel "Platform & Alat").
4. **Kode dan perintah**: Kode program, nama file, path, dan perintah CLI tidak diterjemahkan.
