# UAS BI MTI — Join data eksternal untuk dashboard Minggu 2 (DRAF, disiapkan 12 Nov 2026)

Pendamping `dashboards-week2-sql.md`. File itu menandai tiga breakdown
sebagai "butuh join CSV eksternal, belum kubuatkan": gaji vs median pasar
(OEWS), talent tightness (LAUS), dan pay-transparency law. File ini yang
membuatkannya: langkah load + query join-nya.

## Koreksi satu kesan di file SQL: CSV-nya sudah ada sejak 13 Okt

File-file eksternal itu BUKAN barang baru — semuanya sudah tersimpan di
`workspace/your_files/bi-uts-data-clean/external/` sejak 13 Okt 2026.
Yang belum ada hanyalah cara memakainya di PostgreSQL/Metabase. Isinya:

| File | Isi | Baris |
|---|---|---|
| `laus_state_2024M03-M04.csv` | BLS LAUS: unemployment rate per state, Mar–Apr 2024 (jendela listing yang sama) | 102 data + header |
| `state_pay_transparency_law.csv` | Flag pay-transparency law per state + tanggal efektif + syarat | 51 + header |
| `map_state_clean.csv` | Normalisasi `dim_location.state` yang berantakan → kode state 2 huruf | 84 |
| `map_title_soc.csv` | Judul lowongan → kode SOC (untuk join OEWS) | 200 judul |
| `map_benefit_ncs.csv` | Tipe benefit KarirKu → kategori BLS NCS | 12 |
| `ncs_benefit_access_march2024.csv` | BLS NCS: % pekerja dengan akses benefit, Mar 2024 | 12 |
| `oews_may2023_state.zip` | BLS OEWS Mei 2023 per state (file Excel mentah) | 37.677 baris |
| `ext_oews_median_may2023.csv` | **BARU, dibuat 12 Nov 2026**: hasil ekstrak OEWS — hanya kolom `(state, soc_code, soc_title, a_median_usd)`, hanya okupasi detailed, baris yang mediannya disupresi BLS (`#`/`*`) dibuang | 35.309 |

## Cakupan join — dihitung dari data asli, 12 Nov 2026

Angka-angka ini hasil hitung langsung atas `fact_posting.csv`,
`dim_location.csv`, `dataset_clean.csv`, dan file-file di atas. Bukan klaim.

| Join | Yang bisa di-join | Yang tidak bisa | Artinya buat dashboard |
|---|---|---|---|
| State (normalisasi) | 105.924 lowongan (85,5%) punya kode state valid setelah `map_state_clean` | 17.925 (14,5%): `Unknown`, `United States`, negara lain (Netherlands, The Gambia), provinsi Kanada (ON, QC) | Semua panel per-state memakai 85,5% ini; sisanya dikeluarkan dan disebut di footnote |
| LAUS | Semua 51 state+DC ada di file, Mar dan Apr 2024 | — | Talent-tightness per state bisa penuh untuk 85,5% lowongan |
| Pay-transparency law | 5 state punya UU: CA, CO, HI, NY, WA — semuanya sudah efektif sebelum/saat jendela listing (paling akhir HI, 1 Jan 2024) | 46 state lain belum ada UU sejenis saat itu | 23.034 lowongan (18,6%) berada di state ber-UU |
| Judul → SOC | 200 judul terpetakan = 15.878 lowongan (12,8%) | 87,2% lowongan judulnya di luar 200 judul itu | Panel OEWS hanya berlaku untuk irisan kecil ini — jangan digeneralisasi ke semua lowongan |
| OEWS median | 13.537 lowongan (10,9%) punya judul terpetakan + state valid + median OEWS tersedia | Median disupresi BLS di 1.125 baris detailed (dibuang saat ekstrak) | — |
| OEWS + gaji valid | **3.161 lowongan (2,6% dari semua lowongan)** | — | Inilah penyebut panel premium/diskon gaji. Kecil tapi nyata; laporkan per judul (n=74–101), JANGAN per judul × state (selnya cuma n≈15) |
| NCS benefit | 8 dari 12 tipe benefit KarirKu punya padanan NCS | Child care support, Commuter benefits, Student loan assistance, Tuition assistance tidak ada di NCS | Panel benchmark benefit hanya untuk 8 tipe itu; NCS tidak punya angka civilian untuk dental, vision, paid family leave (kosong di file) |

