# Catatan Keputusan Desain

Tulis dengan bahasamu sendiri. Format: keputusan → alternatif yang dipertimbangkan → alasan → konsekuensi.
Ini yang akan kamu baca ulang sebelum wawancara.

## 001 – Sumber data: yfinance
- **Alternatif**: scraping situs IDX, file Ringkasan Perdagangan IDX manual, API berbayar.
- **Alasan**: (isi sendiri)
- **Konsekuensi / risiko**: (isi sendiri — mis. data tidak resmi, bisa ada gap)

## 002 – Primary key `harga_harian` = (kode, tanggal)
- **Alasan**: (isi sendiri — kenapa bukan id serial saja?)
- **Konsekuensi**: (isi sendiri — hubungannya dengan idempotency)

## 003 – Strategi load: upsert (`ON CONFLICT DO UPDATE`)
- **Alternatif**: `DO NOTHING`, truncate-and-reload, append + dedup belakangan.
- **Alasan**: (isi sendiri)

## 004 – Data bermasalah: dicatat, tidak langsung dibuang
- **Alasan**: (isi sendiri — kaitkan dengan audit trail)

## 005 – Jadwal pengambilan data
- Jadwalkan ETL setelah pasar tutup, misalnya pukul 17:00 WIB
- **Alasan**: (isi sendiri)
