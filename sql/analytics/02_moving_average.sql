-- Pertanyaan 2: berapa moving average 20 dan 50 hari, dan kapan terjadi crossover?
--
-- Cara membaca:
--   ma20 / ma50 = rata-rata harga tutup 20 / 50 hari bursa terakhir (termasuk hari ini).
--                 NULL jika data saham itu belum cukup 20 / 50 hari.
--   crossover   = 'golden_cross' saat ma20 naik menembus ma50 (sinyal tren naik),
--                 'death_cross'  saat ma20 turun menembus ma50 (sinyal tren turun),
--                 NULL di hari lainnya.
--
-- Contoh: SELECT * FROM v_moving_average WHERE crossover IS NOT NULL ORDER BY tanggal DESC;

CREATE OR REPLACE VIEW v_moving_average AS
WITH rata_rata AS (
    SELECT
        kode,
        tanggal,
        harga_tutup,
        AVG(harga_tutup) OVER (PARTITION BY kode ORDER BY tanggal
                               ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS ma20_mentah,
        AVG(harga_tutup) OVER (PARTITION BY kode ORDER BY tanggal
                               ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) AS ma50_mentah,
        ROW_NUMBER()     OVER (PARTITION BY kode ORDER BY tanggal)        AS urutan
    FROM harga_harian
),
rata_rata_valid AS (
    -- Window di awal data berisi kurang dari 20/50 baris; AVG tetap menghitung dari baris yang ada.
    -- Nilai itu menyesatkan, jadi dikosongkan sampai jumlah barisnya cukup.
    SELECT
        kode,
        tanggal,
        harga_tutup,
        CASE WHEN urutan >= 20 THEN ma20_mentah END AS ma20,
        CASE WHEN urutan >= 50 THEN ma50_mentah END AS ma50
    FROM rata_rata
),
posisi AS (
    -- SIGN: 1 jika ma20 di atas ma50, -1 jika di bawah. Crossover = posisinya berbalik dari kemarin.
    SELECT
        *,
        SIGN(ma20 - ma50) AS posisi_hari_ini,
        LAG(SIGN(ma20 - ma50)) OVER (PARTITION BY kode ORDER BY tanggal) AS posisi_kemarin
    FROM rata_rata_valid
)
SELECT
    kode,
    tanggal,
    harga_tutup,
    ROUND(ma20, 2) AS ma20,
    ROUND(ma50, 2) AS ma50,
    CASE
        WHEN posisi_hari_ini = 1  AND posisi_kemarin = -1 THEN 'golden_cross'
        WHEN posisi_hari_ini = -1 AND posisi_kemarin = 1  THEN 'death_cross'
    END AS crossover
FROM posisi;
