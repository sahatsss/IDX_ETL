"""Test format angka dan tanggal gaya Indonesia di dashboard."""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard"))
import fmt  # noqa: E402


@pytest.mark.parametrize("nilai, desimal, hasil", [
    (5025, 0, "5.025"), (1234.5, 1, "1.234,5"), (-2400, 0, "−2.400"), (0, 0, "0"), (None, 0, fmt.KOSONG),
])
def test_angka(nilai, desimal, hasil):
    assert fmt.angka(nilai, desimal) == hasil


@pytest.mark.parametrize("nilai, hasil", [
    (-0.0447, "−4,47%"), (0.0289, "+2,89%"), (0, "0,00%"), (-0.00001, "0,00%"), (None, fmt.KOSONG),
])
def test_persen(nilai, hasil):
    assert fmt.persen(nilai) == hasil


def test_persen_tanpa_tanda_plus():
    assert fmt.persen(0.64, 0, tanda=False) == "64%"


def test_rasio():
    assert fmt.rasio(3.39) == "3,4×"


def test_ringkas_memakai_satuan_indonesia():
    assert fmt.ringkas(500_000_000) == "500 jt"
    assert fmt.ringkas(1_500_000_000) == "1,5 M"
    assert fmt.ringkas(1_000_000_000) == "1 M"
    assert fmt.ringkas(950) == "950"


def test_tanggal_dan_bulan_berbahasa_indonesia():
    d = date(2026, 10, 3)
    assert fmt.tanggal(d) == "3 Okt 2026"
    assert fmt.tanggal_pendek(d) == "3 Okt"
    assert fmt.bulan(d) == "Oktober 2026"
    assert fmt.bulan_pendek(d) == "Okt 26"


def test_posisi_hari():
    seri = [-0.15, -0.05, -0.04, 0.01, 0.08]
    assert fmt.posisi_hari(-0.04, seri) == "Terburuk ke-3"
    assert fmt.posisi_hari(-0.15, seri) == "Terburuk"
    assert fmt.posisi_hari(0.01, seri) == "Terbaik ke-2"
    assert fmt.posisi_hari(0, seri) == "Tanpa perubahan"
