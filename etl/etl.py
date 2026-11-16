#!/usr/bin/env python3
"""
ETL Data Warehouse KarirKu — Kecerdasan Bisnis UAS MTI.

Script ini membangun ulang data warehouse `dw_lowongan` dari CSV hasil
cleaning (folder bi-uts-data-clean), mengikuti rancangan dokumen UTS:
PostgreSQL 16, skema galaxy (3 tabel fakta, 7 dimensi), SCD Type 1,
load awal full dan incremental harian.

Alur: Extract (CSV -> schema staging, tabel stg_*, tanpa constraint)
      -> Transform (pembersihan tipe, pembentukan dimensi, penautan kunci)
      -> Load (schema dw_lowongan).

Mode:
  --mode full         : TRUNCATE semua tabel dw_lowongan lalu muat ulang.
                        Opsi --cutoff YYYY-MM-DD menahan lowongan dengan
                        listed_date sesudah tanggal itu (untuk simulasi
                        load parsial sebelum incremental).
  --mode incremental  : wajib --cutoff YYYY-MM-DD. Hanya lowongan dengan
                        listed_date sesudah cutoff yang belum ada di
                        fact_posting yang dimuat; anggota dimensi baru
                        ditambahkan seperlunya. Aman dijalankan berulang
                        (idempotent, tidak ada duplikat).

Koneksi: environment variable DATABASE_URL, contoh
  postgresql+psycopg2://postgres:postgres@localhost:5432/dw_lowongan
Opsi --database mengganti nama database pada URL itu.

Baris sumber yang rusak (job_id tidak dapat diurai, tanggal tidak valid,
pasangan skill yatim) tidak menggagalkan load; baris itu dicatat ke
quarantine_output.csv dan dihitung pada laporan validasi akhir.

Artefak dokumentasi setiap run: etl.log (log bertimestamp per langkah)
dan validation_report.md (tabel target vs tercapai dan rekonsiliasi),
keduanya ditulis di folder script ini untuk Lampiran 5 laporan UAS.

Catatan sumber benefit: tidak ada CSV hasil cleaning yang memuat benefit
per lowongan, sehingga dim_benefit dan fact_posting_benefit hanya dimuat
bila file opsional `job_benefits.csv` (kolom job_id, benefit_type,
is_inferred) tersedia di folder sumber. Tanpa file itu kedua tabel dibuat
kosong dan ketiadaannya dilaporkan eksplisit pada log dan validasi,
bukan disembunyikan.
"""

import argparse
import io
import logging
import os
import sys
from datetime import date, datetime

import pandas as pd
from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SOURCE_DIR = os.path.expanduser(
    "~/workspace/your_files/bi-uts-data-clean")
DEFAULT_DATABASE_URL = (
    "postgresql+psycopg2://postgres:postgres@localhost:5432/dw_lowongan")

# File sumber -> tabel staging. Semua kolom staging bertipe text.
SOURCE_FILES = {
    "stg_postings": "postings_clean.csv",
    "stg_companies": "companies_clean.csv",
    "stg_dataset": "dataset_clean.csv",
    "stg_posting_skills": "posting_skills_clean.csv",
    "stg_posting_skills_nlp": "posting_skills_nlp.csv",
    "stg_skill_dictionary": "skill_dictionary.csv",
    "stg_quarantine": "quarantine.csv",
}

# Kode state Amerika Serikat (2 huruf, termasuk DC). Kolom country pada
# dim_location hanya diisi 'United States' bila state hasil parsing adalah
# kode state yang sah; nilai lain (nama state penuh, string "... Area",
# wilayah luar AS, 'United States', 'Unknown') menghasilkan NULL. Aturan
# ini mereproduksi persis build Oktober (terverifikasi 8.524/8.524 baris).
US_STATE_CODES = set(
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI "
    "MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT "
    "VA WA WV WI WY".split())

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
             "Saturday", "Sunday"]

UNKNOWN_COMPANY = {
    "company_key": 1, "company_id": -1, "name": "Unknown",
    "name_norm": "__unknown__", "description": None, "company_size": None,
    "city": None, "state": None, "country": None, "zip_code": None,
    "address": None, "url": None,
}

DW_TABLES = ["dim_company", "dim_location", "dim_date", "dim_job_profile",
             "dim_skill", "dim_skill_nlp", "dim_benefit", "fact_posting",
             "fact_posting_skill", "fact_posting_skill_nlp",
             "fact_posting_benefit"]

# Target validasi: jumlah baris build Oktober yang sudah terverifikasi
# (dump dw_lowongan_pg16.sql). Laporan validasi membandingkan hasil run
# terhadap angka ini.
TARGETS = {"dim_company": 24474, "dim_location": 8524, "dim_date": 208,
           "dim_job_profile": 206, "dim_skill": 35, "dim_skill_nlp": 77,
           "dim_benefit": 12, "fact_posting": 123849,
           "fact_posting_skill": 205778, "fact_posting_skill_nlp": 249896,
           "fact_posting_benefit": 65393}
TOTAL_TARGET = 678452
SALARY_VALID_TARGET = 29315          # 23,7% dari fact_posting
INFERRED_PCT_TARGET = 59.1           # persen is_inferred pada benefit