## Temuan awal — sudah dihitung, tinggal divisualkan

Ini bukan klaim dari dokumen, ini hasil hitung dari file-file di atas
(12 Nov 2026). Cocok dipakai sebagai angka jangkar di dashboard:

1. **Pay-transparency law — sinyal kepatuhannya kuat.** Lowongan di 5
   state ber-UU mencantumkan gaji valid pada 43,0% lowongan (9.914 dari
   23.034), vs 17,1% (14.187 dari 82.888) di state tanpa UU. Selisih
   26 poin. Dari sisi perusahaan (KarirKu), ini indikasi risiko
   kepatuhan: perusahaan yang pasang lowongan di state tanpa UU jauh
   lebih jarang transparan soal gaji. Query Q1 di bawah mereproduksi
   angka ini.
2. **LAUS Mar–Apr 2024 (jangkar):** CA 5,2%/5,2%; NV 5,3%/5,4%;
   TX 4,0%/4,1%; NY 4,1%/4,2%; FL 3,2%/3,3%; paling ketat SD 1,7%/1,8%,
   VT 2,1%/2,1%, ND 2,3%/2,3%; DC 5,1%/5,2%. CA adalah state dengan
   lowongan terbanyak (11.484) SEKALIGUS pengangguran tertinggi kedua.
3. **OEWS — premium/diskon gaji per judul (median dari selisih
   midpoint gaji posting vs median OEWS Mei 2023, hanya gaji valid):**
   Senior Accountant +7,6% (n=101), Staff Accountant −21,2% (n=87),
   Project Manager +12,7% (n=86), Controller −13,1% (n=82),
   Administrative Assistant +2,8% (n=80), Executive Assistant +8,4%
   (n=74). Baca sebagai "gaji yang dipasang vs upah median pasar" —
   BUKAN "gaji yang dibayarkan vs pasar".
4. **NCS — benefit yang ditawarkan vs akses nasional (arahnya saja,
   bukan apel-ke-apel):** Medical insurance disebut di 7,7% lowongan vs
   akses civilian 75%; 401(k) 18,7% vs retirement 75%; Dental 5,4% (NCS
   civilian kosong di file); Vision 7,3% (NCS civilian kosong).
   Ingat: penyebut KarirKu adalah lowongan yang MENYEBUT benefit
   (59,1% barisnya inferred), penyebut NCS adalah pekerja yang PUNYA
   akses. Jangan tulis "hanya 7,7% pekerja dapat asuransi kesehatan".

## Langkah 1 — Load tabel eksternal ke PostgreSQL

Jalankan SETELAH restore dump (database `dw_lowongan`). Path di bawah
relatif terhadap folder `external/` — sesuaikan dengan lokasi folder itu
di laptop. Semua tabel dibuat di schema `public` seperti dump.

```sql
CREATE TABLE ext_state_clean (
    state_raw   TEXT PRIMARY KEY,
    state_clean TEXT
);
CREATE TABLE ext_laus (
    state_fips             TEXT,
    state_abbr             TEXT,
    state_name             TEXT,
    year                   INT,
    month                  INT,
    unemployment_rate_pct  NUMERIC,
    labor_force_thousands  NUMERIC,
    PRIMARY KEY (state_abbr, year, month)
);
CREATE TABLE ext_paylaw (
    state          TEXT PRIMARY KEY,
    has_law        INT,
    effective_date DATE,
    requirement    TEXT
);
CREATE TABLE ext_title_soc (
    title          TEXT PRIMARY KEY,
    postings_count INT,
    soc_code       TEXT,
    soc_title      TEXT,
    confidence     TEXT,
    notes          TEXT
);
CREATE TABLE ext_oews_median (
    state         TEXT,
    soc_code      TEXT,
    soc_title     TEXT,
    a_median_usd  INT,
    PRIMARY KEY (state, soc_code)
);
CREATE TABLE ext_ncs (
    benefit             TEXT PRIMARY KEY,
    civilian_access_pct NUMERIC,
    private_access_pct  NUMERIC,
    gov_access_pct      NUMERIC,
    reference_period    TEXT,
    release             TEXT,
    source_table        TEXT,
    source_url          TEXT,
    notes               TEXT
);
CREATE TABLE ext_benefit_map (
    internal_benefit_type TEXT PRIMARY KEY,
    ncs_benefit           TEXT,
    notes                 TEXT
);
-- Judul per lowongan: dump TIDAK punya kolom judul, jadi ambil dari
-- dataset_clean.csv (job_id sama dengan fact_posting.job_id).
CREATE TABLE ext_posting_title (
    job_id BIGINT PRIMARY KEY,
    title  TEXT
);
```

