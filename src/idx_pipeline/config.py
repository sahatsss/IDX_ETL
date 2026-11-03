"""Konfigurasi dari environment (.env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

TICKERS_CSV = ROOT / "config" / "tickers.csv"


def database_url() -> str:
    """URL koneksi SQLAlchemy.

    - DATABASE_URL (jika di-set) dipakai apa adanya: database cloud (Neon), GitHub Actions, Streamlit Cloud.
      Format dari penyedia biasanya `postgresql://...?sslmode=require`; awalannya diubah ke driver psycopg2.
    - Jika tidak di-set, URL disusun dari POSTGRES_* (database lokal Docker).
    """
    url = os.getenv("DATABASE_URL")
    if url:
        for awalan in ("postgres://", "postgresql://"):
            if url.startswith(awalan):
                return "postgresql+psycopg2://" + url[len(awalan):]
        return url
    user = os.getenv("POSTGRES_USER", "idx")
    pw = os.getenv("POSTGRES_PASSWORD", "idx")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "idx")
    return f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}"
