"""Koneksi database untuk dashboard. Semua halaman membaca data lewat `query()`."""
import os
import sys
from decimal import Decimal
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Pakai ulang konfigurasi koneksi milik pipeline ETL (src/idx_pipeline/config.py),
# supaya dashboard dan ETL selalu membaca database yang sama dari .env.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from idx_pipeline import config  # noqa: E402

CACHE_DETIK = 600   # data harian hanya berubah sekali sehari; cache 10 menit cukup


def _ambil_secret_streamlit() -> None:
    """Di Streamlit Community Cloud, DATABASE_URL disimpan di Secrets. Salin ke environment
    agar config.database_url() membacanya, walaupun Streamlit tidak mengekspornya sebagai env var."""
    if os.getenv("DATABASE_URL"):
        return
    try:
        if "DATABASE_URL" in st.secrets:
            os.environ["DATABASE_URL"] = st.secrets["DATABASE_URL"]
    except Exception:       # lokal tanpa .streamlit/secrets.toml: tetap pakai .env / POSTGRES_*
        pass


@st.cache_resource
def engine():
    """Satu engine (connection pool) untuk seluruh sesi dashboard."""
    _ambil_secret_streamlit()
    return create_engine(config.database_url(), pool_pre_ping=True)


def _host_tujuan() -> str:
    return engine().url.host or "?"


@st.cache_data(ttl=CACHE_DETIK, show_spinner=False)
def _query(sql: str, **params) -> pd.DataFrame:
    with engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def query(sql: str, **params) -> pd.DataFrame:
    """Jalankan SELECT dan kembalikan DataFrame. Hasil di-cache berdasarkan teks SQL + parameter."""
    try:
        df = _query(sql, **params).copy()
    except OperationalError as e:
        # Pesan singkat tanpa membocorkan password: host + baris pertama pesan driver
        # (mis. "... failed: FATAL: password authentication failed"); pesan psycopg2 tidak memuat password.
        baris = [b.strip() for b in str(getattr(e, "orig", e)).splitlines() if b.strip()]
        st.error(f"Tidak bisa terhubung ke database (host: `{_host_tujuan()}`). "
                 "Periksa DATABASE_URL di Secrets / .env, dan pastikan database menyala.")
        if baris:
            st.caption(f"Detail: {baris[0]}")
        st.stop()
    # Kolom NUMERIC PostgreSQL terbaca sebagai Decimal (dtype object); ubah ke float agar bisa digrafikkan.
    for kolom in df.columns:
        contoh = df[kolom].dropna()
        if not contoh.empty and isinstance(contoh.iloc[0], Decimal):
            df[kolom] = df[kolom].astype(float)
    return df


def daftar_emiten() -> pd.DataFrame:
    return query("SELECT kode, nama, sektor FROM emiten ORDER BY kode")


def label_emiten(df_emiten: pd.DataFrame) -> dict[str, str]:
    """{kode: 'KODE · Nama'} untuk selectbox."""
    return {r.kode: f"{r.kode} · {r.nama or ''}" for r in df_emiten.itertuples()}