# DDL identik dengan dump dw_lowongan_pg16.sql (nama/kolom/tipe sama),
# ditempatkan pada schema dw_lowongan.
DDL_STATEMENTS = [
    "CREATE SCHEMA IF NOT EXISTS staging",
    "CREATE SCHEMA IF NOT EXISTS dw_lowongan",
    """CREATE TABLE IF NOT EXISTS dw_lowongan.dim_benefit (
        benefit_key integer NOT NULL, benefit_type text,
        CONSTRAINT dim_benefit_pkey PRIMARY KEY (benefit_key))""",
    """CREATE TABLE IF NOT EXISTS dw_lowongan.dim_company (
        company_key integer NOT NULL, company_id bigint, name text,
        name_norm text, description text, company_size smallint,
        city text, state text, country text, zip_code text, address text,
        url text, CONSTRAINT dim_company_pkey PRIMARY KEY (company_key))""",
    """CREATE TABLE IF NOT EXISTS dw_lowongan.dim_date (
        date_key integer NOT NULL, full_date date NOT NULL, day smallint,
        month smallint, year smallint, quarter smallint,
        day_of_week text, is_weekend boolean,
        CONSTRAINT dim_date_pkey PRIMARY KEY (date_key))""",
    """CREATE TABLE IF NOT EXISTS dw_lowongan.dim_job_profile (
        job_profile_key integer NOT NULL, experience_level text,
        work_type text, remote_allowed text, sponsored smallint,
        application_type text,
        CONSTRAINT dim_job_profile_pkey PRIMARY KEY (job_profile_key))""",
    """CREATE TABLE IF NOT EXISTS dw_lowongan.dim_location (
        location_key integer NOT NULL, city text, state text, country text,
        CONSTRAINT dim_location_pkey PRIMARY KEY (location_key))""",
    """CREATE TABLE IF NOT EXISTS dw_lowongan.dim_skill (
        skill_key integer NOT NULL, skill_abr text, skill_name text,
        CONSTRAINT dim_skill_pkey PRIMARY KEY (skill_key))""",
    """CREATE TABLE IF NOT EXISTS dw_lowongan.dim_skill_nlp (
        skill_key integer NOT NULL, skill_name text,
        CONSTRAINT dim_skill_nlp_pkey PRIMARY KEY (skill_key))""",
    """CREATE TABLE IF NOT EXISTS dw_lowongan.fact_posting (
        job_id bigint NOT NULL, company_key integer, location_key integer,
        job_profile_key integer, listed_date_key integer,
        expiry_date_key integer, views_count integer, applies_count integer,
        salary_min_annual_usd numeric(12,2),
        salary_max_annual_usd numeric(12,2), salary_disclosed smallint,
        salary_valid smallint, days_listed integer,
        CONSTRAINT fact_posting_pkey PRIMARY KEY (job_id),
        CONSTRAINT fact_posting_company_key_fkey FOREIGN KEY (company_key)
            REFERENCES dw_lowongan.dim_company (company_key),
        CONSTRAINT fact_posting_location_key_fkey FOREIGN KEY (location_key)
            REFERENCES dw_lowongan.dim_location (location_key),
        CONSTRAINT fact_posting_job_profile_key_fkey
            FOREIGN KEY (job_profile_key)
            REFERENCES dw_lowongan.dim_job_profile (job_profile_key),
        CONSTRAINT fact_posting_listed_date_key_fkey
            FOREIGN KEY (listed_date_key)
            REFERENCES dw_lowongan.dim_date (date_key),
        CONSTRAINT fact_posting_expiry_date_key_fkey
            FOREIGN KEY (expiry_date_key)
            REFERENCES dw_lowongan.dim_date (date_key))""",
    """CREATE TABLE IF NOT EXISTS dw_lowongan.fact_posting_benefit (
        job_id bigint NOT NULL, benefit_key integer NOT NULL,
        is_inferred smallint,
        CONSTRAINT fact_posting_benefit_pkey PRIMARY KEY (job_id, benefit_key),
        CONSTRAINT fact_posting_benefit_job_id_fkey FOREIGN KEY (job_id)
            REFERENCES dw_lowongan.fact_posting (job_id),
        CONSTRAINT fact_posting_benefit_benefit_key_fkey
            FOREIGN KEY (benefit_key)
            REFERENCES dw_lowongan.dim_benefit (benefit_key))""",
    """CREATE TABLE IF NOT EXISTS dw_lowongan.fact_posting_skill (
        job_id bigint NOT NULL, skill_key integer NOT NULL,
        CONSTRAINT fact_posting_skill_pkey PRIMARY KEY (job_id, skill_key),
        CONSTRAINT fact_posting_skill_job_id_fkey FOREIGN KEY (job_id)
            REFERENCES dw_lowongan.fact_posting (job_id),
        CONSTRAINT fact_posting_skill_skill_key_fkey FOREIGN KEY (skill_key)
            REFERENCES dw_lowongan.dim_skill (skill_key))""",
    """CREATE TABLE IF NOT EXISTS dw_lowongan.fact_posting_skill_nlp (
        job_id bigint NOT NULL, skill_key integer NOT NULL,
        CONSTRAINT fact_posting_skill_nlp_pkey PRIMARY KEY (job_id, skill_key),
        CONSTRAINT fact_posting_skill_nlp_job_id_fkey FOREIGN KEY (job_id)
            REFERENCES dw_lowongan.fact_posting (job_id),
        CONSTRAINT fact_posting_skill_nlp_skill_key_fkey
            FOREIGN KEY (skill_key)
            REFERENCES dw_lowongan.dim_skill_nlp (skill_key))""",
    "CREATE INDEX IF NOT EXISTS idx_fact_company "
    "ON dw_lowongan.fact_posting (company_key)",
    "CREATE INDEX IF NOT EXISTS idx_fact_date "
    "ON dw_lowongan.fact_posting (listed_date_key)",
]

log = logging.getLogger("etl")


def setup_logging():
    """Logging ke console dan file etl.log di folder script."""
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    fh = logging.FileHandler(os.path.join(SCRIPT_DIR, "etl.log"),
                             encoding="utf-8")
    fh.setFormatter(fmt)
    log.handlers = [ch, fh]


# ---------------------------------------------------------------------------
# Utilitas
# ---------------------------------------------------------------------------

class Quarantine:
    """Menampung baris rusak beserta alasannya; ditulis ke CSV di akhir run."""

    def __init__(self):
        self.rows = []

    def add(self, source, job_id, reason):
        self.rows.append({"source": source, "job_id": job_id,
                          "reason": reason})

    def __len__(self):
        return len(self.rows)

    def write(self):
        path = os.path.join(SCRIPT_DIR, "quarantine_output.csv")
        pd.DataFrame(self.rows,
                     columns=["source", "job_id", "reason"]).to_csv(
                         path, index=False)
        return path


def bulk_load(conn, df, schema, table):
    """Muat DataFrame ke tabel lewat COPY (cepat, NULL ditulis sebagai \\N)."""
    if df.empty:
        log.info("  %s.%s: 0 baris (kosong)", schema, table)
        return
    buf = io.StringIO()
    df.to_csv(buf, index=False, na_rep="\\N")
    buf.seek(0)
    cols = ", ".join(df.columns)
    raw = conn.connection.dbapi_connection
    with raw.cursor() as cur:
        cur.copy_expert(
            f"COPY {schema}.{table} ({cols}) FROM STDIN "
            "WITH (FORMAT csv, HEADER true, NULL '\\N')", buf)
    log.info("  %s.%s: %d baris", schema, table, len(df))


