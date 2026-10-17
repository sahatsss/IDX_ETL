# Catatan Keputusan Desain

Format: keputusan → alternatif yang dipertimbangkan → alasan → konsekuensi.
Ini yang akan kamu baca ulang sebelum wawancara.

> ⚠️ DRAF dibuat dengan bantuan Claude Code (16 Okt 2026). Baca, sesuaikan dengan bahasamu sendiri,
> dan hapus catatan ini setelah kamu yakin bisa menjelaskan setiap poin tanpa melihat teks.

## 001 – Sumber data: yfinance
- **Keputusan**: mengambil data OHLCV harian saham IDX dari yfinance (ticker berakhiran `.JK`).
- **Alternatif**: scraping situs IDX, file Ringkasan Perdagangan IDX manual, API berbayar.
- **Alasan**:
  - Gratis dan tanpa API key, sehingga cocok untuk proyek portofolio dan mudah dijalankan ulang orang lain.
  - Bisa backfill bertahun-tahun ke belakang dengan satu panggilan, tidak perlu mengunduh file harian satu per satu.
  - Scraping situs IDX rapuh (struktur halaman bisa berubah, ada proteksi bot) dan berisiko melanggar ketentuan situs.
  - API berbayar lebih andal, tapi biayanya tidak sepadan untuk skala proyek ini.
