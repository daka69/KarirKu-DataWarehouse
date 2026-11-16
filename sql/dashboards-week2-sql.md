# UAS BI MTI — Dashboard Metabase Minggu 2: SQL siap pakai (DRAF, disiapkan 12 Nov 2026)

Minggu 2 mulai Jumat 13 Nov 2026. File ini head start untuk itu: 5 dashboard
sesuai scope UTS yang dikomit, masing-masing dengan query SQL yang tinggal
ditempel ke Metabase SQL editor (database `dw_lowongan`, schema `public`).

## Yang sudah dicek — dan yang belum

- Query ditulis MELAWAN DDL ASLI dump `dw_lowongan_pg16.sql` (11 tabel,
  schema `public`): nama tabel dan kolom diambil dari `CREATE TABLE` di dump,
  bukan dari dokumen/DBML. Perbedaan yang ketemu dan sudah diakomodasi:
  - `fact_posting` (bukan `fact_job_posting`); kolomnya `job_id`,
    `company_key`, `location_key`, `job_profile_key`, `listed_date_key`,
    `expiry_date_key`, `views_count`, `applies_count`,
    `salary_min_annual_usd`, `salary_max_annual_usd`, `salary_disclosed`,
    `salary_valid`, `days_listed`.
  - `dim_job_profile` TIDAK punya kolom judul pekerjaan — hanya
    `experience_level`, `work_type`, `remote_allowed`, `sponsored`,
    `application_type`. Jadi tidak ada breakdown per judul pekerjaan.
  - `dim_location` di dump hanya `city`, `state`, `country` — TIDAK ada
    `unemployment_rate` (LAUS) atau flag pay-transparency law. Breakdown
    itu butuh join CSV eksternal, belum ada di file ini.
  - Dump TIDAK punya `dim_occupation` dan TIDAK punya kolom
    `market_median_wage` / `salary_gap_pct`. Perbandingan gaji vs median
    pasar (OEWS) butuh join eksternal — lihat catatan di Dashboard 1.
  - `dim_skill` (35 baris) isinya KATEGORI FUNGSI LinkedIn (Marketing, PR,
    Sales, ...) — BUKAN skill. Dashboard skill memakai
    `fact_posting_skill_nlp` + `dim_skill_nlp` (77 skill asli).
    Selisih dokumen-vs-dump soal "77 skill" tetap seperti dicatat di
    `uas-week1-starter.md` §2: jangan klaim 77 untuk fact kamus kata kunci.
- SEMUA query di file ini lolos parse PostgreSQL (dicek dengan `pglast`,
  12 Nov 2026), dan SUDAH DIEKSEKUSI 15 Nov 2026 di PostgreSQL 16.15
  (database uji cermin persis laptop, schema dw_lowongan): 20/20 blok
  jalan tanpa error, dan angka jangkarnya terverifikasi — cakupan gaji
  valid 29.315 = 23,7%; benefit inferred 59,1%; lowongan yang menyebut
  skill 73,9%. Di laptop, jalankan blok "Smoke test" sekali di Metabase
  sebagai konfirmasi koneksi, lalu query lain tinggal dipakai.
- Aturan angka yang dipakai di semua query: gaji HANYA dari
  `salary_valid = 1` (23,7% coverage, tulis footnote-nya di dashboard);
  `views_count` itu proxy — pakai AVG, jangan SUM; jendela listing hanya
  4 minggu (24 Mar–20 Apr 2024), jadi TIDAK ada klaim tren waktu.
- `company_key = 1` adalah placeholder "Unknown" — dikeluarkan dari
  ranking perusahaan (Dashboard 4).
- `company_size` ordinal 1–7 (kecil → besar), tanpa batas jumlah karyawan
  yang pasti — tampilkan apa adanya, jangan dikarang labelnya.

## Smoke test — jalankan dulu di Metabase SQL editor