def to_int(series):
    """Konversi kolom teks ke Int64 (nullable); nilai tak valid menjadi NA."""
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def clean_text(series):
    """String kosong diperlakukan sebagai NULL, selaras pembacaan CSV cleaning."""
    return series.mask(series == "")


# ---------------------------------------------------------------------------
# Extract: CSV -> staging
# ---------------------------------------------------------------------------

def extract(engine, source_dir, quarantine):
    """Baca semua CSV sumber (semua kolom teks) dan muat ke schema staging.

    Staging selalu dibangun ulang penuh pada setiap run (landing zone),
    tanpa constraint. Mengembalikan dict DataFrame hasil baca balik staging
    untuk tahap transform.
    """
    log.info("EXTRACT: membaca CSV dari %s", source_dir)
    frames = {}
    with engine.begin() as conn:
        for table, filename in SOURCE_FILES.items():
            path = os.path.join(source_dir, filename)
            if not os.path.exists(path):
                raise FileNotFoundError(f"File sumber tidak ditemukan: {path}")
            raw = pd.read_csv(path, dtype=str, low_memory=False)
            conn.execute(text(f"DROP TABLE IF EXISTS staging.{table}"))
            cols = ", ".join(f'"{c}" text' for c in raw.columns)
            conn.execute(text(f"CREATE TABLE staging.{table} ({cols})"))
            bulk_load(conn, raw, "staging", table)
            frames[table] = raw
    q = frames["stg_quarantine"]
    log.info("  quarantine.csv sumber (gaji outlier/non-USD, sudah di-NULL-kan "
             "saat cleaning): %d baris", len(q))
    return frames


def read_staging(engine):
    """Baca balik tabel staging sebagai DataFrame (sumber tahap transform)."""
    frames = {}
    with engine.connect() as conn:
        for table in SOURCE_FILES:
            frames[table] = pd.read_sql_query(
                text(f"SELECT * FROM staging.{table}"), conn)
    return frames


# ---------------------------------------------------------------------------
# Transform: pembentukan dimensi
# ---------------------------------------------------------------------------

def build_dim_company(companies):
    """dim_company: baris Unknown (key 1) + seluruh companies_clean berurutan.

    Urutan kunci mengikuti urutan kemunculan di file companies (key 2, 3, ...),
    sama seperti build Oktober.
    """
    df = companies.copy()
    df["company_id"] = to_int(df["company_id"])
    df["company_size"] = to_int(df["company_size"])
    for c in ["name", "name_norm", "description", "city", "state", "country",
              "zip_code", "address", "url"]:
        df[c] = clean_text(df[c])
    df.insert(0, "company_key", range(2, len(df) + 2))
    unk = pd.DataFrame([UNKNOWN_COMPANY])
    return pd.concat([unk, df], ignore_index=True)[
        ["company_key", "company_id", "name", "name_norm", "description",
         "company_size", "city", "state", "country", "zip_code", "address",
         "url"]]


def location_frame(postings):
    """Pasangan (city, state) unik dari postings, urutan kemunculan pertama.

    State kosong menjadi 'Unknown' (konvensi cleaning). Country mengikuti
    aturan US_STATE_CODES.
    """
    loc = postings[["location_city", "location_state"]].copy()
    loc["location_state"] = loc["location_state"].fillna("Unknown")
    loc = loc.drop_duplicates().reset_index(drop=True)
    loc.insert(0, "location_key", range(1, len(loc) + 1))
    loc["country"] = ["United States" if s in US_STATE_CODES else None
                      for s in loc["location_state"]]
    return loc.rename(columns={"location_city": "city",
                               "location_state": "state"})[
                                   ["location_key", "city", "state",
                                    "country"]]


