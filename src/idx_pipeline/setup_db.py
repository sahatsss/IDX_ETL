"""CLI: python -m idx_pipeline.setup_db

Membuat tabel (sql/schema/*.sql) lalu view analitik (sql/analytics/*.sql) di database tujuan
(DATABASE_URL atau POSTGRES_*). Aman dijalankan berulang: skema memakai CREATE TABLE IF NOT EXISTS,
view memakai CREATE OR REPLACE VIEW.

Di Docker lokal skema dibuat otomatis saat volume pertama kali dibuat; script ini dibutuhkan untuk
database yang tidak dibuat lewat Docker (mis. database cloud) dan untuk memperbarui view.
"""
import logging

from sqlalchemy import create_engine

from . import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("idx_pipeline")

FOLDER_SQL = [config.ROOT / "sql" / "schema", config.ROOT / "sql" / "analytics"]


def jalankan() -> None:
    engine = create_engine(config.database_url())
    log.info("database tujuan: %s", engine.url.render_as_string(hide_password=True))
    conn = engine.raw_connection()
    try:
        with conn.cursor() as cur:
            for folder in FOLDER_SQL:
                # Urutan nama file penting: 03 dan 05 memakai view dari 01.
                for file in sorted(folder.glob("*.sql")):
                    log.info("menjalankan %s", file.relative_to(config.ROOT))
                    cur.execute(file.read_text(encoding="utf-8"))
        conn.commit()      # semua file berhasil, atau tidak ada perubahan sama sekali
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    log.info("selesai")


if __name__ == "__main__":
    jalankan()