```sql
\copy ext_state_clean FROM 'map_state_clean.csv' WITH (FORMAT csv, HEADER true)
\copy ext_laus FROM 'laus_state_2024M03-M04.csv' WITH (FORMAT csv, HEADER true)
\copy ext_paylaw FROM 'state_pay_transparency_law.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy ext_title_soc FROM 'map_title_soc.csv' WITH (FORMAT csv, HEADER true)
\copy ext_oews_median FROM 'ext_oews_median_may2023.csv' WITH (FORMAT csv, HEADER true)
\copy ext_ncs FROM 'ncs_benefit_access_march2024.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy ext_benefit_map FROM 'map_benefit_ncs.csv' WITH (FORMAT csv, HEADER true)
```

Dua detail `\copy` yang sengaja dibuat begitu: `ext_laus` menyimpan
`state_fips` sebagai kolom pertama karena urutan kolom di CSV-nya begitu
(`\copy` membaca posisi, bukan nama kolom); `NULL ''` di `ext_paylaw`
dan `ext_ncs` karena ada sel kosong di kolom DATE/NUMERIC
(`effective_date` kosong di 46 state, beberapa angka civilian NCS
kosong) — tanpa itu load-nya gagal. `ext_posting_title.job_id` dibuat
BIGINT (bukan TEXT) karena `fact_posting.job_id` di dump adalah bigint —
kalau TEXT, join Q3 akan error tipe data.

```sql
-- Hanya dua kolom dari dataset_clean.csv yang dibutuhkan:
\copy ext_posting_title (job_id, title) FROM 'dataset_clean.csv' WITH (FORMAT csv, HEADER true)
```

Catatan `\copy` terakhir: `dataset_clean.csv` punya 21 kolom — `\copy`
dengan daftar kolom `(job_id, title)` akan GAGAL karena kolomnya tidak
berurutan di awal file (title kolom ke-2, tapi ada 19 kolom setelahnya).
Cara yang bekerja: buat tabel staging penuh dulu, lalu isi
`ext_posting_title` dari situ — atau ekstrak dulu dua kolom itu ke CSV
kecil dengan Python/Excel. Jangan pakai `\copy` satu baris di atas
apa adanya.

Smoke test setelah load (harus keluar angka ini):

```sql
SELECT 'ext_state_clean' AS tabel, COUNT(*) AS baris FROM ext_state_clean
UNION ALL SELECT 'ext_laus', COUNT(*) FROM ext_laus
UNION ALL SELECT 'ext_paylaw', COUNT(*) FROM ext_paylaw
UNION ALL SELECT 'ext_title_soc', COUNT(*) FROM ext_title_soc
UNION ALL SELECT 'ext_oews_median', COUNT(*) FROM ext_oews_median
UNION ALL SELECT 'ext_ncs', COUNT(*) FROM ext_ncs
UNION ALL SELECT 'ext_benefit_map', COUNT(*) FROM ext_benefit_map
UNION ALL SELECT 'ext_posting_title', COUNT(*) FROM ext_posting_title;
```

Harus keluar: ext_state_clean 84; ext_laus 102; ext_paylaw 51;
ext_title_soc 200; ext_oews_median 35.309; ext_ncs 12;
ext_benefit_map 12; ext_posting_title 123.849. Kalau
ext_posting_title kurang dari itu, ada job_id duplikat/ganda di CSV —
cek, jangan lanjut sebelum cocok.

## Langkah 2 — Query join (tempel ke Metabase SQL editor)

Aturan yang sama dengan file SQL utama: gaji HANYA dari
`salary_valid = 1`; `views_count` itu proxy (pakai AVG, jangan SUM);
jendela listing 4 minggu, bukan tren waktu. State yang tidak
terpetakan (`state_clean = ''`) selalu dikeluarkan dari panel per-state.

### Q1 — Pay-transparency law: berapa % lowongan yang gajinya valid, di state ber-UU vs tanpa UU

