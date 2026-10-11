"""CLI: python -m idx_pipeline.main [--start YYYY-MM-DD] [--end YYYY-MM-DD]"""
import argparse
import logging
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import create_engine

from . import config, extract, load, validate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("idx_pipeline")


def parse_args():
    p = argparse.ArgumentParser(description="ETL harga saham IDX ke PostgreSQL")
    p.add_argument("--start", type=date.fromisoformat, default=date.today() - timedelta(days=7))
    p.add_argument("--end", type=date.fromisoformat, default=date.today())
    return p.parse_args()


def run(mulai: date, akhir: date) -> None:
    engine = create_engine(config.database_url())
    emiten = pd.read_csv(config.TICKERS_CSV, dtype=str)
    load.muat_emiten(engine, emiten)

    run_id = load.mulai_run(engine, mulai, akhir)
    log.info("run %s: %s s.d. %s, %d saham", run_id, mulai, akhir, len(emiten))
    try:
        mentah = extract.ambil_harga(emiten["kode"].tolist(), mulai, akhir)
        bersih, isu = validate.validasi(mentah)
        dimuat = load.muat_harga(engine, bersih)
        load.catat_isu(engine, run_id, isu)
        load.selesai_run(engine, run_id, "sukses",
                         baris_diambil=len(mentah), baris_dimuat=dimuat, jumlah_isu=len(isu))
        log.info("selesai: %d diambil, %d dimuat, %d isu", len(mentah), dimuat, len(isu))
    except Exception as e:
        load.selesai_run(engine, run_id, "gagal", pesan_error=str(e)[:2000])
        log.exception("run %s gagal", run_id)
        raise


if __name__ == "__main__":
    a = parse_args()
    run(a.start, a.end)
