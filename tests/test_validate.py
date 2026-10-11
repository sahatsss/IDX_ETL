"""Test untuk aturan validasi. Tambahkan satu test per aturan yang kamu tulis."""
from datetime import date

import pandas as pd

from idx_pipeline.validate import validasi


def baris(**ubah):
    b = dict(kode="BBCA", tanggal=date(2024, 1, 2), harga_buka=9400, harga_tertinggi=9500,
             harga_terendah=9350, harga_tutup=9450, volume=1_000_000)
    b.update(ubah)
    return b


def test_data_valid_lolos_tanpa_isu():
    df = pd.DataFrame([baris()])
    bersih, isu = validasi(df)
    assert len(bersih) == 1
    assert isu == []


# Contoh test yang akan GAGAL sampai kamu mengimplementasikan aturannya.
# Hapus tanda skip setelah aturan 'harga_tidak_positif' kamu tulis.
import pytest

@pytest.mark.skip(reason="aturan belum diimplementasikan")
def test_harga_nol_tercatat_sebagai_isu():
    df = pd.DataFrame([baris(harga_tutup=0)])
    _, isu = validasi(df)
    assert any(i["aturan"] == "harga_tidak_positif" for i in isu)
