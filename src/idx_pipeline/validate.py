"""Aturan validasi kualitas data.

Kontrak fungsi `validasi(df, hari_ini=None)`:
- Input: DataFrame dengan kolom extract.KOLOM.
- Output: tuple (df_bersih, isu)
    - df_bersih: baris yang lolos dan boleh dimuat.
    - isu: list of dict {kode, tanggal, aturan, keterangan}, disimpan ke tabel data_quality_issue.

Perlakuan per aturan (lihat DECISIONS.md #004):
- BUANG + catat : harga_tidak_positif, ohlc_tidak_konsisten, volume_negatif, duplikat, tanggal_masa_depan
                  (datanya pasti salah, jadi tidak boleh masuk analisis)
- SIMPAN + catat: lonjakan_ekstrem
                  (bisa saja nyata, mis. stock split karena harga disimpan tanpa adjust)

Urutan aturan penting: baris yang sudah dibuang oleh aturan sebelumnya tidak diperiksa lagi,
sehingga satu kesalahan tidak tercatat berkali-kali dan perbandingan dengan NaN tidak perlu dipikirkan.
"""
from collections.abc import Callable
from datetime import date

import pandas as pd

KOLOM_HARGA = ["harga_buka", "harga_tertinggi", "harga_terendah", "harga_tutup"]

# Batas auto rejection BEI berdasarkan harga acuan (harga tutup hari sebelumnya):
# (harga_acuan_minimum, persentase). Dipakai simetris untuk naik (ARA) maupun turun (ARB),
# dengan angka ARA sebagai batas terluas, agar aturan hanya menandai perubahan yang
# memang mustahil terjadi dalam satu hari perdagangan normal.
# ⚠️ Verifikasi ke peraturan BEI terbaru; batas ARB pernah diubah beberapa kali (2020, 2023, 2025).
BATAS_AUTO_REJECTION = [
    (5000, 0.20),
    (200, 0.25),
    (0, 0.35),
]
# Kelonggaran untuk pembulatan fraksi harga (tick size) dan selisih kecil data yfinance.
TOLERANSI_LONJAKAN = 0.01


def _batas_auto_rejection(harga_acuan: float) -> float:
    if pd.isna(harga_acuan):
        return float("nan")
    for minimum, persen in BATAS_AUTO_REJECTION:
        if harga_acuan >= minimum:
            return persen
    return BATAS_AUTO_REJECTION[-1][1]


def _catat(isu: list[dict], dilanggar: pd.DataFrame, aturan: str,
           keterangan: Callable[[dict], str]) -> None:
    """Ubah setiap baris yang melanggar menjadi satu dict isu."""
    for b in dilanggar.to_dict("records"):
        isu.append({
            "kode": b["kode"],
            "tanggal": b["tanggal"],
            "aturan": aturan,
            "keterangan": keterangan(b),
        })


def validasi(df: pd.DataFrame, hari_ini: date | None = None) -> tuple[pd.DataFrame, list[dict]]:
    """`hari_ini` bisa diisi di test agar hasil tidak bergantung pada tanggal saat test dijalankan."""
    isu: list[dict] = []
    if df.empty:
        return df, isu
    hari_ini = hari_ini or date.today()

    # True = baris dibuang. Setiap aturan hanya memeriksa baris yang belum dibuang (`~buang`).
    buang = pd.Series(False, index=df.index)

    # 1. tanggal_masa_depan
    tanggal = pd.to_datetime(df["tanggal"]).dt.date
    mask = ~buang & (tanggal > hari_ini)
    _catat(isu, df[mask], "tanggal_masa_depan",
           lambda b: f"tanggal {b['tanggal']} melewati hari ini ({hari_ini})")
    buang |= mask

    # 2. harga_tidak_positif: `NaN <= 0` bernilai False, jadi kosong harus dicek terpisah
    harga_salah = df[KOLOM_HARGA].isna() | (df[KOLOM_HARGA] <= 0)
    mask = ~buang & harga_salah.any(axis=1)
    _catat(isu, df[mask], "harga_tidak_positif",
           lambda b: "kolom bermasalah: " + ", ".join(
               f"{k}={b[k]}" for k in KOLOM_HARGA if pd.isna(b[k]) or b[k] <= 0))
    buang |= mask

    # 3. ohlc_tidak_konsisten: tertinggi harus >= buka & tutup, terendah harus <= buka & tutup
    atas = df[["harga_buka", "harga_tutup"]].max(axis=1)
    bawah = df[["harga_buka", "harga_tutup"]].min(axis=1)
    mask = ~buang & ((df["harga_tertinggi"] < atas) | (df["harga_terendah"] > bawah))
    _catat(isu, df[mask], "ohlc_tidak_konsisten",
           lambda b: (f"O={b['harga_buka']} H={b['harga_tertinggi']} "
                      f"L={b['harga_terendah']} C={b['harga_tutup']}"))
    buang |= mask

    # 4. volume_negatif (volume 0 sah: saham tidak diperdagangkan hari itu)
    mask = ~buang & (df["volume"] < 0)
    _catat(isu, df[mask], "volume_negatif", lambda b: f"volume={b['volume']}")
    buang |= mask

    # 5. duplikat: salinan pertama yang lolos aturan 1-4 disimpan, salinan berikutnya dibuang.
    # Dicek hanya di antara baris yang belum dibuang, lalu dikembalikan ke index df (sisanya False).
    mask = (df[~buang].duplicated(subset=["kode", "tanggal"], keep="first")
            .reindex(df.index, fill_value=False))
    _catat(isu, df[mask], "duplikat", lambda b: "(kode, tanggal) muncul lebih dari sekali")
    buang |= mask

    bersih = df[~buang]

    # 6. lonjakan_ekstrem: hanya ditandai, baris tetap dimuat.
    # Keterbatasan: baris pertama tiap kode dalam batch tidak punya harga kemarin
    # (harga itu ada di database, bukan di DataFrame), jadi tidak diperiksa.
    urut = bersih.sort_values(["kode", "tanggal"])
    acuan = urut.groupby("kode")["harga_tutup"].shift(1)
    perubahan = urut["harga_tutup"] / acuan - 1
    batas = acuan.map(_batas_auto_rejection)
    mask = perubahan.abs() > batas + TOLERANSI_LONJAKAN   # NaN (tanpa acuan) -> False
    dilanggar = urut[mask].assign(_acuan=acuan[mask], _perubahan=perubahan[mask], _batas=batas[mask])
    _catat(isu, dilanggar, "lonjakan_ekstrem",
           lambda b: (f"tutup {b['_acuan']} -> {b['harga_tutup']} ({b['_perubahan']:+.1%}), "
                      f"batas auto rejection ±{b['_batas']:.0%}"))

    return bersih, isu
