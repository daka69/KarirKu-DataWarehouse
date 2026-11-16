# ETL Data Warehouse KarirKu

Script `etl.py` membangun ulang data warehouse `dw_lowongan` dari CSV
hasil cleaning dengan Python (pandas + SQLAlchemy), mengikuti rancangan
dokumen UTS: PostgreSQL 16, skema galaxy (3 tabel fakta, 7 dimensi),
SCD Type 1, load awal full dan incremental harian.

Alur pipeline: **Extract** (CSV dimuat ke schema `staging`, tabel
`stg_*`, semua kolom text, tanpa constraint) → **Transform** (pengetikan
ulang, pembentukan dimensi, penautan kunci perusahaan / lokasi / profil /
tanggal) → **Load** (schema `dw_lowongan`, DDL identik dengan dump
`dw_lowongan_pg16.sql`).

## Prasyarat

- PostgreSQL 16 berjalan dan database tujuan sudah dibuat
  (`createdb dw_lowongan`).
- Python 3 dengan dependensi pada `requirements.txt`:

  ```
  pip install -r requirements.txt
  ```

- Folder CSV hasil cleaning (isi `bi-uts-data-clean`): postings_clean,
  companies_clean, dataset_clean, posting_skills_clean,
  posting_skills_nlp, skill_dictionary, quarantine.

## Koneksi

Koneksi dibaca dari environment variable `DATABASE_URL`, contoh:

```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/dw_lowongan
```

Tanpa variable itu, default-nya adalah URL di atas. Opsi `--database
NAMA` mengganti nama database pada URL, berguna untuk database uji.

## Cara menjalankan

Load penuh (TRUNCATE semua tabel `dw_lowongan`, lalu muat ulang):

```
python etl.py --mode full
```

Load incremental (hanya lowongan dengan `listed_date` sesudah cutoff
yang belum ada di `fact_posting`; anggota dimensi baru ditambahkan
seperlunya; aman dijalankan berulang tanpa duplikat):

```
python etl.py --mode incremental --cutoff 2024-04-21
```

Opsi lain:

- `--source-dir PATH` — folder CSV sumber (default
  `~/workspace/your_files/bi-uts-data-clean`).
- Pada mode full, `--cutoff YYYY-MM-DD` menahan lowongan dengan
  `listed_date` sesudah tanggal itu. Dipakai untuk simulasi load
  parsial yang kemudian dilengkapi run incremental dengan cutoff yang
  sama; hasil akhirnya terbukti identik dengan load full sekaligus.

## Perilaku penting

- **Quarantine.** Baris sumber yang rusak (job_id tidak dapat diurai,
  tanggal tidak valid, pasangan skill yatim) tidak menggagalkan load;
  baris itu dicatat ke `quarantine_output.csv` dan dihitung pada
  validasi akhir. File `quarantine.csv` dari tahap cleaning (478 baris
  gaji outlier/non-USD) bersifat informatif: nilai gajinya sudah
  di-NULL-kan saat cleaning, postingnya tetap dimuat.
- **Kunci perusahaan.** Lowongan ditautkan ke `dim_company` lewat
  company_id; fallback memakai `company_name_norm` (kemunculan
  pertama), termasuk lowongan tanpa nama perusahaan yang tertaut ke
  perusahaan tanpa nama di companies_clean; sisanya ke baris Unknown
  (`company_key` 1).
- **Benefit.** Tidak ada CSV hasil cleaning yang memuat benefit per
  lowongan, jadi `dim_benefit` dan `fact_posting_benefit` tidak dapat
  diturunkan dari sumber yang tersedia. Script membuat kedua tabel,
  membiarkannya kosong, dan melaporkannya secara eksplisit pada log dan
  laporan validasi (bukan disembunyikan). Bila suatu saat file opsional
  `job_benefits.csv` (kolom `job_id`, `benefit_type`, `is_inferred`)
  tersedia di folder sumber, kedua tabel otomatis ikut dimuat pada run
  berikutnya.
- **Validasi akhir.** Setiap run diakhiri pemeriksaan: jumlah baris
  per tabel, jumlah `salary_valid = 1`, persen benefit inferred, dan 11
  pemeriksaan orphan foreign key. Run gagal (exit code 2) bila ada
  orphan.

## Dokumentasi untuk laporan

Kesesuaian artefak ETL dengan template laporan UAS:

| Artefak | Dipakai pada |
|---|---|
| `etl.log` (log bertimestamp per langkah) dan `validation_report.md` (tabel target vs tercapai + rekonsiliasi) | Lampiran 5 — Log ETL + Validasi |
| `etl.py` | Bab III subbab 3.8 Dokumentasi Source Code, dan repository GitHub (folder `etl/`) |
| Tangkapan layar jalannya script di terminal (extract, load per tabel, validasi akhir) | Lampiran 4 — Dokumentasi Implementasi |

`validation_report.md` ditulis ulang pada setiap run, jadi jalankan
satu run final (mode full pada database presentasi) sebelum isinya
disalin ke Lampiran 5, supaya mode dan tanggal pada laporan sesuai
dengan run yang didokumentasikan.
