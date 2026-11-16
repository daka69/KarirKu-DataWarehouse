-- Pindahkan 11 tabel warehouse dari schema public ke schema dw_lowongan,
-- dan buat schema staging (kosong; tabel staging dimuat pada implementasi ETL).
-- Sesuai requirement dokumen UTS: satu instance PostgreSQL 16, dua schema
-- staging + dw_lowongan. Jalankan SATU KALI setelah restore dump:
--   psql -U postgres -d dw_lowongan -f move-to-dw-schema.sql
-- ALTER TABLE ... SET SCHEMA memindahkan tabel beserta index, constraint,
-- dan sequence yang dimilikinya; relasi antar tabel tetap utuh karena
-- kesebelas tabel pindah bersama.

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS dw_lowongan;

ALTER TABLE public.dim_benefit SET SCHEMA dw_lowongan;
ALTER TABLE public.dim_company SET SCHEMA dw_lowongan;
ALTER TABLE public.dim_date SET SCHEMA dw_lowongan;
ALTER TABLE public.dim_job_profile SET SCHEMA dw_lowongan;
ALTER TABLE public.dim_location SET SCHEMA dw_lowongan;
ALTER TABLE public.dim_skill SET SCHEMA dw_lowongan;
ALTER TABLE public.dim_skill_nlp SET SCHEMA dw_lowongan;
ALTER TABLE public.fact_posting SET SCHEMA dw_lowongan;
ALTER TABLE public.fact_posting_benefit SET SCHEMA dw_lowongan;
ALTER TABLE public.fact_posting_skill SET SCHEMA dw_lowongan;
ALTER TABLE public.fact_posting_skill_nlp SET SCHEMA dw_lowongan;

-- Verifikasi (jalankan terpisah setelah perintah di atas):
--   SELECT table_schema, count(*) FROM information_schema.tables
--   WHERE table_schema IN ('dw_lowongan','staging','public')
--   GROUP BY table_schema;
--   -> dw_lowongan = 11, public = 0 (staging tidak berisi tabel dari dump)
--   SELECT count(*) FROM dw_lowongan.fact_posting;  -> 123849