def date_frame(dates):
    """dim_date: kalender kontinu dari tanggal minimum ke maksimum.

    date_key berbentuk YYYYMMDD; day_of_week nama hari bahasa Inggris.
    """
    days = pd.date_range(min(dates), max(dates), freq="D")
    df = pd.DataFrame({"full_date": days.date})
    df.insert(0, "date_key", [int(d.strftime("%Y%m%d")) for d in days])
    df["day"] = days.day.astype("int16")
    df["month"] = days.month.astype("int16")
    df["year"] = days.year.astype("int16")
    df["quarter"] = ((days.month - 1) // 3 + 1).astype("int16")
    df["day_of_week"] = [DAY_NAMES[d.weekday()] for d in days]
    df["is_weekend"] = [d.weekday() >= 5 for d in days]
    return df


def profile_frame(postings):
    """dim_job_profile: kombinasi unik atribut profil, urutan kemunculan.

    Input adalah postings yang sudah ditempel atribut dataset_clean oleh
    attach_profile_attrs (experience_level, work_type, remote_allowed,
    application_type) plus sponsored dari postings_clean. Kombinasi hanya
    dibentuk dari postings yang ikut dimuat, supaya load parsial (cutoff)
    tidak menciptakan kombinasi berkunci yatim.
    """
    combos = postings[["experience_level", "work_type", "remote_allowed",
                       "sponsored", "application_type"]].drop_duplicates()
    combos = combos.reset_index(drop=True)
    combos.insert(0, "job_profile_key", range(1, len(combos) + 1))
    return combos


def skill_frame(pairs):
    """dim_skill: pasangan (skill_abr, skill_name) unik, urutan kemunculan."""
    sk = pairs[["skill_abr", "skill_name"]].drop_duplicates()
    sk = sk.reset_index(drop=True)
    sk.insert(0, "skill_key", range(1, len(sk) + 1))
    return sk


def skill_nlp_frame(dictionary):
    """dim_skill_nlp: 77 skill sesuai urutan skill_dictionary.csv."""
    sk = dictionary[["skill"]].copy()
    sk.insert(0, "skill_key", range(1, len(sk) + 1))
    return sk.rename(columns={"skill": "skill_name"})


# ---------------------------------------------------------------------------
# Transform: penyiapan postings dan penautan kunci fakta
# ---------------------------------------------------------------------------

def prepare_postings(stg_postings, quarantine):
    """Ketik ulang kolom postings staging; baris rusak masuk quarantine.

    Mengembalikan DataFrame postings bersih bertipe benar, termasuk kolom
    listed_date (date) hasil parse listed_time_at.
    """
    df = stg_postings.copy()
    df["job_id_num"] = pd.to_numeric(df["job_id"], errors="coerce")
    bad = df[df["job_id_num"].isna()]
    for _, r in bad.iterrows():
        quarantine.add("postings_clean", r["job_id"],
                       "job_id tidak dapat diurai sebagai angka")
    df = df[df["job_id_num"].notna()].copy()
    df["job_id"] = df["job_id_num"].astype("int64")
    dup = df[df.duplicated(subset=["job_id"], keep="first")]
    for _, r in dup.iterrows():
        quarantine.add("postings_clean", r["job_id"], "job_id duplikat")
    df = df.drop_duplicates(subset=["job_id"], keep="first")

    df["listed_ts"] = pd.to_datetime(df["listed_time_at"], errors="coerce")
    df["expiry_ts"] = pd.to_datetime(df["expiry_at"], errors="coerce")
    bad_date = df[df["listed_ts"].isna() | df["expiry_ts"].isna()]
    for _, r in bad_date.iterrows():
        quarantine.add("postings_clean", r["job_id"],
                       "listed_time_at/expiry_at tidak valid")
    df = df[df["listed_ts"].notna() & df["expiry_ts"].notna()].copy()
    df["listed_date"] = df["listed_ts"].dt.date
    df["expiry_date"] = df["expiry_ts"].dt.date

    df["company_id"] = to_int(df["company_id"])
    df["company_name_norm"] = clean_text(df["company_name_norm"])
    df["location_state"] = df["location_state"].fillna("Unknown")
    df["views_count"] = to_int(df["views"])
    df["applies_count"] = to_int(df["applies"])
    df["salary_min_annual_usd"] = pd.to_numeric(
        df["salary_min_annual_usd"], errors="coerce")
    df["salary_max_annual_usd"] = pd.to_numeric(
        df["salary_max_annual_usd"], errors="coerce")
    df["salary_disclosed"] = df["salary_disclosed"].map(
        {"True": 1, "False": 0, "1": 1, "0": 0}).astype("Int64")
    df["salary_valid"] = to_int(df["salary_valid"])
    df["days_listed"] = to_int(df["days_listed"])
    return df


def link_companies(postings, dim_company):
    """Tautkan postings ke dim_company; mengembalikan Series company_key.

    Aturan (sesuai build Oktober, terverifikasi 0 selisih pada 123.849 baris):
    1) company_id cocok -> kunci perusahaan itu;
    2) fallback company_name_norm (kemunculan pertama di dim); nilai kosong
       pada kedua sisi dianggap cocok, sehingga lowongan tanpa nama
       perusahaan tertaut ke perusahaan tanpa nama di companies_clean;
    3) tidak tertaut sama sekali -> Unknown (company_key 1).
    """
    by_id = dim_company.dropna(subset=["company_id"]).set_index(
        "company_id")["company_key"]
    key = postings["company_id"].map(by_id)

    missing = key.isna()
    if missing.any():
        first_by_norm = dim_company.assign(
            _norm=dim_company["name_norm"].fillna("\x00NA\x00")).drop_duplicates(
                subset=["_norm"], keep="first").set_index(
                    "_norm")["company_key"]
        norms = postings.loc[missing, "company_name_norm"].fillna("\x00NA\x00")
        key.loc[missing] = norms.map(first_by_norm)
    key = key.fillna(1).astype("int64")
    return key


def build_fact_posting(postings, dim_company, dim_location, dim_date,
                       dim_profile):
    """Rakit fact_posting dari postings yang sudah tertaut ke dimensi."""
    df = postings.copy()
    df["company_key"] = link_companies(df, dim_company)

    df = df.merge(dim_location[["city", "state", "location_key"]],
                  left_on=["location_city", "location_state"],
                  right_on=["city", "state"], how="left").drop(
                      columns=["city", "state"])
    prof_cols = ["experience_level", "work_type", "remote_allowed",
                 "sponsored", "application_type"]
    df = df.merge(dim_profile[prof_cols + ["job_profile_key"]],
                  on=prof_cols, how="left")

    valid_dates = set(dim_date["full_date"])
    df["listed_date_key"] = [int(d.strftime("%Y%m%d"))
                             for d in df["listed_date"]]
    df["expiry_date_key"] = [int(d.strftime("%Y%m%d"))
                             for d in df["expiry_date"]]
    assert set(df["listed_date"]).issubset(valid_dates)
    assert set(df["expiry_date"]).issubset(valid_dates)
    assert df["location_key"].notna().all()
    assert df["job_profile_key"].notna().all()

    cols = ["job_id", "company_key", "location_key", "job_profile_key",
            "listed_date_key", "expiry_date_key", "views_count",
            "applies_count", "salary_min_annual_usd", "salary_max_annual_usd",
            "salary_disclosed", "salary_valid", "days_listed"]
    return df[cols]


def attach_profile_attrs(postings, dataset):
    """Tempel atribut profil (dari dataset_clean) ke postings per job_id.

    postings_clean juga punya kolom work_type (enum FULL_TIME),
    remote_allowed, dan application_type; nilai tampilan pada dimensi
    berasal dari dataset_clean, jadi kolom postings yang bertabrakan
    dibuang dulu sebelum merge.
    """
    attrs = dataset[["job_id", "experience_level", "work_type",
                     "remote_allowed", "application_type"]].copy()
    attrs["job_id"] = to_int(attrs["job_id"])
    base = postings.drop(columns=["work_type", "remote_allowed",
                                  "application_type"], errors="ignore")
    out = base.merge(attrs, on="job_id", how="left")
    out["sponsored"] = to_int(out["sponsored"])
    return out


def build_skill_fact(pairs, dim, key_cols, job_ids, source, quarantine):
    """Rakit fakta pasangan (job_id, skill_key); pasangan yatim di-quarantine.

    pairs: DataFrame sumber pasangan; dim: dimensi skill; key_cols: kolom
    pada pairs dan dim yang menjadi kunci alami (['skill_abr','skill_name']
    atau ['skill']).
    """
    df = pairs.copy()
    df["job_id"] = to_int(df["job_id"])
    dim_lookup = dim.set_index(key_cols)["skill_key"]
    if key_cols == ["skill"]:
        keys = df["skill"].map(dim_lookup)
    else:
        keys = df.set_index(key_cols).index.map(dim_lookup.get)
        keys = pd.Series(keys, index=df.index)
    df["skill_key"] = keys
    orphan_job = ~df["job_id"].isin(job_ids)
    orphan_skill = df["skill_key"].isna()
    for _, r in df[orphan_job | orphan_skill].iterrows():
        reason = ("job_id tidak ada di fact_posting" if orphan_job.loc[r.name]
                  else "skill tidak ada di dimensi")
        quarantine.add(source, r["job_id"], reason)
    df = df[~orphan_job & ~orphan_skill]
    out = df[["job_id", "skill_key"]].drop_duplicates()
    out["skill_key"] = out["skill_key"].astype("int64")
    return out


def build_benefit(source_dir, fact_job_ids, quarantine):
    """Muat benefit bila file opsional job_benefits.csv tersedia.

    Mengembalikan (dim_benefit, fact_posting_benefit); keduanya None bila
    file sumber tidak ada (kondisi saat ini: benefit tidak ikut diekspor
    ke CSV hasil cleaning).
    """
    path = os.path.join(source_dir, "job_benefits.csv")
    if not os.path.exists(path):
        return None, None
    raw = pd.read_csv(path, dtype=str)
    types = raw["benefit_type"].drop_duplicates().reset_index(drop=True)
    dim = pd.DataFrame({"benefit_key": range(1, len(types) + 1),
                        "benefit_type": types})
    key = dim.set_index("benefit_type")["benefit_key"]
    fact = raw.copy()
    fact["job_id"] = to_int(fact["job_id"])
    fact["benefit_key"] = fact["benefit_type"].map(key).astype("int64")
    fact["is_inferred"] = to_int(fact["is_inferred"])
    ok = fact["job_id"].isin(fact_job_ids)
    for _, r in fact[~ok].iterrows():
        quarantine.add("job_benefits", r["job_id"],
                       "job_id tidak ada di fact_posting")
    fact = fact[ok][["job_id", "benefit_key", "is_inferred"]]
    return dim, fact.drop_duplicates()


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def create_dw_schema(engine):
    with engine.begin() as conn:
        for stmt in DDL_STATEMENTS:
            conn.execute(text(stmt))


def truncate_dw(engine):
    with engine.begin() as conn:
        conn.execute(text(
            "TRUNCATE dw_lowongan." + ", dw_lowongan.".join(DW_TABLES)))


def load_full(engine, frames, source_dir, cutoff, quarantine):
    """Load penuh: bangun semua dimensi dan fakta dari staging.

    cutoff (opsional) menahan lowongan dengan listed_date sesudah tanggal
    itu, untuk simulasi load parsial yang nanti dilengkapi incremental.
    """
    log.info("TRANSFORM + LOAD (full%s)", f", cutoff {cutoff}" if cutoff else "")
    postings = prepare_postings(frames["stg_postings"], quarantine)
    if cutoff:
        postings = postings[postings["listed_date"] <= cutoff]
    postings = attach_profile_attrs(postings, frames["stg_dataset"])
    log.info("  postings dimuat: %d", len(postings))

    dim_company = build_dim_company(frames["stg_companies"])
    dim_location = location_frame(postings)
    dim_date = date_frame(pd.concat([postings["listed_date"],
                                     postings["expiry_date"]]))
    dim_profile = profile_frame(postings)
    dim_skill = skill_frame(frames["stg_posting_skills"])
    dim_skill_nlp = skill_nlp_frame(frames["stg_skill_dictionary"])

    fact = build_fact_posting(postings, dim_company, dim_location, dim_date,
                              dim_profile)
    job_ids = set(fact["job_id"])
    fact_skill = build_skill_fact(
        frames["stg_posting_skills"], dim_skill,
        ["skill_abr", "skill_name"], job_ids, "posting_skills_clean",
        quarantine)
    fact_skill_nlp = build_skill_fact(
        frames["stg_posting_skills_nlp"].rename(columns={"skill": "skill"}),
        dim_skill_nlp.rename(columns={"skill_name": "skill"}),
        ["skill"], job_ids, "posting_skills_nlp", quarantine)
    fact_skill_nlp = fact_skill_nlp[["job_id", "skill_key"]]
    dim_benefit, fact_benefit = build_benefit(source_dir, job_ids, quarantine)

    truncate_dw(engine)
    with engine.begin() as conn:
        bulk_load(conn, dim_company, "dw_lowongan", "dim_company")
        bulk_load(conn, dim_location, "dw_lowongan", "dim_location")
        bulk_load(conn, dim_date, "dw_lowongan", "dim_date")
        bulk_load(conn, dim_profile, "dw_lowongan", "dim_job_profile")
        bulk_load(conn, dim_skill, "dw_lowongan", "dim_skill")
        bulk_load(conn, dim_skill_nlp, "dw_lowongan", "dim_skill_nlp")
        if dim_benefit is not None:
            bulk_load(conn, dim_benefit, "dw_lowongan", "dim_benefit")
        bulk_load(conn, fact, "dw_lowongan", "fact_posting")
        bulk_load(conn, fact_skill, "dw_lowongan", "fact_posting_skill")
        bulk_load(conn, fact_skill_nlp, "dw_lowongan",
                  "fact_posting_skill_nlp")
        if fact_benefit is not None:
            bulk_load(conn, fact_benefit, "dw_lowongan",
                      "fact_posting_benefit")
    if dim_benefit is None:
        log.warning("  SUMBER BENEFIT TIDAK ADA: job_benefits.csv tidak "
                    "ditemukan di folder sumber. dim_benefit dan "
                    "fact_posting_benefit dibiarkan kosong (0 baris). "
                    "Tidak ada CSV hasil cleaning yang memuat benefit per "
                    "lowongan, jadi kedua tabel tidak dapat diturunkan "
                    "dari sumber yang tersedia.")
    return len(postings)


def load_incremental(engine, frames, source_dir, cutoff, quarantine):
    """Load incremental: hanya lowongan listed_date > cutoff yang belum ada.

    Anggota dimensi baru (perusahaan, lokasi, profil, tanggal) ditambahkan
    dengan kunci berikutnya. Menjalankan ulang perintah yang sama tidak
    menambah apa pun (idempotent).
    """
    log.info("TRANSFORM + LOAD (incremental, cutoff %s)", cutoff)
    with engine.connect() as conn:
        existing = pd.read_sql_query(
            text("SELECT job_id FROM dw_lowongan.fact_posting"), conn)
        dim_company = pd.read_sql_query(
            text("SELECT * FROM dw_lowongan.dim_company"), conn)
        dim_location = pd.read_sql_query(
            text("SELECT * FROM dw_lowongan.dim_location"), conn)
        dim_date = pd.read_sql_query(
            text("SELECT * FROM dw_lowongan.dim_date"), conn)
        dim_profile = pd.read_sql_query(
            text("SELECT * FROM dw_lowongan.dim_job_profile"), conn)
        dim_skill = pd.read_sql_query(
            text("SELECT * FROM dw_lowongan.dim_skill"), conn)
        dim_skill_nlp = pd.read_sql_query(
            text("SELECT * FROM dw_lowongan.dim_skill_nlp"), conn)
    if existing.empty:
        raise RuntimeError("fact_posting masih kosong; jalankan --mode full "
                           "terlebih dahulu.")
    existing_ids = set(existing["job_id"])

    postings = prepare_postings(frames["stg_postings"], quarantine)
    postings = postings[(postings["listed_date"] > cutoff)
                        & (~postings["job_id"].isin(existing_ids))]
    postings = attach_profile_attrs(postings, frames["stg_dataset"])
    log.info("  postings baru: %d", len(postings))
    if postings.empty:
        return 0

    # Perusahaan baru dari file companies (belum ada di dimensi).
    full_company = build_dim_company(frames["stg_companies"])
    known_ids = set(dim_company["company_id"].dropna())
    new_company = full_company[
        ~full_company["company_id"].isin(known_ids)
        & (full_company["company_key"] != 1)].copy()
    if not new_company.empty:
        start = int(dim_company["company_key"].max()) + 1
        new_company["company_key"] = range(start, start + len(new_company))
        dim_company = pd.concat([dim_company, new_company],
                                ignore_index=True)
    else:
        new_company = None

    # Lokasi baru dari postings baru.
    cand_loc = location_frame(postings)
    known_loc = set(zip(dim_location["city"], dim_location["state"]))
    new_loc = cand_loc[[(c, s) not in known_loc for c, s in zip(
        cand_loc["city"], cand_loc["state"])]].copy()
    if not new_loc.empty:
        start = int(dim_location["location_key"].max()) + 1
        new_loc["location_key"] = range(start, start + len(new_loc))
        dim_location = pd.concat([dim_location, new_loc],
                                 ignore_index=True)
    else:
        new_loc = None

    # Profil baru dari postings baru.
    cand_prof = profile_frame(postings)
    prof_cols = ["experience_level", "work_type", "remote_allowed",
                 "sponsored", "application_type"]
    known_prof = set(map(tuple, dim_profile[prof_cols].astype(str).values))
    new_prof = cand_prof[[tuple(r) not in known_prof for r in cand_prof[
        prof_cols].astype(str).values]].copy()
    if not new_prof.empty:
        start = int(dim_profile["job_profile_key"].max()) + 1
        new_prof["job_profile_key"] = range(start, start + len(new_prof))
        dim_profile = pd.concat([dim_profile, new_prof], ignore_index=True)
    else:
        new_prof = None

    # Tanggal: rentang kalender diperluas kontinu sampai tanggal terjauh
    # yang dibutuhkan postings baru (listed maupun expiry).
    need_max = max(postings["listed_date"].max(), postings["expiry_date"].max())
    cur_min = min(dim_date["full_date"])
    cur_max = max(dim_date["full_date"])
    new_date = None
    if need_max > cur_max:
        new_date = date_frame(pd.concat([
            pd.Series([cur_min, need_max])]))
        new_date = new_date[new_date["full_date"] > cur_max]
        dim_date = pd.concat([dim_date, new_date], ignore_index=True)

    fact = build_fact_posting(postings, dim_company, dim_location, dim_date,
                              dim_profile)
    job_ids = set(fact["job_id"])
    all_ids = existing_ids | job_ids
    fact_skill = build_skill_fact(
        frames["stg_posting_skills"], dim_skill,
        ["skill_abr", "skill_name"], all_ids, "posting_skills_clean",
        quarantine)
    fact_skill = fact_skill[fact_skill["job_id"].isin(job_ids)]
    fact_skill_nlp = build_skill_fact(
        frames["stg_posting_skills_nlp"],
        dim_skill_nlp.rename(columns={"skill_name": "skill"}),
        ["skill"], all_ids, "posting_skills_nlp", quarantine)
    fact_skill_nlp = fact_skill_nlp[fact_skill_nlp["job_id"].isin(job_ids)][
        ["job_id", "skill_key"]]
    dim_benefit_new, fact_benefit = build_benefit(
        source_dir, all_ids, quarantine)
    if fact_benefit is not None:
        fact_benefit = fact_benefit[fact_benefit["job_id"].isin(job_ids)]

    with engine.begin() as conn:
        if new_company is not None:
            bulk_load(conn, new_company, "dw_lowongan", "dim_company")
        if new_loc is not None:
            bulk_load(conn, new_loc, "dw_lowongan", "dim_location")
        if new_date is not None:
            bulk_load(conn, new_date, "dw_lowongan", "dim_date")
        if new_prof is not None:
            bulk_load(conn, new_prof, "dw_lowongan", "dim_job_profile")
        bulk_load(conn, fact, "dw_lowongan", "fact_posting")
        bulk_load(conn, fact_skill, "dw_lowongan", "fact_posting_skill")
        bulk_load(conn, fact_skill_nlp, "dw_lowongan",
                  "fact_posting_skill_nlp")
        if fact_benefit is not None:
            bulk_load(conn, fact_benefit, "dw_lowongan",
                      "fact_posting_benefit")
    if dim_benefit_new is None:
        log.warning("  SUMBER BENEFIT TIDAK ADA: fact_posting_benefit "
                    "tidak ditambah (lihat catatan pada mode full).")
    return len(postings)


# ---------------------------------------------------------------------------
# Validasi akhir
# ---------------------------------------------------------------------------

ORPHAN_CHECKS = {
    "fact_posting.company_key": (
        "SELECT COUNT(*) FROM dw_lowongan.fact_posting f "
        "LEFT JOIN dw_lowongan.dim_company d "
        "ON d.company_key = f.company_key "
        "WHERE f.company_key IS NOT NULL AND d.company_key IS NULL"),
    "fact_posting.location_key": (
        "SELECT COUNT(*) FROM dw_lowongan.fact_posting f "
        "LEFT JOIN dw_lowongan.dim_location d "
        "ON d.location_key = f.location_key "
        "WHERE f.location_key IS NOT NULL AND d.location_key IS NULL"),
    "fact_posting.job_profile_key": (
        "SELECT COUNT(*) FROM dw_lowongan.fact_posting f "
        "LEFT JOIN dw_lowongan.dim_job_profile d "
        "ON d.job_profile_key = f.job_profile_key "
        "WHERE f.job_profile_key IS NOT NULL AND d.job_profile_key IS NULL"),
    "fact_posting.listed_date_key": (
        "SELECT COUNT(*) FROM dw_lowongan.fact_posting f "
        "LEFT JOIN dw_lowongan.dim_date d "
        "ON d.date_key = f.listed_date_key "
        "WHERE f.listed_date_key IS NOT NULL AND d.date_key IS NULL"),
    "fact_posting.expiry_date_key": (
        "SELECT COUNT(*) FROM dw_lowongan.fact_posting f "
        "LEFT JOIN dw_lowongan.dim_date d "
        "ON d.date_key = f.expiry_date_key "
        "WHERE f.expiry_date_key IS NOT NULL AND d.date_key IS NULL"),
    "fact_posting_skill.job_id": (
        "SELECT COUNT(*) FROM dw_lowongan.fact_posting_skill f "
        "LEFT JOIN dw_lowongan.fact_posting p ON p.job_id = f.job_id "
        "WHERE p.job_id IS NULL"),
    "fact_posting_skill.skill_key": (
        "SELECT COUNT(*) FROM dw_lowongan.fact_posting_skill f "
        "LEFT JOIN dw_lowongan.dim_skill d ON d.skill_key = f.skill_key "
        "WHERE d.skill_key IS NULL"),
    "fact_posting_skill_nlp.job_id": (
        "SELECT COUNT(*) FROM dw_lowongan.fact_posting_skill_nlp f "
        "LEFT JOIN dw_lowongan.fact_posting p ON p.job_id = f.job_id "
        "WHERE p.job_id IS NULL"),
    "fact_posting_skill_nlp.skill_key": (
        "SELECT COUNT(*) FROM dw_lowongan.fact_posting_skill_nlp f "
        "LEFT JOIN dw_lowongan.dim_skill_nlp d "
        "ON d.skill_key = f.skill_key WHERE d.skill_key IS NULL"),
    "fact_posting_benefit.job_id": (
        "SELECT COUNT(*) FROM dw_lowongan.fact_posting_benefit f "
        "LEFT JOIN dw_lowongan.fact_posting p ON p.job_id = f.job_id "
        "WHERE p.job_id IS NULL"),
    "fact_posting_benefit.benefit_key": (
        "SELECT COUNT(*) FROM dw_lowongan.fact_posting_benefit f "
        "LEFT JOIN dw_lowongan.dim_benefit d "
        "ON d.benefit_key = f.benefit_key WHERE d.benefit_key IS NULL"),
}


def validate(engine, quarantine, mode=None, cutoff=None,
             staging_counts=None):
    """Cetak dan log hasil validasi, tulis validation_report.md.

    Mengembalikan jumlah orphan FK total. Laporan Markdown berisi tabel
    target vs tercapai per tabel dan pemeriksaan rekonsiliasi; file ini
    menjadi bahan Lampiran 5 laporan UAS (Log ETL + Validasi).
    """
    log.info("VALIDASI AKHIR")
    total = 0
    orphans = 0
    counts = {}
    orphan_detail = {}
    with engine.connect() as conn:
        for table in DW_TABLES:
            n = conn.execute(text(
                f"SELECT COUNT(*) FROM dw_lowongan.{table}")).scalar()
            counts[table] = n
            total += n
            log.info("  %-28s %8d baris", table, n)
        log.info("  %-28s %8d baris", "TOTAL", total)
        valid, npost = conn.execute(text(
            "SELECT SUM(CASE WHEN salary_valid = 1 THEN 1 ELSE 0 END), "
            "COUNT(*) FROM dw_lowongan.fact_posting")).fetchone()
        log.info("  salary_valid = 1: %d dari %d (%.1f%%)",
                 valid, npost, 100.0 * valid / npost)
        nb, ninf = conn.execute(text(
            "SELECT COUNT(*), SUM(CASE WHEN is_inferred = 1 THEN 1 ELSE 0 "
            "END) FROM dw_lowongan.fact_posting_benefit")).fetchone()
        if nb:
            log.info("  benefit is_inferred: %d dari %d (%.1f%%)",
                     ninf, nb, 100.0 * ninf / nb)
        else:
            log.warning("  benefit: 0 baris (sumber benefit tidak tersedia "
                        "di CSV hasil cleaning)")
        for name, sql in ORPHAN_CHECKS.items():
            n = conn.execute(text(sql)).scalar()
            orphan_detail[name] = n
            orphans += n
            log.info("  orphan %-32s %d", name, n)
    log.info("  baris masuk quarantine pada run ini: %d", len(quarantine))
    write_validation_report(engine, mode, cutoff, counts, total, valid,
                            npost, nb, ninf, orphan_detail, orphans,
                            quarantine, staging_counts)
    return orphans


def _status(ok):
    return "Sesuai" if ok else "Tidak sesuai"


def _pct(x):
    """Format persen dengan koma desimal (gaya Indonesia): 23,7%."""
    return f"{x:.1f}".replace(".", ",") + "%"


def write_validation_report(engine, mode, cutoff, counts, total, valid,
                            npost, nb, ninf, orphan_detail, orphans,
                            quarantine, staging_counts):
    """Tulis validation_report.md (target vs tercapai) di folder script."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = ["# Laporan Validasi ETL Data Warehouse KarirKu", "",
             f"- Waktu run: {now}",
             f"- Mode: {mode}" + (f" (cutoff {cutoff})" if cutoff else ""),
             f"- Database: {engine.url.database}",
             f"- Skema: staging -> dw_lowongan", "",
             "## Jumlah baris per tabel", "",
             "| Tabel | Target | Tercapai | Status |",
             "|---|---:|---:|---|"]
    for table in DW_TABLES:
        lines.append(f"| {table} | {TARGETS[table]} | {counts[table]} | "
                     f"{_status(counts[table] == TARGETS[table])} |")
    lines.append(f"| **Total** | **{TOTAL_TARGET}** | **{total}** | "
                 f"**{_status(total == TOTAL_TARGET)}** |")
    lines += ["", "## Pemeriksaan rekonsiliasi", "",
              "| Pemeriksaan | Target | Tercapai | Status |",
              "|---|---:|---:|---|"]
    pct_valid = 100.0 * valid / npost if npost else 0.0
    lines.append(
        f"| Lowongan bergaji valid (salary_valid = 1) | "
        f"{SALARY_VALID_TARGET} (23,7%) | {valid} "
        f"({_pct(pct_valid)}) | {_status(valid == SALARY_VALID_TARGET)} |")
    if nb:
        pct_inf = 100.0 * ninf / nb
        lines.append(
            f"| Benefit inferred (is_inferred = 1) | 59,1% | "
            f"{_pct(pct_inf)} ({ninf} dari {nb}) | "
            f"{_status(abs(pct_inf - INFERRED_PCT_TARGET) < 0.05)} |")
    else:
        lines.append(
            "| Benefit inferred (is_inferred = 1) | 59,1% | 0 baris benefit "
            "| Tidak tercapai, sumber benefit tidak tersedia |")
    lines.append(
        f"| Orphan foreign key (total 11 pemeriksaan) | 0 | {orphans} | "
        f"{_status(orphans == 0)} |")
    if staging_counts:
        lines.append(
            f"| Baris staging postings (stg_postings) | - | "
            f"{staging_counts.get('stg_postings', 0)} | - |")
        lines.append(
            f"| Baris staging pasangan skill (stg_posting_skills) | - | "
            f"{staging_counts.get('stg_posting_skills', 0)} | - |")
        lines.append(
            f"| Baris staging pasangan skill NLP "
            f"(stg_posting_skills_nlp) | - | "
            f"{staging_counts.get('stg_posting_skills_nlp', 0)} | - |")
    lines.append(
        f"| Baris masuk quarantine pada run ini | 0 | {len(quarantine)} | "
        f"{_status(len(quarantine) == 0)} |")
    lines += ["", "## Orphan foreign key per pemeriksaan", "",
              "| Pemeriksaan | Target | Tercapai | Status |",
              "|---|---:|---:|---|"]
    for name, n in orphan_detail.items():
        lines.append(f"| {name} | 0 | {n} | {_status(n == 0)} |")
    lines += ["", "## Catatan", ""]
    if counts["fact_posting_benefit"] == 0:
        lines.append(
            "- dim_benefit dan fact_posting_benefit kosong karena tidak "
            "ada CSV hasil cleaning yang memuat benefit per lowongan; "
            "kedua tabel hanya dapat diturunkan bila file opsional "
            "job_benefits.csv tersedia di folder sumber. Selisih total "
            "baris terhadap target berasal dari kedua tabel ini.")
    if mode == "incremental":
        lines.append(
            "- Mode incremental: fact_posting adalah akumulasi load full "
            "dan incremental, sehingga jumlahnya dapat melebihi baris "
            "staging pada run ini.")
    if cutoff and mode == "full":
        lines.append(
            f"- Mode full dengan cutoff {cutoff}: lowongan dengan "
            "listed_date sesudah cutoff sengaja ditahan untuk dilengkapi "
            "pada run incremental, sehingga target belum tercapai pada "
            "run ini.")
    lines.append(
        "- Target adalah jumlah baris build Oktober yang terverifikasi "
        "pada dump dw_lowongan_pg16.sql.")
    path = os.path.join(SCRIPT_DIR, "validation_report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    log.info("  Laporan validasi ditulis: %s", path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="ETL Data Warehouse KarirKu (full / incremental).")
    p.add_argument("--mode", choices=["full", "incremental"], required=True)
    p.add_argument("--cutoff", help="Tanggal YYYY-MM-DD. Pada mode full: "
                   "tahan lowongan listed sesudah tanggal ini. Pada mode "
                   "incremental (wajib): muat lowongan listed sesudah "
                   "tanggal ini.")
    p.add_argument("--database", help="Nama database tujuan (mengganti "
                   "nama database pada DATABASE_URL).")
    p.add_argument("--source-dir", default=DEFAULT_SOURCE_DIR,
                   help="Folder CSV hasil cleaning.")
    args = p.parse_args(argv)
    if args.mode == "incremental" and not args.cutoff:
        p.error("--mode incremental membutuhkan --cutoff")
    cutoff = None
    if args.cutoff:
        cutoff = datetime.strptime(args.cutoff, "%Y-%m-%d").date()
    return args, cutoff


def main(argv=None):
    args, cutoff = parse_args(argv)
    setup_logging()
    from sqlalchemy.engine.url import make_url
    url = make_url(os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))
    if args.database:
        url = url.set(database=args.database)
    engine = create_engine(url)
    log.info("ETL KarirKu mulai: mode=%s database=%s",
             args.mode, engine.url.database)
    quarantine = Quarantine()
    try:
        create_dw_schema(engine)
        extract(engine, args.source_dir, quarantine)
        frames = read_staging(engine)
        if args.mode == "full":
            load_full(engine, frames, args.source_dir, cutoff, quarantine)
        else:
            load_incremental(engine, frames, args.source_dir, cutoff,
                             quarantine)
        staging_counts = {t: len(frames[t]) for t in SOURCE_FILES}
        orphans = validate(engine, quarantine, mode=args.mode,
                           cutoff=cutoff, staging_counts=staging_counts)
    except Exception:
        log.exception("ETL GAGAL")
        quarantine.write()
        return 1
    path = quarantine.write()
    log.info("File quarantine: %s (%d baris)", path, len(quarantine))
    if orphans:
        log.error("VALIDASI GAGAL: ditemukan %d orphan foreign key", orphans)
        return 2
    log.info("ETL selesai tanpa orphan foreign key.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
