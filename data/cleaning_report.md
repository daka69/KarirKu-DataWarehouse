# Laporan Cleaning Dataset

== LOAD ==

postings: 123849 baris, 123849 job_id unik

companies: 24473 baris

job_skills: 213768 baris; skill unik di mappings: 35

days_listed terisi: 123849 (100.0%)

pay_period tak dikenal: 0

gaji disclosed: 29793 (24.1%); non-USD: 15

quarantine: 478 baris (outlier gaji: 464, non-USD: 14) -> quarantine.csv

gaji: valid 29315 (23.7% dari total), invalid 478, tanpa gaji 94056

company_id: float64 di postings (1717 null) vs int64 di companies

overlap company_id setelah penyeragaman tipe: 100.0% -> JOIN KEY UTAMA

nama perusahaan unik (ternormalisasi) di postings: 24385

nama perusahaan unik (ternormalisasi) di companies: 24385

match via nama ternormalisasi (fallback utk company_id null): 98.6%

lokasi ter-parse (ada state): 89.2%

job_skills: 205778 baris valid; orphan job_id dibuang: 7990


== OUTPUT di /home/hatch/workspace/your_files/bi-uts-data-clean ==

  cleaning_report.md  (0.0 MB)

  companies_clean.csv  (23.7 MB)

  companies_clean.xlsx  (10.4 MB)

  dataset_clean.csv  (27.8 MB)

  dataset_clean.xlsx  (15.3 MB)

  dim_benefit.csv  (0.0 MB)

  dim_company.csv  (23.8 MB)

  dim_date.csv  (0.0 MB)

  dim_job_profile.csv  (0.0 MB)

  dim_location.csv  (0.3 MB)

  dim_skill.csv  (0.0 MB)

  dim_skill_nlp.csv  (0.0 MB)

  dw_lowongan_pg16.sql  (38.9 MB)

  fact_posting.csv  (7.2 MB)

  fact_posting_benefit.csv  (1.1 MB)

  fact_posting_skill.csv  (3.0 MB)

  fact_posting_skill_nlp.csv  (3.6 MB)

  kamus-kolom.md  (0.0 MB)

  posting_skills_clean.csv  (6.1 MB)

  posting_skills_nlp.csv  (5.4 MB)

  postings_clean.csv  (39.2 MB)

  quarantine.csv  (0.1 MB)

  skill_dictionary.csv  (0.0 MB)

  warehouse.db  (48.1 MB)


Kolom yang TIDAK dibawa (diarsip di staging): description, skills_desc (98% null), med_salary (94,9% null), normalized_salary (dipakai validasi silang saja), original_listed_time, posting_domain, application_url

Aturan validasi gaji: outlier = gaji tahunan < $10.000 atau > $1.000.000 (dugaan kesalahan entri); 15 baris non-USD tidak dikonversi. Gaji bermasalah di-NULL-kan + salary_valid=0, posting tetap dimuat (prinsip: jangan buang baris karena satu kolom rusak). Faktor jam kerja 2080 jam/tahun.