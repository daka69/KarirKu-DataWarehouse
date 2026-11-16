# KarirKu MTI Data Warehouse

Implementasi data warehouse dan dashboard Business Intelligence untuk
analisis pasar lowongan kerja pada KarirKu (studi kasus fiktif), dibangun
mengikuti desain dokumen UTS Kecerdasan Bisnis. Bidang Manajemen
Teknologi Informasi (MTI), UAS Kecerdasan Bisnis 2026.

- Nama: Badjradaka Herdinansyah Rahardjo
- NIM: 2410817210029
- Metode MTI: System Usability Scale (SUS)

## Isi sistem

- Data warehouse PostgreSQL 16, skema galaxy (fact constellation):
  3 tabel fakta, 7 dimensi, SCD Type 1, schema `staging` dan `dw_lowongan`.
- Dataset: LinkedIn Job Postings (2023-2024) dari Kaggle oleh arshkon,
  123.849 lowongan (listing 24 Mar s.d. 20 Apr 2024).
- 5 sumber data eksternal: hukum transparansi gaji per state (DOL/NCSL),
  BLS OEWS Mei 2023, BLS NCS Maret 2024, BLS LAUS Mar-Apr 2024,
  AIOE (Felten et al.).
- 5 dashboard Metabase, satu per masalah bisnis: Perbandingan Gaji Pasar,
  Permintaan Skill, Pola Perekrutan, Daya Tarik Perusahaan, Benefit.
- Evaluasi usability dashboard dengan SUS (minimal 20 responden bebas),
  didahului evaluasi heuristik Nielsen sebagai pemeriksaan awal.

## Cara menjalankan

Prasyarat: Docker Desktop.

1. Salin `.env.example` menjadi `.env` dan isi password PostgreSQL.
2. Jalankan stack:

   docker compose up -d

3. Restore dump warehouse ke container:

   psql -U postgres -d dw_lowongan -f dw_lowongan_pg16.sql
   psql -U postgres -d dw_lowongan -f move-to-dw-schema.sql

   (11 pesan `role "root" does not exist` saat restore bersifat non-fatal.)
4. Muat 8 tabel eksternal dari folder `external/`:

   psql -U postgres -d dw_lowongan -f load-external-tables.sql

   Smoke test di akhir script harus menunjukkan 84 / 102 / 51 / 200 /
   35.309 / 12 / 12 / 123.849.
5. Buka Metabase di http://localhost:3000, tambahkan database `dw_lowongan`
   (host `db`, schema `dw_lowongan`), lalu buat dashboard dari query di
   folder `sql/`.

## Struktur folder

- `data/` — dataset mentah dan hasil cleaning beserta laporan cleaning.
- `external/` — CSV sumber eksternal dan script pemuatannya.
- `sql/` — dump warehouse, script schema, query dashboard, query validasi.
- `docs/` — dokumen desain dan instrumen evaluasi (kuesioner SUS).
- `docker-compose.yml` — PostgreSQL 16 + Metabase.