```sql
SELECT CASE WHEN p.has_law = 1 THEN 'State ber-UU pay transparency' ELSE 'State tanpa UU' END AS kelompok,
       COUNT(*) AS postings,
       SUM(CASE WHEN f.salary_valid = 1 THEN 1 ELSE 0 END) AS valid_salary_postings,
       ROUND(100.0 * SUM(CASE WHEN f.salary_valid = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS valid_salary_pct
FROM fact_posting f
JOIN dim_location l ON l.location_key = f.location_key
JOIN ext_state_clean s ON s.state_raw = l.state
JOIN ext_paylaw p ON p.state = s.state_clean
WHERE s.state_clean <> ''
GROUP BY p.has_law
ORDER BY p.has_law DESC;
```

Harus keluar (jangkar, 12 Nov 2026): ber-UU 23.034 lowongan, 43,0%
valid; tanpa UU 82.888 lowongan, 17,1% valid. (Dua lowongan di ON/QC
tidak masuk hitungan karena provinsinya tidak ada di file pay-law.)
Kalau angkanya jauh dari ini, cek dulu `ext_state_clean` dan
`ext_paylaw` sudah ter-load benar.

### Q2 — LAUS: lowongan + % gaji valid per state, dengan unemployment rate (top 10 state)

```sql
SELECT s.state_clean AS state,
       COUNT(*) AS postings,
       ROUND(100.0 * SUM(CASE WHEN f.salary_valid = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS valid_salary_pct,
       la.avg_unemployment_mar_apr_2024
FROM fact_posting f
JOIN dim_location l ON l.location_key = f.location_key
JOIN ext_state_clean s ON s.state_raw = l.state
JOIN (SELECT state_abbr, AVG(unemployment_rate_pct) AS avg_unemployment_mar_apr_2024
      FROM ext_laus WHERE year = 2024 AND month IN (3, 4)
      GROUP BY state_abbr) la ON la.state_abbr = s.state_clean
WHERE s.state_clean <> ''
GROUP BY s.state_clean, la.avg_unemployment_mar_apr_2024
ORDER BY postings DESC
LIMIT 10;
```

LAUS-nya diagregasi dulu per state (rata-rata Mar–Apr) di subquery —
jangan join langsung ke `ext_laus` dengan `month IN (3, 4)`, karena tiap
lowongan akan kehitung dua kali (satu baris Mar, satu baris Apr).

Footnote: unemployment dirata-rata Mar–Apr 2024 (dua bulan jendela
listing). CA dan NV — pengangguran tertinggi — justru yang lowongannya
paling banyak: sinyal pasar longgar, bukan ketat.

### Q3 — OEWS: premium/diskon gaji vs median pasar per judul (hanya judul dengan n >= 30)

```sql
SELECT pt.title AS jabatan,
       COUNT(*) AS postings_bergaji_valid,
       ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (
           ORDER BY 100.0 * (((f.salary_min_annual_usd + f.salary_max_annual_usd) / 2.0) - o.a_median_usd) / o.a_median_usd
       ))::numeric, 1) AS median_gap_pct_vs_oews
FROM fact_posting f
JOIN dim_location l ON l.location_key = f.location_key
JOIN ext_state_clean s ON s.state_raw = l.state
JOIN ext_posting_title pt ON pt.job_id = f.job_id
JOIN ext_title_soc t ON t.title = pt.title
JOIN ext_oews_median o ON o.state = s.state_clean AND o.soc_code = t.soc_code
WHERE f.salary_valid = 1 AND s.state_clean <> ''
GROUP BY pt.title
HAVING COUNT(*) >= 30
ORDER BY median_gap_pct_vs_oews DESC;
```

DIPERBAIKI 15 Nov 2026 saat eksekusi pertama (lihat bagian verifikasi di
bawah): (1) hasil PERCENTILE_CONT bertipe double precision sehingga ROUND
dua argumen tidak dikenal PostgreSQL — harus di-cast `::numeric` dulu;
(2) GROUP BY yang benar adalah judul lowongan (`pt.title`), bukan
`t.soc_title` — jangkar di bawah dihitung per judul lowongan; grouping per
SOC title menggabungkan beberapa judul (mis. Accountants and Auditors
n=241) dan angkanya tidak cocok dengan jangkar.

Harus keluar (jangkar, 12 Nov 2026): Senior Accountant +7,6% (n=101),
Project Manager +12,7% (n=86), Executive Assistant +8,4% (n=74),
Administrative Assistant +2,8% (n=80), Controller −13,1% (n=82),
Staff Accountant −21,2% (n=87). Total baris query ini: 3.161 lowongan.

