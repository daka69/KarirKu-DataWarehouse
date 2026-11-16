-- Perbaikan khusus ext_posting_title (jalankan dari folder external):
--    psql -U postgres -d dw_lowongan -f load-posting-title-fix.sql
-- Sebab: psql di Windows membaca file sebagai WIN1252, sedangkan
-- posting_title.csv ber-encoding UTF-8; \encoding UTF8 menyelaraskannya.
-- Hasil akhir harus: 123849 baris.
SET search_path TO dw_lowongan;
\encoding UTF8
\copy ext_posting_title (job_id, title) FROM 'posting_title.csv' WITH (FORMAT csv, HEADER true)
SELECT COUNT(*) AS ext_posting_title FROM ext_posting_title;
