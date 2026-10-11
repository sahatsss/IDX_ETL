"""Aturan validasi kualitas data.

⚠️ BAGIAN INI KAMU TULIS SENDIRI (lihat CLAUDE.md, aturan #1).

Kontrak fungsi `validasi(df)`:
- Input: DataFrame dengan kolom extract.KOLOM.
- Output: tuple (df_bersih, isu)
    - df_bersih: baris yang lolos dan boleh dimuat.
    - isu: list of dict {kode, tanggal, aturan, keterangan}, disimpan ke tabel data_quality_issue.

Keputusan yang harus kamu ambil (dan catat di DECISIONS.md):
- Baris bermasalah dibuang, tetap dimuat dengan flag, atau tergantung aturannya?

Ide aturan (TODO, implementasikan satu per satu dan buat test-nya di tests/test_validate.py):
- [ ] harga_tidak_positif   : harga buka/tinggi/rendah/tutup <= 0 atau kosong
- [ ] ohlc_tidak_konsisten  : high < max(open, close) atau low > min(open, close)
- [ ] volume_negatif        : volume < 0
- [ ] duplikat              : (kode, tanggal) muncul lebih dari sekali
- [ ] lonjakan_ekstrem      : perubahan harga tutup harian melebihi batas ARB/ARA
                              (cari tahu sendiri batas auto rejection BEI yang berlaku!)
- [ ] tanggal_masa_depan    : tanggal > hari ini
"""
import pandas as pd


def validasi(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    isu: list[dict] = []
    # TODO: tulis aturanmu di sini
    return df, isu
