-- Pertanyaan 1: berapa return harian dan return kumulatif tiap saham?
--
-- Cara membaca:
--   return_harian    = perubahan harga tutup dibanding hari bursa sebelumnya (0.0150 = naik 1,5%).
--                      NULL di baris pertama tiap saham karena belum ada hari sebelumnya.
--   return_kumulatif = perubahan sejak tanggal pertama yang ada di database untuk saham itu.
--
-- Definisi: simple return = tutup / tutup_kemarin - 1 (lihat DECISIONS.md).
-- "Kemarin" = baris sebelumnya (hari bursa), bukan hari kalender; hari libur tidak ada di tabel.
-- Harga mentah (auto_adjust=False): return di tanggal stock split / spin-off akan terdistorsi.

CREATE OR REPLACE VIEW v_return_harian AS
WITH dasar AS (
    SELECT
        kode,
        tanggal,
        harga_tutup,
        LAG(harga_tutup)         OVER w AS tutup_kemarin,
        FIRST_VALUE(harga_tutup) OVER w AS tutup_pertama
    FROM harga_harian
    WINDOW w AS (PARTITION BY kode ORDER BY tanggal)
)
SELECT
    kode,
    tanggal,
    harga_tutup,
    tutup_kemarin,
    ROUND(harga_tutup / NULLIF(tutup_kemarin, 0) - 1, 6) AS return_harian,
    ROUND(harga_tutup / NULLIF(tutup_pertama, 0) - 1, 6) AS return_kumulatif
FROM dasar;
