"""Test extract tanpa internet: yf.download diganti fungsi palsu (monkeypatch)."""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from idx_pipeline import extract

TANGGAL = pd.to_datetime(["2024-01-02", "2024-01-03"])


def frame_batch(data_per_ticker: dict) -> pd.DataFrame:
    """Tiru bentuk hasil yf.download(group_by='ticker'): kolom MultiIndex (ticker, field)."""
    bagian = {}
    for ticker, tutup in data_per_ticker.items():
        bagian[ticker] = pd.DataFrame(
            {"Open": tutup, "High": tutup, "Low": tutup, "Close": tutup, "Adj Close": tutup,
             "Volume": [1000 if not np.isnan(t) else np.nan for t in tutup]},
            index=pd.Index(TANGGAL, name="Date"),
        )
    return pd.concat(bagian, axis=1)


@pytest.fixture(autouse=True)
def tanpa_jeda(monkeypatch):
    monkeypatch.setattr(extract.time, "sleep", lambda detik: None)


def test_batch_dipisah_per_kode_dan_tanpa_akhiran_jk(monkeypatch):
    monkeypatch.setattr(extract, "_unduh", lambda batch, m, a: frame_batch(
        {"BBCA.JK": [100.0, 101.0], "BBRI.JK": [50.0, 51.0]}))
    df = extract.ambil_harga(["BBCA", "BBRI"], date(2024, 1, 2), date(2024, 1, 3))
    assert sorted(df["kode"].unique()) == ["BBCA", "BBRI"]
    assert len(df) == 4
    assert list(df.columns) == extract.KOLOM
    assert df["tanggal"].iloc[0] == date(2024, 1, 2)


def test_baris_nan_dari_gabungan_tanggal_dibuang(monkeypatch):
    # BBRI tidak punya data 3 Jan, tapi baris NaN muncul karena BBCA punya. Baris itu harus hilang.
    monkeypatch.setattr(extract, "_unduh", lambda batch, m, a: frame_batch(
        {"BBCA.JK": [100.0, 101.0], "BBRI.JK": [50.0, np.nan]}))
    df = extract.ambil_harga(["BBCA", "BBRI"], date(2024, 1, 2), date(2024, 1, 3))
    assert len(df[df["kode"] == "BBRI"]) == 1


def test_ticker_kosong_dicoba_ulang_lalu_berhasil(monkeypatch):
    panggilan = []

    def palsu(batch, m, a):
        panggilan.append(list(batch))
        if len(panggilan) == 1:                     # percobaan pertama: BBRI kosong
            return frame_batch({"BBCA.JK": [100.0, 101.0]})
        return frame_batch({"BBRI.JK": [50.0, 51.0]})

    monkeypatch.setattr(extract, "_unduh", palsu)
    df = extract.ambil_harga(["BBCA", "BBRI"], date(2024, 1, 2), date(2024, 1, 3))
    assert panggilan == [["BBCA", "BBRI"], ["BBRI"]]   # hanya ticker yang kosong yang diulang
    assert sorted(df["kode"].unique()) == ["BBCA", "BBRI"]


def test_ticker_tetap_kosong_dilewati_dan_dicatat(monkeypatch, caplog):
    monkeypatch.setattr(extract, "_unduh", lambda batch, m, a: frame_batch({"BBCA.JK": [100.0, 101.0]}))
    df = extract.ambil_harga(["BBCA", "XXXX"], date(2024, 1, 2), date(2024, 1, 3))
    assert df["kode"].unique().tolist() == ["BBCA"]
    assert "XXXX" in caplog.text


def test_error_jaringan_dicoba_ulang(monkeypatch):
    percobaan = {"n": 0}

    def palsu(batch, m, a):
        percobaan["n"] += 1
        if percobaan["n"] == 1:
            raise ConnectionError("timeout")
        return frame_batch({"BBCA.JK": [100.0, 101.0]})

    monkeypatch.setattr(extract, "_unduh", palsu)
    df = extract.ambil_harga(["BBCA"], date(2024, 1, 2), date(2024, 1, 3))
    assert len(df) == 2


def test_dibagi_per_batch(monkeypatch):
    monkeypatch.setattr(extract, "UKURAN_BATCH", 2)
    ukuran = []

    def palsu(batch, m, a):
        ukuran.append(len(batch))
        return frame_batch({f"{k}.JK": [1.0, 2.0] for k in batch})

    monkeypatch.setattr(extract, "_unduh", palsu)
    extract.ambil_harga(["A", "B", "C", "D", "E"], date(2024, 1, 2), date(2024, 1, 3))
    assert ukuran == [2, 2, 1]
