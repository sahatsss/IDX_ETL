from idx_pipeline import config


def test_tanpa_database_url_memakai_postgres_lokal(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    assert config.database_url().startswith("postgresql+psycopg2://")
    assert "@localhost:" in config.database_url()


def test_database_url_dari_penyedia_diubah_ke_driver_psycopg2(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@ep-x.neon.tech/idx?sslmode=require")
    assert config.database_url() == "postgresql+psycopg2://u:p@ep-x.neon.tech/idx?sslmode=require"


def test_awalan_postgres_lama_juga_diterima(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@host/db")
    assert config.database_url() == "postgresql+psycopg2://u:p@host/db"