```sql
SELECT 'fact_posting' AS tabel, COUNT(*) AS baris FROM fact_posting
UNION ALL SELECT 'fact_posting_skill', COUNT(*) FROM fact_posting_skill
UNION ALL SELECT 'fact_posting_skill_nlp', COUNT(*) FROM fact_posting_skill_nlp
UNION ALL SELECT 'fact_posting_benefit', COUNT(*) FROM fact_posting_benefit
UNION ALL SELECT 'dim_company', COUNT(*) FROM dim_company
UNION ALL SELECT 'dim_location', COUNT(*) FROM dim_location;
```

Harus keluar: fact_posting 123.849; fact_posting_skill 205.778;
fact_posting_skill_nlp 249.896; fact_posting_benefit 65.393;
dim_company 24.474; dim_location 8.524. Kalau cocok, koneksi benar.

---

## Dashboard 1 — Perbandingan Gaji Pasar

Footnote wajib di dashboard: "Hanya 23,7% lowongan yang gajinya valid
(salary_valid = 1; 29.315 dari 123.849). Angka di sini hanya dari lowongan
bergaji valid. Data listing 24 Mar–20 Apr 2024, bukan tren waktu."
Catatan: perbandingan vs median pasar (OEWS) TIDAK BISA dari dump saja —
butuh join `external/` BLS OEWS per SOC + state, dan dump tidak punya kolom
SOC. Itu pekerjaan tambahan di luar file ini; jangan klaim sudah ada.

### 1.1 KPI — cakupan gaji

```sql
SELECT COUNT(*) AS total_postings,
       SUM(CASE WHEN salary_valid = 1 THEN 1 ELSE 0 END) AS valid_salary_postings,
       ROUND(100.0 * SUM(CASE WHEN salary_valid = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS valid_salary_pct
FROM fact_posting;
```

### 1.2 Median gaji per jenis pekerjaan (work_type)

```sql
SELECT jp.work_type,
       COUNT(*) AS postings_bergaji_valid,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.salary_min_annual_usd))::bigint AS median_min_usd,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.salary_max_annual_usd))::bigint AS median_max_usd
FROM fact_posting f
JOIN dim_job_profile jp ON jp.job_profile_key = f.job_profile_key
WHERE f.salary_valid = 1
GROUP BY jp.work_type
ORDER BY postings_bergaji_valid DESC;
```

### 1.3 Median gaji per level pengalaman

```sql
SELECT jp.experience_level,
       COUNT(*) AS postings_bergaji_valid,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.salary_min_annual_usd))::bigint AS median_min_usd,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.salary_max_annual_usd))::bigint AS median_max_usd
FROM fact_posting f
JOIN dim_job_profile jp ON jp.job_profile_key = f.job_profile_key
WHERE f.salary_valid = 1
GROUP BY jp.experience_level
ORDER BY median_min_usd DESC;
```

### 1.4 Median gaji per state — 10 state dengan lowongan bergaji terbanyak

```sql
SELECT l.state,
       COUNT(*) AS postings_bergaji_valid,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.salary_min_annual_usd))::bigint AS median_min_usd,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.salary_max_annual_usd))::bigint AS median_max_usd
FROM fact_posting f
JOIN dim_location l ON l.location_key = f.location_key
WHERE f.salary_valid = 1 AND l.state <> 'Unknown'
GROUP BY l.state
ORDER BY postings_bergaji_valid DESC
LIMIT 10;
```

---

## Dashboard 2 — Skill Demand

Sumber: `fact_posting_skill_nlp` (249.896 pasangan) + `dim_skill_nlp`
(77 skill). BUKAN `fact_posting_skill`/`dim_skill` — yang 35 itu kategori
fungsi LinkedIn. Penyebut persentase = seluruh 123.849 lowongan.

### 2.1 Top 20 skill yang paling banyak diminta

```sql
SELECT s.skill_name,
       COUNT(*) AS postings,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM fact_posting), 2) AS pct_of_all_postings
FROM fact_posting_skill_nlp fs
JOIN dim_skill_nlp s ON s.skill_key = fs.skill_key
GROUP BY s.skill_name
ORDER BY postings DESC
LIMIT 20;
```

