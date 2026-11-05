"""Format angka dan tanggal gaya Indonesia. Tanpa Streamlit, agar mudah diuji."""
import pandas as pd

KOSONG = "–"
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]
BULAN_SINGKAT = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def angka(x, desimal: int = 0) -> str:
    """5025 -> '5.025'; 1234.5 dengan desimal=1 -> '1.234,5'."""
    if pd.isna(x):
        return KOSONG
    teks = f"{abs(float(x)):,.{desimal}f}".translate(str.maketrans(",.", ".,"))
    return f"−{teks}" if round(float(x), desimal) < 0 else teks


def persen(x, desimal: int = 2, tanda: bool = True) -> str:
    """Pecahan ke persen: -0.0447 -> '−4,47%'; 0.0289 -> '+2,89%'; 0 -> '0,00%'."""
    if pd.isna(x):
        return KOSONG
    nilai = round(float(x) * 100, desimal)
    plus = "+" if tanda and nilai > 0 else ""
    return f"{plus}{angka(nilai, desimal)}%"


def rasio(x) -> str:
    return KOSONG if pd.isna(x) else f"{angka(x, 1)}×"


def ringkas(x) -> str:
    """Bilangan besar dengan satuan Indonesia: 500_000_000 -> '500 jt'; 1_500_000_000 -> '1,5 M'."""
    if pd.isna(x):
        return KOSONG
    if abs(x) >= 1e9:
        return f"{angka(x / 1e9, 1 if x % 1e9 else 0)} M"
    if abs(x) >= 1e6:
        return f"{angka(x / 1e6, 1 if x % 1e6 else 0)} jt"
    return angka(x)


def tanggal(d) -> str:
    return KOSONG if pd.isna(d) else f"{d.day} {BULAN_SINGKAT[d.month - 1]} {d.year}"


def tanggal_pendek(d) -> str:
    return KOSONG if pd.isna(d) else f"{d.day} {BULAN_SINGKAT[d.month - 1]}"


def tanggal_waktu(d) -> str:
    return KOSONG if pd.isna(d) else f"{tanggal(d)} {d.hour:02d}:{d.minute:02d}"


def bulan(d) -> str:
    return KOSONG if pd.isna(d) else f"{BULAN[d.month - 1]} {d.year}"


def bulan_pendek(d) -> str:
    return KOSONG if pd.isna(d) else f"{BULAN_SINGKAT[d.month - 1]} {str(d.year)[2:]}"


def posisi_hari(nilai: float, seri) -> str:
    """Posisi nilai hari ini di antara hari-hari pembanding (`seri` sudah termasuk hari ini)."""
    if nilai < 0:
        ke = int((pd.Series(seri) < nilai).sum()) + 1
        return "Terburuk" if ke == 1 else f"Terburuk ke-{ke}"
    if nilai > 0:
        ke = int((pd.Series(seri) > nilai).sum()) + 1
        return "Terbaik" if ke == 1 else f"Terbaik ke-{ke}"
    return "Tanpa perubahan"
