"""Mengambil data OHLCV harian dari yfinance."""
from datetime import date

import pandas as pd
import yfinance as yf

KOLOM = ["kode", "tanggal", "harga_buka", "harga_tertinggi", "harga_terendah", "harga_tutup", "volume"]


def ambil_harga(kode_list: list[str], mulai: date, akhir: date) -> pd.DataFrame:
    """Kembalikan DataFrame panjang (satu baris per kode per tanggal) dengan kolom KOLOM.

    `akhir` bersifat inklusif (yfinance memperlakukan `end` eksklusif, jadi ditambah 1 hari).
    """
    frames = []
    for kode in kode_list:
        df = yf.download(
            f"{kode}.JK",
            start=mulai.isoformat(),
            end=(pd.Timestamp(akhir) + pd.Timedelta(days=1)).date().isoformat(),
            auto_adjust=False,   # simpan harga mentah; penyesuaian corporate action diputuskan nanti
            progress=False,
        )
        if df.empty:
            continue
        if isinstance(df.columns, pd.MultiIndex):   # yfinance versi baru mengembalikan MultiIndex
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index().rename(columns={
            "Date": "tanggal", "Open": "harga_buka", "High": "harga_tertinggi",
            "Low": "harga_terendah", "Close": "harga_tutup", "Volume": "volume",
        })
        df["kode"] = kode
        df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.date
        frames.append(df[KOLOM])

    if not frames:
        return pd.DataFrame(columns=KOLOM)
    return pd.concat(frames, ignore_index=True)