### 2.2 Top 10 skill di lowongan Full-time

```sql
SELECT s.skill_name,
       COUNT(*) AS postings
FROM fact_posting_skill_nlp fs
JOIN dim_skill_nlp s ON s.skill_key = fs.skill_key
JOIN fact_posting f ON f.job_id = fs.job_id
JOIN dim_job_profile jp ON jp.job_profile_key = f.job_profile_key
WHERE jp.work_type = 'Full-time'
GROUP BY s.skill_name
ORDER BY postings DESC
LIMIT 10;
```

### 2.3 KPI — berapa lowongan yang menyebut skill, dan rata-rata skill per lowongan

```sql
SELECT COUNT(DISTINCT job_id) AS postings_with_skill,
       ROUND(100.0 * COUNT(DISTINCT job_id) / (SELECT COUNT(*) FROM fact_posting), 1) AS pct_postings_with_skill,
       ROUND(1.0 * COUNT(*) / COUNT(DISTINCT job_id), 2) AS avg_skills_per_posting
FROM fact_posting_skill_nlp;
```

---

## Dashboard 3 — Hiring Patterns (jangka pendek)

Jendela listing 24 Mar–20 Apr 2024 (4 minggu). Semua angka di sini adalah
potret 4 minggu itu — jangan dibaca sebagai tren.

### 3.1 Lowongan per minggu listing

```sql
SELECT DATE_TRUNC('week', d.full_date) AS week_start,
       COUNT(*) AS postings
FROM fact_posting f
JOIN dim_date d ON d.date_key = f.listed_date_key
GROUP BY week_start
ORDER BY week_start;
```

### 3.2 Lowongan per work_type x experience_level

```sql
SELECT jp.work_type,
       jp.experience_level,
       COUNT(*) AS postings
FROM fact_posting f
JOIN dim_job_profile jp ON jp.job_profile_key = f.job_profile_key
GROUP BY jp.work_type, jp.experience_level
ORDER BY postings DESC;
```

### 3.3 Pangsa remote per work_type

```sql
SELECT jp.work_type,
       COUNT(*) AS postings,
       SUM(CASE WHEN jp.remote_allowed = 'Yes' THEN 1 ELSE 0 END) AS remote_postings,
       ROUND(100.0 * SUM(CASE WHEN jp.remote_allowed = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 1) AS remote_pct
FROM fact_posting f
JOIN dim_job_profile jp ON jp.job_profile_key = f.job_profile_key
GROUP BY jp.work_type
ORDER BY postings DESC;
```

### 3.4 Rata-rata days_listed, applies, dan views per work_type

```sql
SELECT jp.work_type,
       COUNT(*) AS postings,
       ROUND(AVG(f.days_listed), 1) AS avg_days_listed,
       ROUND(AVG(f.applies_count), 1) AS avg_applies,
       ROUND(AVG(f.views_count), 1) AS avg_views
FROM fact_posting f
JOIN dim_job_profile jp ON jp.job_profile_key = f.job_profile_key
GROUP BY jp.work_type
ORDER BY postings DESC;
```

---

## Dashboard 4 — Company Attractiveness

`company_key = 1` ("Unknown") dikeluarkan dari ranking. Views adalah proxy
— pakai rata-rata, bukan total. Pool top-10 mengikuti aturan UTS: minimal
5 lowongan untuk ranking rata-rata applies.

### 4.1 Top 10 perusahaan per jumlah lowongan

```sql
SELECT c.name AS company,
       COUNT(*) AS postings
FROM fact_posting f
JOIN dim_company c ON c.company_key = f.company_key
WHERE c.company_key <> 1
GROUP BY c.name
ORDER BY postings DESC
LIMIT 10;
```

### 4.2 Top 10 perusahaan per rata-rata applies (min. 5 lowongan)

