"""Memuat data ke PostgreSQL secara idempotent (upsert)."""
import pandas as pd
from psycopg2.extras import execute_values
from sqlalchemy import text
from sqlalchemy.engine import Engine

# Dipakai dengan psycopg2 execute_values: `VALUES %s` diganti banyak baris sekaligus,
# (..), (..), ... sebanyak UKURAN_HALAMAN per perintah, bukan satu perintah per baris.
KOLOM_HARGA = ["kode", "tanggal", "harga_buka", "harga_tertinggi", "harga_terendah", "harga_tutup", "volume"]
UKURAN_HALAMAN = 1000
UPSERT_HARGA = f"""
    INSERT INTO harga_harian ({", ".join(KOLOM_HARGA)})
    VALUES %s
    ON CONFLICT (kode, tanggal) DO UPDATE SET
        harga_buka      = EXCLUDED.harga_buka,
        harga_tertinggi = EXCLUDED.harga_tertinggi,
        harga_terendah  = EXCLUDED.harga_terendah,
        harga_tutup     = EXCLUDED.harga_tutup,
        volume          = EXCLUDED.volume,
        dimuat_pada     = now()
"""

UPSERT_EMITEN = text("""
    INSERT INTO emiten (kode, nama, sektor) VALUES (:kode, :nama, :sektor)
    ON CONFLICT (kode) DO UPDATE SET
        nama   = COALESCE(EXCLUDED.nama, emiten.nama),
        sektor = COALESCE(EXCLUDED.sektor, emiten.sektor)
""")

INSERT_ISU = text("""
    INSERT INTO data_quality_issue (run_id, kode, tanggal, aturan, keterangan)
    VALUES (:run_id, :kode, :tanggal, :aturan, :keterangan)
""")


def _nullable(df: pd.DataFrame) -> list[dict]:
    """Ubah NaN menjadi None agar tersimpan sebagai NULL."""
    return df.astype(object).where(pd.notna(df), None).to_dict("records")


def muat_emiten(engine: Engine, emiten: pd.DataFrame) -> None:
    with engine.begin() as conn:
        conn.execute(UPSERT_EMITEN, _nullable(emiten[["kode", "nama", "sektor"]]))


def muat_harga(engine: Engine, df: pd.DataFrame) -> int:
    """Upsert seluruh baris dalam satu transaksi, dikirim per halaman UKURAN_HALAMAN baris.

    Syarat: tidak boleh ada (kode, tanggal) ganda dalam satu batch. PostgreSQL menolak ON CONFLICT DO UPDATE
    yang mengenai baris yang sama dua kali dalam satu perintah. Aturan `duplikat` di validate.py menjamin ini.
    """
    if df.empty:
        return 0
    baris = [tuple(b[k] for k in KOLOM_HARGA) for b in _nullable(df[KOLOM_HARGA])]
    # execute_values adalah fitur psycopg2, jadi pakai koneksi DBAPI mentah di bawah engine SQLAlchemy.
    conn = engine.raw_connection()
    try:
        with conn.cursor() as cur:
            execute_values(cur, UPSERT_HARGA, baris, page_size=UKURAN_HALAMAN)
        conn.commit()          # semua halaman masuk, atau...
    except Exception:
        conn.rollback()        # ...tidak ada sama sekali (tetap satu transaksi seperti sebelumnya)
        raise
    finally:
        conn.close()           # mengembalikan koneksi ke pool
    return len(df)


def catat_isu(engine: Engine, run_id: int, isu: list[dict]) -> None:
    if not isu:
        return
    with engine.begin() as conn:
        conn.execute(INSERT_ISU, [{"run_id": run_id, **i} for i in isu])


def mulai_run(engine: Engine, tanggal_awal, tanggal_akhir) -> int:
    with engine.begin() as conn:
        return conn.execute(
            text("INSERT INTO log_etl (tanggal_awal, tanggal_akhir) VALUES (:a, :b) RETURNING id"),
            {"a": tanggal_awal, "b": tanggal_akhir},
        ).scalar_one()


def selesai_run(engine: Engine, run_id: int, status: str, **kolom) -> None:
    set_extra = "".join(f", {k} = :{k}" for k in kolom)
    with engine.begin() as conn:
        conn.execute(
            text(f"UPDATE log_etl SET selesai = now(), status = :status{set_extra} WHERE id = :id"),
            {"id": run_id, "status": status, **kolom},
        )
