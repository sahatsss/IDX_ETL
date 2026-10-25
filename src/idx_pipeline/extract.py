"""Mengambil data OHLCV harian dari yfinance."""
import logging
import time
from datetime import date

import pandas as pd
import yfinance as yf

log = logging.getLogger("idx_pipeline")

KOLOM = ["kode", "tanggal", "harga_buka", "harga_tertinggi", "harga_terendah", "harga_tutup", "volume"]
KOLOM_YF = {"Open": "harga_buka", "High": "harga_tertinggi", "Low": "harga_terendah",
            "Close": "harga_tutup", "Volume": "volume"}

UKURAN_BATCH = 20        # jumlah ticker per panggilan yf.download
PERCOBAAN = 3            # total percobaan untuk ticker yang datanya kosong / gagal
JEDA_AWAL_DETIK = 2      # jeda sebelum percobaan ulang, dikali 2 setiap kali (2, 4, ...)


def _unduh(kode_batch: list[str], mulai: date, akhir: date) -> pd.DataFrame:
    """Satu panggilan yfinance untuk banyak ticker. `akhir` inklusif (yfinance memperlakukan `end` eksklusif)."""
    return yf.download(
        [f"{k}.JK" for k in kode_batch],
        start=mulai.isoformat(),
        end=(pd.Timestamp(akhir) + pd.Timedelta(days=1)).date().isoformat(),
        auto_adjust=False,   # simpan harga mentah, lihat DECISIONS.md #007
        group_by="ticker",   # kolom MultiIndex: (ticker, field)
        threads=True,
        progress=False,
    )


def _pisahkan(data: pd.DataFrame, kode: str) -> pd.DataFrame:
    """Ambil data satu kode dari hasil batch; kembalikan DataFrame kosong jika tidak ada."""
    ticker = f"{kode}.JK"
    if data is None or data.empty:
        return pd.DataFrame(columns=KOLOM)
    if isinstance(data.columns, pd.MultiIndex):
        if ticker not in data.columns.get_level_values(0):
            return pd.DataFrame(columns=KOLOM)
        df = data[ticker]
    else:
        df = data
    # Hasil batch memakai gabungan tanggal semua ticker. Tanggal di mana ticker ini tidak punya data
    # muncul sebagai baris NaN; baris itu bukan data rusak, jadi dibuang di sini, bukan di validasi.
    df = df.dropna(subset=list(KOLOM_YF), how="all")
    if df.empty:
        return pd.DataFrame(columns=KOLOM)
    df = df.reset_index().rename(columns={"Date": "tanggal", **KOLOM_YF})
    df["kode"] = kode
    df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.date
    return df[KOLOM]


def ambil_harga(kode_list: list[str], mulai: date, akhir: date) -> pd.DataFrame:
    """Kembalikan DataFrame panjang (satu baris per kode per tanggal) dengan kolom KOLOM.

    Ticker diunduh per batch. Ticker yang hasilnya kosong atau error dicoba ulang (maks. PERCOBAAN kali);
    jika tetap kosong, dicatat di log sebagai peringatan dan dilewati.
    """
    frames = []
    sisa = list(kode_list)
    for percobaan in range(1, PERCOBAAN + 1):
        kosong = []
        for i in range(0, len(sisa), UKURAN_BATCH):
            batch = sisa[i:i + UKURAN_BATCH]
            try:
                data = _unduh(batch, mulai, akhir)
            except Exception as e:          # error jaringan dsb.: seluruh batch dicoba ulang
                log.warning("percobaan %d: batch %s gagal: %s", percobaan, batch, e)
                kosong.extend(batch)
                continue
            for kode in batch:
                df = _pisahkan(data, kode)
                if df.empty:
                    kosong.append(kode)
                else:
                    frames.append(df)
        if not kosong:
            break
        if percobaan < PERCOBAAN:
            jeda = JEDA_AWAL_DETIK * 2 ** (percobaan - 1)
            log.warning("percobaan %d: %d ticker kosong %s, coba lagi dalam %ds",
                        percobaan, len(kosong), kosong, jeda)
            time.sleep(jeda)
        sisa = kosong
    else:
        log.warning("tidak ada data setelah %d percobaan: %s", PERCOBAAN, kosong)

    if not frames:
        return pd.DataFrame(columns=KOLOM)
    return pd.concat(frames, ignore_index=True)
