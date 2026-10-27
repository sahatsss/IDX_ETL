"""Koneksi database untuk dashboard. Semua halaman membaca data lewat `query()`."""
import sys
from decimal import Decimal
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

# Pakai ulang konfigurasi koneksi milik pipeline ETL (src/idx_pipeline/config.py),
# supaya dashboard dan ETL selalu membaca database yang sama dari .env.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from idx_pipeline import config  # noqa: E402

CACHE_DETIK = 600   # data harian hanya berubah sekali sehari; cache 10 menit cukup


@st.cache_resource
def engine():
    """Satu engine (connection pool) untuk seluruh sesi dashboard."""
    return create_engine(config.database_url(), pool_pre_ping=True)


@st.cache_data(ttl=CACHE_DETIK, show_spinner=False)
def query(sql: str, **params) -> pd.DataFrame:
    """Jalankan SELECT dan kembalikan DataFrame. Hasil di-cache berdasarkan teks SQL + parameter."""
    with engine().connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)
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


def persen(x: float, desimal: int = 1) -> str:
    return "–" if pd.isna(x) else f"{x * 100:+.{desimal}f}%"
