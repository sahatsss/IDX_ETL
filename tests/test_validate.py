"""Test untuk aturan validasi. Satu kelompok test per aturan."""
from datetime import date

import pandas as pd

from idx_pipeline.validate import validasi

HARI_INI = date(2024, 1, 31)


def baris(**ubah):
    b = dict(kode="BBCA", tanggal=date(2024, 1, 2), harga_buka=9400, harga_tertinggi=9500,
             harga_terendah=9350, harga_tutup=9450, volume=1_000_000)
    b.update(ubah)
    return b


def jalankan(*daftar_baris):
    return validasi(pd.DataFrame(list(daftar_baris)), hari_ini=HARI_INI)


def aturan_dari(isu):
    return [i["aturan"] for i in isu]


def test_data_valid_lolos_tanpa_isu():
    bersih, isu = jalankan(baris())
    assert len(bersih) == 1
    assert isu == []


def test_dataframe_kosong():
    bersih, isu = jalankan()
    assert bersih.empty
    assert isu == []


def test_format_isu_sesuai_kontrak():
    _, isu = jalankan(baris(harga_tutup=0))
    assert set(isu[0]) == {"kode", "tanggal", "aturan", "keterangan"}
    assert isu[0]["kode"] == "BBCA"
    assert isu[0]["tanggal"] == date(2024, 1, 2)


# --- harga_tidak_positif ---------------------------------------------------

def test_harga_nol_tercatat_sebagai_isu():
    bersih, isu = jalankan(baris(harga_tutup=0))
    assert aturan_dari(isu) == ["harga_tidak_positif"]
    assert bersih.empty


def test_harga_negatif_tercatat():
    _, isu = jalankan(baris(harga_buka=-1))
    assert aturan_dari(isu) == ["harga_tidak_positif"]


def test_harga_kosong_tercatat():
    _, isu = jalankan(baris(harga_terendah=None))
    assert aturan_dari(isu) == ["harga_tidak_positif"]
    assert "harga_terendah" in isu[0]["keterangan"]


def test_baris_valid_tidak_ikut_tercatat_saat_dicampur():
    bersih, isu = jalankan(baris(), baris(kode="BBRI", harga_tutup=0))
    assert [i["kode"] for i in isu] == ["BBRI"]
    assert bersih["kode"].tolist() == ["BBCA"]


# --- ohlc_tidak_konsisten --------------------------------------------------

def test_tertinggi_di_bawah_tutup():
    bersih, isu = jalankan(baris(harga_tertinggi=9420))   # tutup 9450
    assert aturan_dari(isu) == ["ohlc_tidak_konsisten"]
    assert bersih.empty


def test_terendah_di_atas_buka():
    _, isu = jalankan(baris(harga_terendah=9410))          # buka 9400
    assert aturan_dari(isu) == ["ohlc_tidak_konsisten"]


def test_harga_sama_semua_valid():
    _, isu = jalankan(baris(harga_buka=9400, harga_tertinggi=9400, harga_terendah=9400, harga_tutup=9400))
    assert isu == []


def test_harga_kosong_tidak_dicatat_dua_kali():
    _, isu = jalankan(baris(harga_tertinggi=None))
    assert aturan_dari(isu) == ["harga_tidak_positif"]


# --- volume_negatif ----------------------------------------------------------

def test_volume_negatif():
    bersih, isu = jalankan(baris(volume=-5))
    assert aturan_dari(isu) == ["volume_negatif"]
    assert bersih.empty


def test_volume_nol_valid():
    _, isu = jalankan(baris(volume=0))
    assert isu == []


# --- duplikat ----------------------------------------------------------------

def test_duplikat_salinan_pertama_disimpan():
    bersih, isu = jalankan(baris(), baris(volume=2_000_000))
    assert aturan_dari(isu) == ["duplikat"]
    assert len(bersih) == 1
    assert bersih["volume"].iloc[0] == 1_000_000


def test_kode_berbeda_tanggal_sama_bukan_duplikat():
    _, isu = jalankan(baris(), baris(kode="BBRI"))
    assert isu == []


def test_duplikat_dengan_salinan_pertama_rusak():
    # salinan pertama dibuang karena harga 0, jadi salinan kedua yang valid harus disimpan
    bersih, isu = jalankan(baris(harga_tutup=0), baris())
    assert aturan_dari(isu) == ["harga_tidak_positif"]
    assert len(bersih) == 1


# --- tanggal_masa_depan ------------------------------------------------------

def test_tanggal_masa_depan():
    bersih, isu = jalankan(baris(tanggal=date(2024, 2, 1)))
    assert aturan_dari(isu) == ["tanggal_masa_depan"]
    assert bersih.empty


def test_tanggal_hari_ini_valid():
    _, isu = jalankan(baris(tanggal=HARI_INI))
    assert isu == []


# --- lonjakan_ekstrem --------------------------------------------------------

def dua_hari(tutup_kemarin, tutup_hari_ini, kode="BBCA"):
    def b(tgl, tutup):
        return baris(kode=kode, tanggal=tgl, harga_buka=tutup, harga_tertinggi=tutup,
                     harga_terendah=tutup, harga_tutup=tutup)
    return b(date(2024, 1, 2), tutup_kemarin), b(date(2024, 1, 3), tutup_hari_ini)


def test_lonjakan_ditandai_tapi_tetap_dimuat():
    bersih, isu = jalankan(*dua_hari(10_000, 15_000))      # +50%, batas 20%
    assert aturan_dari(isu) == ["lonjakan_ekstrem"]
    assert isu[0]["tanggal"] == date(2024, 1, 3)
    assert len(bersih) == 2


def test_penurunan_ekstrem_ditandai():
    _, isu = jalankan(*dua_hari(1_000, 500))               # -50%, batas 25%
    assert aturan_dari(isu) == ["lonjakan_ekstrem"]


def test_perubahan_dalam_batas_tidak_ditandai():
    _, isu = jalankan(*dua_hari(1_000, 1_250))             # tepat +25% (ARA harga 200-5000)
    assert isu == []


def test_batas_tergantung_harga_acuan():
    _, isu_mahal = jalankan(*dua_hari(10_000, 12_400))     # +24% > 20%
    _, isu_murah = jalankan(*dua_hari(100, 124))           # +24% < 35%
    assert aturan_dari(isu_mahal) == ["lonjakan_ekstrem"]
    assert isu_murah == []


def test_lonjakan_tidak_membandingkan_antar_kode():
    bbca, _ = dua_hari(10_000, 10_000, kode="BBCA")
    _, bbri = dua_hari(1_000, 1_000, kode="BBRI")
    _, isu = jalankan(bbca, bbri)
    assert isu == []
