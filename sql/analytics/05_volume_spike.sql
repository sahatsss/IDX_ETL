-- Pertanyaan 5: hari apa saja volume perdagangan melonjak > 3x rata-rata 20 hari?
--
-- Cara membaca (hanya berisi hari yang terjadi lonjakan):
--   rata_volume_20h = rata-rata volume 20 hari bursa SEBELUMNYA (hari ini tidak ikut dihitung,
--                     supaya lonjakan hari ini tidak ikut menaikkan pembandingnya sendiri).
--   rasio           = volume hari ini / rata_volume_20h (3.50 = 3,5x lebih ramai dari biasanya).
--   return_harian   = arah harga di hari itu, untuk melihat lonjakan volume terjadi saat naik atau turun.
--
-- Contoh: SELECT * FROM v_volume_spike ORDER BY rasio DESC LIMIT 10;

CREATE OR REPLACE VIEW v_volume_spike AS
WITH volume_historis AS (
    SELECT
        kode,
        tanggal,
        volume,
        AVG(volume)   OVER w20 AS rata_volume_20h,
        COUNT(volume) OVER w20 AS jumlah_hari
    FROM harga_harian
    WINDOW w20 AS (PARTITION BY kode ORDER BY tanggal ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING)
)
SELECT
    v.kode,
    v.tanggal,
    v.volume,
    ROUND(v.rata_volume_20h)                               AS rata_volume_20h,
    ROUND(v.volume / NULLIF(v.rata_volume_20h, 0), 2)      AS rasio,
    r.return_harian
FROM volume_historis v
JOIN v_return_harian r USING (kode, tanggal)
WHERE v.jumlah_hari = 20                    -- abaikan 20 hari pertama: pembandingnya belum lengkap
  AND v.volume > 3 * v.rata_volume_20h;
