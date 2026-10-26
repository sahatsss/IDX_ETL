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
                  (bisa saja nyata, mis. stock split karena harga disimpan tanpa adjust).
                  Batas ARA/ARB mengikuti periode aturan BEI yang berlaku di tanggal transaksi.

Urutan aturan penting: baris yang sudah dibuang oleh aturan sebelumnya tidak diperiksa lagi,
sehingga satu kesalahan tidak tercatat berkali-kali dan perbandingan dengan NaN tidak perlu dipikirkan.
"""
from collections.abc import Callable
from datetime import date

import pandas as pd

KOLOM_HARGA = ["harga_buka", "harga_tertinggi", "harga_terendah", "harga_tutup"]

# Batas auto rejection (AR) BEI per periode berlaku, berdasarkan harga acuan (harga tutup kemarin).
# Setiap rentang: (harga_acuan_lebih_dari, ARA, ARB), dicek dari harga tertinggi.
# Nilai None = batas nominal Rp1 (rentang Rp1-Rp10), bukan persentase.
# Sumber: Siaran Pers BEI No. 083/BEI.SPR/09-2026 (21 Sep 2026), SK Direksi BEI Kep-00136/BEI/09-2026
#         https://www.idx.co.id/id/berita/siaran-pers/2704
_SIMETRIS = [(5000, 0.20, 0.20), (200, 0.25, 0.25), (0, 0.35, 0.35)]
_ARB_15 = [(5000, 0.20, 0.15), (200, 0.25, 0.15), (0, 0.35, 0.15)]
_RP1 = [(0, None, None)]   # Rp1-Rp10, berlaku sejak harga minimum turun ke Rp1

PERIODE_AUTO_REJECTION = [
    # (berlaku_mulai, rentang). Tanggal sebelum periode pertama memakai periode pertama.
    # Dua periode pertama (sebelum 28 Sep 2026): ketentuan BEI/OJK yang berlaku saat itu; dokumen spesifiknya
    # belum dicantumkan. Didukung data: dengan ARB 15% untuk semua tanggal, 11 penurunan 16-25% tertandai dan
    # semuanya sebelum Mar 2025 (saat ARB masih simetris). Lihat DECISIONS.md #004.
    (date(2023, 9, 4), _SIMETRIS),
    (date(2025, 4, 8), _ARB_15),
    (date(2026, 9, 28), _ARB_15[:2] + [(10, 0.35, 0.15)] + _RP1),
    (date(2027, 1, 1), _SIMETRIS[:2] + [(10, 0.35, 0.35)] + _RP1),
]
# Kelonggaran untuk pembulatan fraksi harga (tick size) dan selisih kecil data yfinance.
TOLERANSI_LONJAKAN = 0.01


def _batas_auto_rejection(harga_acuan: float, tanggal: date) -> tuple[float, float]:
    """Kembalikan (ARA, ARB) sebagai pecahan (0.25 = 25%) untuk harga acuan dan tanggal transaksi."""
    if pd.isna(harga_acuan) or harga_acuan <= 0:
        return float("nan"), float("nan")
    rentang = PERIODE_AUTO_REJECTION[0][1]
    for berlaku_mulai, r in PERIODE_AUTO_REJECTION:
        if tanggal >= berlaku_mulai:
            rentang = r
    for lebih_dari, ara, arb in rentang:
        if harga_acuan > lebih_dari:      # aturan BEI: ">Rp200 - <=Rp5.000", jadi pakai >, bukan >=
            if ara is None:               # batas nominal Rp1 diubah ke persentase dari harga acuan
                return 1 / harga_acuan, 1 / harga_acuan
            return ara, arb
    return float("nan"), float("nan")


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
    # Batas dipilih per baris: tergantung harga acuan, tanggal (periode aturan), dan arah perubahan
    # (naik dibandingkan dengan ARA, turun dengan ARB, karena keduanya bisa berbeda / asimetris).
    tanggal_urut = pd.to_datetime(urut["tanggal"]).dt.date
    batas = pd.Series(
        [ara if p >= 0 else arb
         for p, (ara, arb) in zip(perubahan, map(_batas_auto_rejection, acuan, tanggal_urut))],
        index=urut.index, dtype=float,
    )
    mask = perubahan.abs() > batas + TOLERANSI_LONJAKAN   # NaN (tanpa acuan) -> False
    dilanggar = urut[mask].assign(_acuan=acuan[mask], _perubahan=perubahan[mask], _batas=batas[mask])
    _catat(isu, dilanggar, "lonjakan_ekstrem",
           lambda b: (f"tutup {b['_acuan']} -> {b['harga_tutup']} ({b['_perubahan']:+.1%}), "
                      f"batas {'ARA' if b['_perubahan'] >= 0 else 'ARB'} {b['_batas']:.0%}"))

    return bersih, isu
