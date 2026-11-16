# Laporan Validasi ETL Data Warehouse KarirKu

- Waktu run: 2026-11-16 18:25:55
- Mode: full
- Database: etl_test
- Skema: staging -> dw_lowongan

## Jumlah baris per tabel

| Tabel | Target | Tercapai | Status |
|---|---:|---:|---|
| dim_company | 24474 | 24474 | Sesuai |
| dim_location | 8524 | 8524 | Sesuai |
| dim_date | 208 | 208 | Sesuai |
| dim_job_profile | 206 | 206 | Sesuai |
| dim_skill | 35 | 35 | Sesuai |
| dim_skill_nlp | 77 | 77 | Sesuai |
| dim_benefit | 12 | 12 | Sesuai |
| fact_posting | 123849 | 123849 | Sesuai |
| fact_posting_skill | 205778 | 205778 | Sesuai |
| fact_posting_skill_nlp | 249896 | 249896 | Sesuai |
| fact_posting_benefit | 65393 | 65393 | Sesuai |
| **Total** | **678452** | **678452** | **Sesuai** |

## Pemeriksaan rekonsiliasi

| Pemeriksaan | Target | Tercapai | Status |
|---|---:|---:|---|
| Lowongan bergaji valid (salary_valid = 1) | 29315 (23,7%) | 29315 (23,7%) | Sesuai |
| Benefit inferred (is_inferred = 1) | 59,1% | 59,1% (38657 dari 65393) | Sesuai |
| Orphan foreign key (total 11 pemeriksaan) | 0 | 0 | Sesuai |
| Baris staging postings (stg_postings) | - | 123849 | - |
| Baris staging pasangan skill (stg_posting_skills) | - | 205778 | - |
| Baris staging pasangan skill NLP (stg_posting_skills_nlp) | - | 249896 | - |
| Baris masuk quarantine pada run ini | 0 | 0 | Sesuai |

## Orphan foreign key per pemeriksaan

| Pemeriksaan | Target | Tercapai | Status |
|---|---:|---:|---|
| fact_posting.company_key | 0 | 0 | Sesuai |
| fact_posting.location_key | 0 | 0 | Sesuai |
| fact_posting.job_profile_key | 0 | 0 | Sesuai |
| fact_posting.listed_date_key | 0 | 0 | Sesuai |
| fact_posting.expiry_date_key | 0 | 0 | Sesuai |
| fact_posting_skill.job_id | 0 | 0 | Sesuai |
| fact_posting_skill.skill_key | 0 | 0 | Sesuai |
| fact_posting_skill_nlp.job_id | 0 | 0 | Sesuai |
| fact_posting_skill_nlp.skill_key | 0 | 0 | Sesuai |
| fact_posting_benefit.job_id | 0 | 0 | Sesuai |
| fact_posting_benefit.benefit_key | 0 | 0 | Sesuai |

## Catatan

- Target adalah jumlah baris build Oktober yang terverifikasi pada dump dw_lowongan_pg16.sql.