- **Konsekuensi / risiko**:
  - Data **tidak resmi**: bisa ada tanggal hilang, nilai 0, atau koreksi data di kemudian hari.
  - Tidak ada SLA; jika Yahoo mengubah API, extract bisa gagal → dimitigasi dengan `log_etl` (status `gagal` + `pesan_error`).
  - Harga disimpan **mentah** (`auto_adjust=False`, lihat #007), sehingga stock split/dividen tidak disesuaikan.
  - Karena risiko kualitas ini, pipeline butuh lapisan validasi (#004).

## 002 – Primary key `harga_harian` = (kode, tanggal)
- **Keputusan**: natural key komposit `(kode, tanggal)`, bukan `id SERIAL`.
- **Alternatif**: surrogate key `id SERIAL` + index biasa di (kode, tanggal).
- **Alasan**:
  - Secara bisnis, satu saham hanya punya **satu** harga harian per tanggal. Primary key memaksa aturan itu di level database,
    bukan hanya di kode Python.
  - Dengan `id SERIAL`, menjalankan ETL dua kali akan menghasilkan baris ganda dengan id berbeda, dan database tidak akan menolaknya.
  - Constraint unik ini juga menjadi target `ON CONFLICT (kode, tanggal)` untuk upsert (#003).
- **Konsekuensi**:
  - **Idempotency** dijamin oleh database: sudah dibuktikan di Fase 2. ETL dijalankan 3 kali untuk rentang
    2026-09-01 s.d. 2026-10-14, dan `SELECT count(*) FROM harga_harian` tetap 320 baris (10 saham × 32 hari bursa).
  - Query analitik (Fase 4) yang mem-filter/mengurutkan berdasarkan kode lalu tanggal otomatis terbantu index primary key.
  - Jika suatu saat ada dua sumber data untuk tanggal yang sama, kolom `sumber` harus masuk ke key, atau sumber kedua harus menimpa.

## 003 – Strategi load: upsert (`ON CONFLICT DO UPDATE`)
- **Keputusan**: `INSERT ... ON CONFLICT (kode, tanggal) DO UPDATE SET ...` dan memperbarui `dimuat_pada = now()`.
- **Alternatif**:
  - `DO NOTHING`: aman dari duplikat, tapi koreksi data dari yfinance (mis. volume yang diperbarui keesokan harinya) tidak pernah masuk.
  - Truncate-and-reload: sederhana, tapi menghapus seluruh histori setiap run, lambat untuk backfill bertahun-tahun,
    dan jika reload gagal di tengah jalan, tabel bisa kosong.
  - Append + dedup belakangan: tabel sempat berisi duplikat, sehingga setiap query harus ingat untuk dedup.
- **Alasan**:
  - Run ulang untuk rentang yang sama menghasilkan kondisi akhir yang sama (idempotent).
  - Data terbaru dari sumber selalu menang, sehingga koreksi data ikut masuk.
  - Default run harian mengambil 7 hari terakhir (overlap dengan run sebelumnya). Itu hanya aman karena upsert.
  - Seluruh batch dimuat dalam satu transaksi (`engine.begin()`): jika gagal, tidak ada data setengah jadi.
- **Konsekuensi**:
  - Nilai lama ditimpa tanpa histori. Jika butuh jejak perubahan harga, perlu tabel histori/audit terpisah.
  - `baris_dimuat` di `log_etl` saat ini = jumlah baris yang **dikirim** (`len(df)`), bukan jumlah baris baru.
    Bukti idempotency ada di `count(*)` tabel, bukan di angka ini.

## 004 – Data bermasalah: perlakuan berbeda per aturan
- **Keputusan**: setiap pelanggaran **selalu dicatat** di `data_quality_issue`, tapi perlakuan barisnya bergantung pada aturannya.

  | Aturan | Perlakuan | Alasan |
  |---|---|---|
  | `tanggal_masa_depan` | buang + catat | tidak mungkin ada harga untuk hari yang belum terjadi |
  | `harga_tidak_positif` | buang + catat | harga ≤ 0 atau kosong pasti salah, dan akan merusak perhitungan return |
  | `ohlc_tidak_konsisten` | buang + catat | high di bawah open/close (atau low di atas) mustahil secara definisi |
  | `volume_negatif` | buang + catat | volume tidak mungkin negatif (volume 0 tetap sah: saham tidak diperdagangkan) |
  | `duplikat` | simpan salinan pertama yang valid, buang sisanya | data tidak hilang, tapi tidak ada baris ganda |
  | `lonjakan_ekstrem` | **simpan** + catat | bisa jadi nyata (stock split, corporate action), jadi tidak boleh dibuang otomatis |

- **Alternatif**:
  - Buang semua yang bermasalah: database pasti bersih, tapi data nyata (mis. split) ikut hilang dan muncul "lubang" tanggal.
  - Muat semua, hanya catat: tidak ada data hilang, tapi data yang pasti salah ikut masuk ke analisis.
- **Alasan**:
  - **Audit trail**: tidak ada data yang hilang diam-diam. Setiap baris yang dibuang punya jejak (run_id, kode, tanggal, aturan, keterangan),
    sehingga bisa ditelusuri dan diperiksa ulang. Ini prinsip yang sama dengan kontrol di audit IT: setiap pengecualian harus terdokumentasi.
  - Membedakan "pasti salah" (dibuang) dan "mencurigakan" (ditandai) menghindari keputusan otomatis atas data yang butuh penilaian manusia.
- **Konsekuensi**:
  - Baris yang dibuang membuat `LAG()` di Fase 4 melompati hari itu, sehingga return-nya mencakup 2 hari.
  - Isu dicatat ulang setiap run (satu set per `run_id`). Ini disengaja (jejak per run), tapi query laporan harus mem-filter run terakhir.
  - Keterbatasan `lonjakan_ekstrem`: baris pertama tiap saham dalam satu batch tidak dicek karena harga kemarin ada di database,
    bukan di DataFrame.
  - Batas ARB/ARA di `validate.py` (35% / 25% / 20% menurut rentang harga, dipakai simetris + toleransi 1%)
    **harus diverifikasi ke peraturan BEI terbaru** (sumber: ...isi sendiri...).

## 005 – Jadwal pengambilan data
- **Keputusan**: ETL dijadwalkan setelah pasar tutup, hari Senin–Jumat pukul 17:00 WIB.
- **Alternatif**: intraday/realtime, tengah malam, atau pagi sebelum pasar buka.
- **Alasan**:
  - Data yang dibutuhkan adalah harga **harian** (OHLCV penutupan), yang baru final setelah sesi perdagangan dan pre-closing selesai sore hari.
  - Memberi jeda agar yfinance sempat memperbarui data hari itu.
  - Hasil sudah tersedia untuk dashboard pada malam hari yang sama.
  - Realtime tidak diperlukan untuk analisis harian dan jauh lebih kompleks.
- **Konsekuensi**:
  - Jika yfinance terlambat update, data hari itu belum lengkap. Karena run harian mengambil 7 hari terakhir dan load memakai upsert (#003),
    data tersebut otomatis terisi/terkoreksi pada run berikutnya.
  - GitHub Actions memakai UTC: 17:00 WIB = 10:00 UTC (`cron: "0 10 * * 1-5"`).
  - Hari libur bursa tetap memicu run, tapi tidak ada data baru. Ini bukan error.

## 006 – Parameter `hari_ini` pada `validasi()`
- **Keputusan**: `validasi(df, hari_ini=None)`. Jika kosong, memakai `date.today()`.
- **Alternatif**: memanggil `date.today()` langsung di dalam aturan.
- **Alasan**: test aturan `tanggal_masa_depan` harus memberi hasil yang sama kapan pun dijalankan (deterministik).
  Ini bentuk sederhana *dependency injection*.
- **Konsekuensi**: `main.py` tidak perlu berubah karena nilai default tetap hari ini.

## 007 – Harga disimpan mentah (`auto_adjust=False`)
- **Keputusan**: menyimpan harga apa adanya dari bursa, tidak disesuaikan corporate action.
- **Alternatif**: `auto_adjust=True` (harga historis disesuaikan untuk split/dividen).
- **Alasan**: harga mentah adalah harga yang benar-benar terjadi di bursa pada hari itu, sehingga cocok dibandingkan dengan batas ARB/ARA.
  Harga adjusted bisa berubah mundur setiap ada corporate action baru, sehingga upsert akan terus menimpa histori.
- **Konsekuensi**: return dan drawdown di Fase 4 akan terdistorsi pada tanggal split, dan `lonjakan_ekstrem` akan menandainya.
  Pertimbangkan menyimpan kolom adjusted close terpisah jika analisis return jangka panjang dibutuhkan.
