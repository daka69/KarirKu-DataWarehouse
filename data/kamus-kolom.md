# Kamus Kolom — Dataset Lowongan Kerja Bersih

Dokumen ini menjelaskan fungsi setiap kolom pada `dataset_clean.csv` / `dataset_clean.xlsx`
(123.849 baris, hasil cleaning dataset LinkedIn Job Postings 2023–2024).

## Nilai khusus yang dipakai

| Nilai | Arti | Dipakai di |
|---|---|---|
| `NULL` | Data tidak tercatat / tidak diketahui (bukan nol) | Kolom angka: views, applies, gaji, company_size |
| `Unknown` | Kategori tidak diketahui | company_name, location_city, location_state |
| `Not specified` | Tidak disebutkan di lowongan | experience_level, remote_allowed, skills, skills_nlp |

Tidak ada sel yang dikosongkan dan tidak ada nilai yang dikarang.

## Daftar kolom

| Kolom | Tipe | Fungsi |
|---|---|---|
| `job_id` | Angka | ID unik tiap lowongan dari LinkedIn. Kunci utama baris. |
| `title` | Teks | Judul posisi yang dibuka, mis. "Marketing Coordinator". |
| `company_name` | Teks | Nama perusahaan pemasang lowongan. `Unknown` bila tidak tercantum (1,4%). |
| `company_size` | Kode 0–7 | Skala jumlah karyawan perusahaan: 0 = terkecil, 7 = terbesar. `NULL` bila tidak diketahui. Diambil dari tabel perusahaan. |
| `listed_date` | Tanggal | Tanggal lowongan dipublikasikan. |
| `expiry_date` | Tanggal | Tanggal lowongan kedaluwarsa. |
| `days_listed` | Angka (hari) | Lama lowongan tayang, dihitung dari `expiry_date − listed_date`. Terisi 100%. |
| `location_city` | Teks | Kota lokasi pekerjaan, hasil parsing kolom lokasi asli. |
| `location_state` | Teks | Kode negara bagian (mis. CA, NY, TX). `Unknown` bila tidak terparse (10,8%). |
| `views` | Angka | Jumlah kali lowongan dilihat. `NULL` bila tidak tercatat (1,4% kosong). Metrik utama daya tarik lowongan. |
| `applies` | Angka | Jumlah lamaran yang masuk. `NULL` bila tidak tercatat (81,2% kosong), sehingga tidak dipakai sebagai metrik utama. |
| `salary_min_annual_usd` | Angka (USD/tahun) | Batas bawah gaji, sudah dinormalisasi ke dolar AS per tahun (per jam ×2080, per bulan ×12, dst.; hanya USD, non-USD di-NULL-kan). `NULL` bila tidak dicantumkan atau tidak valid (76,3% kosong). |
| `salary_max_annual_usd` | Angka (USD/tahun) | Batas atas gaji, normalisasi sama seperti di atas. |
| `salary_disclosed` | 1 / 0 | Flag: 1 = lowongan mencantumkan gaji (24,1%), 0 = tidak. Bahan analisis transparansi gaji. |
| `salary_valid` | 1 / 0 / NULL | Flag: 1 = disclosed dan lolos validasi (23,7%); 0 = disclosed tetapi outlier (<$10K atau >$1M/tahun) atau non-USD; NULL = gaji tidak dicantumkan. Hanya bermakna bila `salary_disclosed` = 1. |
| `experience_level` | Teks | Jenjang pengalaman yang diminta: Entry level, Mid-Senior level, Associate, Director, Internship, Executive. `Not specified` bila tidak disebut (23,7%). |
| `work_type` | Teks | Jenis pekerjaan: Full-time, Part-time, Contract, Temporary, Internship, Volunteer. |
| `remote_allowed` | Teks | `Yes` bila lowongan secara eksplisit membolehkan kerja remote (12,3%), `Not specified` bila tidak disebut. |
| `application_type` | Teks | Mekanisme lamaran: SimpleOnsiteApply, ComplexOnsiteApply, OffsiteApply, UnknownApply. |
| `skills` | Teks | Kategori skill versi LinkedIn (35 kategori kasar, mis. Information Technology, Sales). Beberapa kategori dipisah tanda `|`. |
| `skills_nlp` | Teks | Skill spesifik hasil ekstraksi berbasis kamus kata kunci dari teks deskripsi memakai kamus 77 skill (mis. Python, SQL, Excel, AWS). Beberapa skill dipisah tanda `|`. `Not specified` bila tidak ada yang terdeteksi (26,1%). |

## Catatan

- Kolom `skills` berasal dari taksonomi LinkedIn yang kategorinya kasar; kolom `skills_nlp`
  adalah hasil ekstraksi mandiri yang lebih granular dan menjadi dasar analisis skill demand.
- 464 baris outlier gaji (<$10K atau >$1M/tahun) dan 14 baris non-USD: nilai gajinya di-NULL-kan (`salary_valid=0`) tetapi postingnya tetap dimuat; tercatat di `quarantine.csv` beserta alasannya.
- Daftar 77 skill kamus NLP terdokumentasi di `skill_dictionary.csv`.
