"""Konfigurasi dari environment (.env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

TICKERS_CSV = ROOT / "config" / "tickers.csv"


def database_url() -> str:
    user = os.getenv("POSTGRES_USER", "idx")
    pw = os.getenv("POSTGRES_PASSWORD", "idx")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "idx")
    return f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}"
