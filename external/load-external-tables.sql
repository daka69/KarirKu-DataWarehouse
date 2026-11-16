-- Load 8 tabel eksternal ke schema dw_lowongan (database dw_lowongan).
-- SUDAH DIUJI 15 Nov 2026 di PostgreSQL 16.15: semua hitungan smoke test
-- cocok dengan jangkar (lihat external-joins-week2.md).
--
-- Cara pakai di laptop:
-- 1. Kumpulkan file CSV berikut dalam SATU folder bersama file ini:
--    map_state_clean.csv, laus_state_2024M03-M04.csv,
--    state_pay_transparency_law.csv, map_title_soc.csv,
--    ext_oews_median_may2023.csv, ncs_benefit_access_march2024.csv,
--    map_benefit_ncs.csv  (dari folder external/ data UTS)
--    posting_title.csv    (file pendamping script ini; ekstrak job_id+title
--                          dari dataset_clean.csv, 123.849 baris)
-- 2. Jalankan dari folder itu:
--    psql -U postgres -d dw_lowongan -f load-external-tables.sql
-- \copy membaca path relatif terhadap folder tempat psql dijalankan.

SET search_path TO dw_lowongan;
-- Wajib di Windows: psql default membaca file sebagai WIN1252, sedangkan
-- posting_title.csv UTF-8 (error byte 0x90 ditemukan saat uji Windows
-- 15 Nov 2026). Baris ini menyelaraskan encoding sebelum \copy.
\encoding UTF8

CREATE TABLE IF NOT EXISTS ext_state_clean (
    state_raw   TEXT PRIMARY KEY,
    state_clean TEXT
);
CREATE TABLE IF NOT EXISTS ext_laus (
    state_fips             TEXT,
    state_abbr             TEXT,
    state_name             TEXT,
    year                   INT,
    month                  INT,
    unemployment_rate_pct  NUMERIC,
    labor_force_thousands  NUMERIC,
    PRIMARY KEY (state_abbr, year, month)
);
CREATE TABLE IF NOT EXISTS ext_paylaw (
    state          TEXT PRIMARY KEY,
    has_law        INT,
    effective_date DATE,
    requirement    TEXT
);
CREATE TABLE IF NOT EXISTS ext_title_soc (
    title          TEXT PRIMARY KEY,
    postings_count INT,
    soc_code       TEXT,
    soc_title      TEXT,
    confidence     TEXT,
    notes          TEXT
);
CREATE TABLE IF NOT EXISTS ext_oews_median (
    state         TEXT,
    soc_code      TEXT,
    soc_title     TEXT,
    a_median_usd  INT,
    PRIMARY KEY (state, soc_code)
);
CREATE TABLE IF NOT EXISTS ext_ncs (
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
CREATE TABLE IF NOT EXISTS ext_benefit_map (
    internal_benefit_type TEXT PRIMARY KEY,
    ncs_benefit           TEXT,
    notes                 TEXT
);
CREATE TABLE IF NOT EXISTS ext_posting_title (
    job_id BIGINT PRIMARY KEY,
    title  TEXT
);

\copy ext_state_clean FROM 'map_state_clean.csv' WITH (FORMAT csv, HEADER true)
\copy ext_laus FROM 'laus_state_2024M03-M04.csv' WITH (FORMAT csv, HEADER true)
\copy ext_paylaw FROM 'state_pay_transparency_law.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy ext_title_soc FROM 'map_title_soc.csv' WITH (FORMAT csv, HEADER true)
\copy ext_oews_median FROM 'ext_oews_median_may2023.csv' WITH (FORMAT csv, HEADER true)
\copy ext_ncs FROM 'ncs_benefit_access_march2024.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy ext_benefit_map FROM 'map_benefit_ncs.csv' WITH (FORMAT csv, HEADER true)
\copy ext_posting_title (job_id, title) FROM 'posting_title.csv' WITH (FORMAT csv, HEADER true)

-- Smoke test: harus keluar 84 / 102 / 51 / 200 / 35309 / 12 / 12 / 123849
SELECT 'ext_state_clean' AS tabel, COUNT(*) AS baris FROM ext_state_clean
UNION ALL SELECT 'ext_laus', COUNT(*) FROM ext_laus
UNION ALL SELECT 'ext_paylaw', COUNT(*) FROM ext_paylaw
UNION ALL SELECT 'ext_title_soc', COUNT(*) FROM ext_title_soc
UNION ALL SELECT 'ext_oews_median', COUNT(*) FROM ext_oews_median
UNION ALL SELECT 'ext_ncs', COUNT(*) FROM ext_ncs
UNION ALL SELECT 'ext_benefit_map', COUNT(*) FROM ext_benefit_map
UNION ALL SELECT 'ext_posting_title', COUNT(*) FROM ext_posting_title;