### Q4 — NCS: % lowongan yang menyebut benefit vs % pekerja dengan akses (nasional)

```sql
SELECT b.benefit_type AS benefit_karirku,
       m.ncs_benefit AS kategori_ncs,
       COUNT(DISTINCT fb.job_id) AS postings,
       ROUND(100.0 * COUNT(DISTINCT fb.job_id) / (SELECT COUNT(*) FROM fact_posting), 1) AS pct_postings_menyebut,
       n.civilian_access_pct AS ncs_civilian_access_pct
FROM fact_posting_benefit fb
JOIN dim_benefit b ON b.benefit_key = fb.benefit_key
JOIN ext_benefit_map m ON m.internal_benefit_type = b.benefit_type
JOIN ext_ncs n ON n.benefit = m.ncs_benefit
WHERE m.ncs_benefit <> '' AND n.civilian_access_pct IS NOT NULL
GROUP BY b.benefit_type, m.ncs_benefit, n.civilian_access_pct
ORDER BY pct_postings_menyebut DESC;
```

Hanya 3 tipe yang muncul dari query ini apa adanya (401(k), Pension
plan, Medical insurance). Sisanya gugur karena tiga sebab berbeda:
Disability insurance terpetakan ke string gabungan
`short_term_disability; long_term_disability` sehingga tidak ke-join
dengan `ext_ncs` (pecah manual jadi dua baris kalau mau memakainya);
Dental, Vision, Paid maternity/paternity leave angka civilian-nya
kosong di file NCS; 4 tipe (Child care, Commuter, Student loan,
Tuition) memang tidak punya padanan NCS. Tulis di dashboard: "penyebut
berbeda — KarirKu = % lowongan yang menyebut, NCS = % pekerja dengan
akses; perbandingan ini searah saja."

## Status verifikasi — SUDAH DIEKSEKUSI 15 Nov 2026

Seluruh isi file ini dieksekusi 15 Nov 2026 di PostgreSQL 16.15 (database
uji yang isinya cermin persis laptop: dump yang sama + pemindahan schema
ke dw_lowongan yang sama; tabel ext_* dimuat di schema dw_lowongan).
Hasilnya:

- Smoke test load: kedelapan hitungan cocok persis (84 / 102 / 51 / 200 /
  35.309 / 12 / 12 / 123.849).
- Q1 cocok persis dengan jangkar: ber-UU 23.034 lowongan 43,0% valid;
  tanpa UU 82.888 lowongan 17,1% valid.
- Q2 jalan; CA 11.484 lowongan dan unemployment 5,2 cocok dengan jangkar.
- Q3: total irisan 3.161 cocok; setelah dua perbaikan di atas, keenam
  jangkar per judul cocok persis (Senior Accountant +7,6 n=101; Project
  Manager +12,7 n=86; Executive Assistant +8,4 n=74; Administrative
  Assistant +2,8 n=80; Controller -13,1 n=82; Staff Accountant -21,2 n=87).
- Q4 jalan; tepat 3 baris seperti diprediksi (401(k) 18,7% vs 75;
  Medical insurance 7,7% vs 75; Pension plan 0,7% vs 75).
- Script load siap pakai untuk laptop: `load-external-tables.sql`
  (DDL + \copy + smoke test), dengan `posting_title.csv` hasil ekstrak
  dua kolom dataset_clean.csv sebagai file pendamping — jebakan \copy
  dua kolom di Langkah 1 sudah teratasi oleh file ekstrak itu.

## Yang belum dicek
- OEWS Mei 2023 vs lowongan Mar–Apr 2024: vintage-nya beda 10 bulan.
  Kalau mau yang sebaya, unduh OEWS Mei 2024 (rilis Apr 2025) dan ulangi
  ekstrak yang sama — tapi itu mengubah angka jangkar di atas, jadi
  putuskan dulu: pakai Mei 2023 apa adanya (didokumentasikan), atau
  ganti vintage (angka Q3 berubah).
- `map_title_soc_full.csv` (190 KB, di folder yang sama) belum dipakai —
  isinya pemetaan judul yang lebih luas; kalau panel OEWS mau diperlebar
  dari 200 judul, cek file itu dulu sebelum memetakan ulang.
- `bls_ep_2023-33.zip` (Employment Projections) belum dipakai — di luar
  scope 5 dashboard yang dikomit; jangan dimasukkan tanpa keputusan.