```sql
SELECT c.name AS company,
       COUNT(*) AS postings,
       ROUND(AVG(f.applies_count), 1) AS avg_applies,
       ROUND(AVG(f.views_count), 1) AS avg_views
FROM fact_posting f
JOIN dim_company c ON c.company_key = f.company_key
WHERE c.company_key <> 1
GROUP BY c.name
HAVING COUNT(*) >= 5
ORDER BY avg_applies DESC
LIMIT 10;
```

### 4.3 Rata-rata views dan applies per ukuran perusahaan (ordinal 1–7)

```sql
SELECT c.company_size,
       COUNT(*) AS postings,
       ROUND(AVG(f.views_count), 1) AS avg_views,
       ROUND(AVG(f.applies_count), 1) AS avg_applies
FROM fact_posting f
JOIN dim_company c ON c.company_key = f.company_key
WHERE c.company_size IS NOT NULL
GROUP BY c.company_size
ORDER BY c.company_size;
```

### 4.4 Lowongan per ukuran perusahaan

```sql
SELECT c.company_size,
       COUNT(*) AS postings,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM fact_posting), 1) AS pct_of_all_postings
FROM fact_posting f
JOIN dim_company c ON c.company_key = f.company_key
WHERE c.company_size IS NOT NULL
GROUP BY c.company_size
ORDER BY c.company_size;
```

---

## Dashboard 5 — Benefits

Total baris `fact_posting_benefit` 65.393, 12 tipe benefit. 59,1% baris
adalah inferred (`is_inferred = 1`) — tulis itu di dashboard, jangan
sembunyikan.

### 5.1 Mix benefit — jumlah lowongan per tipe

```sql
SELECT b.benefit_type,
       COUNT(*) AS offers,
       COUNT(DISTINCT fb.job_id) AS postings,
       ROUND(100.0 * COUNT(DISTINCT fb.job_id) / (SELECT COUNT(*) FROM fact_posting), 2) AS pct_of_all_postings
FROM fact_posting_benefit fb
JOIN dim_benefit b ON b.benefit_key = fb.benefit_key
GROUP BY b.benefit_type
ORDER BY offers DESC;
```

### 5.2 Explicit vs inferred

```sql
SELECT CASE WHEN is_inferred = 1 THEN 'Inferred' ELSE 'Explicit' END AS origin,
       COUNT(*) AS offers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_offers
FROM fact_posting_benefit
GROUP BY is_inferred
ORDER BY offers DESC;
```

### 5.3 KPI — lowongan yang menawarkan minimal 1 benefit

```sql
SELECT COUNT(DISTINCT job_id) AS postings_with_benefit,
       ROUND(100.0 * COUNT(DISTINCT job_id) / (SELECT COUNT(*) FROM fact_posting), 1) AS pct_postings_with_benefit,
       ROUND(1.0 * COUNT(*) / COUNT(DISTINCT job_id), 2) AS avg_benefits_per_posting
FROM fact_posting_benefit;
```

### 5.4 Top 5 benefit di lowongan Full-time

```sql
SELECT b.benefit_type,
       COUNT(*) AS offers
FROM fact_posting_benefit fb
JOIN dim_benefit b ON b.benefit_key = fb.benefit_key
JOIN fact_posting f ON f.job_id = fb.job_id
JOIN dim_job_profile jp ON jp.job_profile_key = f.job_profile_key
WHERE jp.work_type = 'Full-time'
GROUP BY b.benefit_type
ORDER BY offers DESC
LIMIT 5;
```

---

## Yang belum ada di file ini (jangan diklaim sudah beres)

- Perbandingan gaji vs median pasar OEWS: butuh join eksternal per SOC +
  state; dump tidak punya SOC/median. Kerjakan terpisah atau nyatakan
  sebagai pengembangan lanjutan — sesuai aturan UTS, jangan klaim tren
  atau perbandingan yang datanya tidak ada di dump.
- Breakdown LAUS (talent tightness per state) dan pay-transparency law:
  butuh join CSV `external/`; kolomnya tidak ada di dump.
- Visual Metabase-nya sendiri (tipe chart, filter, drill-down): pilih
  setelah query jalan dan angkanya cocok — 5 menit per query di SQL
  editor, bukan di file ini.
