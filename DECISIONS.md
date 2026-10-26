# Catatan Keputusan Desain

Format: keputusan → alternatif yang dipertimbangkan → alasan → konsekuensi.
Ini yang akan kamu baca ulang sebelum wawancara.

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
  - Seluruh batch dimuat dalam satu transaksi (`commit` / `rollback`, lihat #012): jika gagal, tidak ada data setengah jadi.
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
- **Batas ARA/ARB untuk `lonjakan_ekstrem`: mengikuti periode aturan BEI** (`PERIODE_AUTO_REJECTION` di `validate.py`).
  - Batas dipilih berdasarkan **tanggal transaksi**, **harga acuan** (tutup kemarin), dan **arah** (naik → ARA, turun → ARB),
    ditambah toleransi 1% untuk pembulatan fraksi harga.

    | Berlaku mulai | Rp1–Rp10 | Rp11/50–≤Rp200 | >Rp200–≤Rp5.000 | >Rp5.000 | Sumber |
    |---|---|---|---|---|---|
    | 4 Sep 2023 | – | 35% / 35% | 25% / 25% | 20% / 20% | ketentuan BEI/OJK saat itu* |
    | 8 Apr 2025 | – | 35% / 15% | 25% / 15% | 20% / 15% | ketentuan BEI/OJK saat itu*; disebut "saat ini" di SP 083 |
    | 28 Sep 2026 | Rp1 / Rp1 | 35% / 15% | 25% / 15% | 20% / 15% | SP 083 |
    | 1 Jan 2027 | Rp1 / Rp1 | 35% / 35% | 25% / 25% | 20% / 20% | SP 083 |

    (format: ARA / ARB)
  - **Acuan utama**: Siaran Pers BEI No. 083/BEI.SPR/09-2026 ("SP 083"), 21 Sep 2026
    (SK Direksi BEI Kep-00136/BEI/09-2026, perubahan Peraturan II-A),
    https://www.idx.co.id/id/berita/siaran-pers/2704.
  - \* **Periode sebelum 28 Sep 2026** mengikuti ketentuan BEI/OJK yang berlaku saat itu. Dokumen spesifik untuk tanggal
    4 Sep 2023 dan 8 Apr 2025 belum dicantumkan, tapi batasnya **didukung data**: jika ARB 15% diterapkan ke semua tanggal,
    muncul 11 penurunan 16–25% (mis. ADRO −24,8% pada 28 Nov 2024), dan **semuanya sebelum Maret 2025**. Sejak April 2025
    tidak ada satu pun penurunan > 15%, sehingga konsisten dengan ARB simetris sebelum 2025 dan ARB 15% sesudahnya.
  - **Alternatif yang ditolak**:
    - Satu batas simetris terluas untuk semua tanggal: tidak pernah salah menandai, tapi penurunan 16–25% di periode ARB 15% lolos.
    - Hanya aturan terbaru untuk semua tanggal: data historis yang sah (mis. ADRO −24,8% pada Nov 2024, saat ARB masih 25%) salah ditandai.
  - Batas rentang memakai `>` sesuai teks aturan (">Rp200 – ≤Rp5.000"): harga acuan tepat Rp5.000 memakai 25%, bukan 20%.
  - Rentang Rp1–Rp10 memakai batas nominal Rp1, sehingga dikonversi menjadi persentase `1 / harga_acuan`.
  - Hasil uji pada 32.521 baris (Okt 2023 – Okt 2026, 45 saham): 0 isu, sehingga tidak ada data sah yang salah ditandai.

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

## 008 – Query analitik disimpan sebagai VIEW
- **Keputusan**: setiap file di `sql/analytics/` membuat view (`CREATE OR REPLACE VIEW v_...`), total 8 view dari 6 file.
- **Alternatif**:
  - File `.sql` berisi `SELECT` biasa yang dijalankan manual: sederhana, tapi dashboard harus membaca file atau menyalin query.
  - Materialized view / tabel hasil: lebih cepat dibaca, tapi harus di-refresh setiap selesai ETL dan bisa basi.
  - Hitung di pandas: logika analitik tersebar di Python, tidak bisa dipakai ulang dari psql atau tool lain.
- **Alasan**:
  - Logika analitik tersimpan **di database**, satu tempat; dashboard cukup `SELECT * FROM v_...`.
  - View dihitung ulang setiap dipanggil, sehingga **otomatis ikut ter-update** setiap kali ETL memuat data baru, tanpa langkah refresh.
  - View bisa dibangun di atas view lain (`v_volatilitas` dan `v_volume_spike` memakai `v_return_harian`),
    sehingga rumus return hanya ditulis sekali.
- **Konsekuensi**:
  - Setiap query membaca ulang `harga_harian`. Pada 32.521 baris semua view masih < 260 ms; jika data jauh lebih besar,
    pertimbangkan materialized view.
  - `CREATE OR REPLACE VIEW` tidak bisa mengubah/menghapus kolom yang sudah ada. Perubahan struktur kolom butuh
    `DROP VIEW ... CASCADE` lalu membuat ulang view yang bergantung.
  - View harus dibuat ulang di database baru (mis. database cloud di Fase 6), karena tidak dibuat otomatis oleh skema awal.

## 009 – Definisi return: simple return
- **Keputusan**: `return = harga_tutup / harga_tutup_kemarin − 1`; kumulatif = `harga_tutup / harga_tutup_pertama − 1`.
- **Alternatif**: log return `ln(harga_tutup / harga_tutup_kemarin)`.
- **Alasan**:
  - Paling mudah dibaca dan dijelaskan: 0,05 = naik 5%. Ini juga angka yang dilihat investor di aplikasi sekuritas.
  - Return kumulatif dan return bulanan cukup dihitung dari dua harga (awal dan akhir), tanpa menjumlahkan return harian.
- **Konsekuensi**:
  - Simple return tidak bisa dijumlahkan antar hari (+10% lalu −10% ≠ 0%). Log return bisa dijumlahkan dan lebih umum di
    model statistik, tapi untuk return harian yang kecil, selisih keduanya tidak signifikan.
  - Volatilitas (#03) memakai standar deviasi simple return harian; disetahunkan dengan × √252.
  - "Kemarin" = hari bursa sebelumnya (baris sebelumnya), bukan hari kalender.

## 010 – Daftar saham: konstituen LQ45 resmi
- **Keputusan**: 45 konstituen LQ45 periode 3 Agu – 30 Okt 2026, dari Lampiran 2 Pengumuman BEI
  No. Peng-00148/BEI.POP/07-2026 (27 Jul 2026), diunduh dari halaman Indeks Saham idx.co.id.
  Daftar ini dipakai sementara; diperbarui saat BEI mengumumkan konstituen periode berikutnya.
- **Alternatif**:
  - Memilih sendiri ±40 saham besar: cepat, tapi sulit dipertanggungjawabkan ("kenapa saham ini?").
  - Seluruh saham IDX (±900): kebanyakan tidak likuid, data yfinance sering bolong.
  - Menyimpan histori keanggotaan indeks per periode (tabel baru): paling akurat, tapi butuh data historis LQ45 dan perubahan skema.
- **Alasan**:
  - LQ45 dipilih BEI berdasarkan likuiditas dan kapitalisasi pasar, dievaluasi berkala: kriteria yang objektif dan bisa ditelusuri.
  - Saham likuid punya data harian yang lebih lengkap dan jarang berisi volume 0.
- **Konsekuensi**:
  - **Survivorship bias**: daftar terbaru dipakai untuk seluruh 3 tahun. Saham yang sudah keluar dari indeks
    (mis. SMGR, TOWR) tidak dianalisis, sedangkan saham yang baru masuk (mis. INDY, NCKL) ikut dianalisis sejak 2023
    walaupun dulu belum termasuk LQ45. Hasil analisis bisa terlihat lebih baik dari kenyataan.
  - Saham yang listing belakangan punya data lebih pendek (AADI mulai 5 Des 2024). Ini bukan data hilang.
  - Lampiran BEI hanya memuat kode saham; nama dan sektor (klasifikasi IDX-IC) diisi terpisah di `config/tickers.csv`.
  - Saat konstituen diperbarui, saham yang keluar tetap ada di database (datanya tidak dihapus); cukup ubah `tickers.csv`.

## 011 – Extract: unduhan per batch + retry
- **Keputusan**: `yf.download` dipanggil untuk 20 ticker sekaligus (`UKURAN_BATCH`). Ticker yang hasilnya kosong atau error
  dicoba ulang maksimal 3 kali dengan jeda 2 lalu 4 detik (*exponential backoff*); yang tetap kosong dicatat di log lalu dilewati.
- **Alternatif**:
  - Loop satu ticker per panggilan (versi Fase 1): mudah dipahami, tapi 45 panggilan dan tanpa ketahanan terhadap gagal sementara.
  - Satu panggilan untuk semua 45 ticker: paling sedikit panggilan, tapi satu kegagalan bisa mengenai semuanya.
- **Alasan**:
  - Lebih sedikit panggilan jaringan: 45 ticker = 3 batch. Extract 3 tahun × 45 saham selesai ±6 detik.
  - Gangguan sementara (timeout, rate limit) tidak langsung menggagalkan run; hanya ticker yang gagal yang diulang.
  - Backoff memberi waktu server pulih, alih-alih langsung membanjiri dengan permintaan ulang.
- **Konsekuensi**:
  - Hasil batch memakai gabungan tanggal semua ticker. Tanggal ketika suatu ticker tidak punya data (mis. AADI sebelum listing)
    muncul sebagai baris NaN. Baris ini adalah **artefak penggabungan, bukan data rusak**, jadi dibuang di `extract.py`;
    jika dibiarkan, validasi akan mencatat ratusan isu `harga_tidak_positif` palsu dan audit trail tercemar.
  - Ticker yang tetap kosong hanya muncul di log, belum dicatat di `data_quality_issue`.
  - Diuji tanpa internet di `tests/test_extract.py` (yfinance diganti fungsi palsu dengan `monkeypatch`).

## 012 – Load: `psycopg2.extras.execute_values`
- **Keputusan**: `muat_harga` mengirim baris per halaman 1.000 baris (`VALUES %s`), memakai SQL upsert yang sama (#003).
- **Pengukuran sebelum memutuskan** (32.521 baris, DB lokal): extract 5,9 s, validasi 0,3 s, **load 62,3 s**. Bottleneck ada di load.
  Penyebabnya bukan PostgreSQL, tapi **round trip**: cara lama mengirim satu perintah INSERT per baris (32.521 kali bolak-balik).
- **Alternatif**:
  - SQLAlchemy Core `insert().on_conflict_do_update()` (batching *insertmanyvalues*): tetap di abstraksi SQLAlchemy,
    tapi perlu definisi `Table` yang selaras dengan skema SQL.
  - `COPY` ke tabel staging lalu `INSERT ... SELECT ... ON CONFLICT`: paling cepat dan skalabel, tapi kode paling rumit
    dan berlebihan untuk skala ini.
- **Alasan**: perubahan paling kecil (SQL upsert tidak berubah), tanpa dependency baru (psycopg2 sudah dipakai),
  dan cukup cepat: load turun dari 62 s ke ±4 s (≈15×), yang penting saat database pindah ke cloud (round trip lebih mahal).
- **Konsekuensi**:
  - Butuh `engine.raw_connection()` karena `execute_values` fitur driver psycopg2, bukan SQLAlchemy; transaksi ditulis eksplisit
    (`commit` jika semua halaman sukses, `rollback` jika ada error).
  - **Syarat baru**: dalam satu perintah tidak boleh ada `(kode, tanggal)` ganda, karena PostgreSQL menolak
    `ON CONFLICT DO UPDATE` yang mengenai baris sama dua kali dan seluruh transaksi batal. Aturan `duplikat` (#004)
    menjamin syarat ini, sehingga kontrol kualitas data menjadi prasyarat teknis load.
  - Idempotency tetap terbukti: load dijalankan dua kali, `count(*)` tetap 32.521.
  - Tidak menambah index: primary key `(kode, tanggal)` sudah menjadi index yang sesuai pola `PARTITION BY kode ORDER BY tanggal`,
    dan semua view < 260 ms.
