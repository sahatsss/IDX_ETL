-- Pertanyaan 3: berapa volatilitas 30 hari bergulir, dan saham mana paling volatil tiap bulan?
--
-- Volatilitas = standar deviasi return harian. Makin besar, makin liar pergerakan harganya.
-- Butuh v_return_harian (01_return_harian.sql) sudah dibuat.

-- 3a. Volatilitas 30 hari bergulir, per saham per hari.
--   volatilitas_30h         = stddev 30 return harian terakhir (skala harian, 0.02 = 2% per hari).
--   volatilitas_30h_tahunan = disetahunkan dengan x akar(252), konvensi ±252 hari bursa per tahun.
--   NULL jika belum ada 30 return (= 31 hari bursa, karena return hari pertama NULL).
CREATE OR REPLACE VIEW v_volatilitas AS
WITH bergulir AS (
    SELECT
        kode,
        tanggal,
        return_harian,
        STDDEV_SAMP(return_harian) OVER (PARTITION BY kode ORDER BY tanggal
                                         ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS stddev_mentah,
        COUNT(return_harian)       OVER (PARTITION BY kode ORDER BY tanggal
                                         ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS jumlah_return
    FROM v_return_harian
)
SELECT
    kode,
    tanggal,
    return_harian,
    ROUND(stddev_mentah, 6)              AS volatilitas_30h,
    ROUND(stddev_mentah * SQRT(252::numeric), 4) AS volatilitas_30h_tahunan   -- ::numeric: ROUND(x, n) hanya untuk tipe numeric
FROM bergulir
WHERE jumlah_return = 30;

-- 3b. Saham paling volatil tiap bulan.
--   Volatilitas bulanan = stddev return harian di dalam bulan kalender itu.
--   peringkat 1 = paling volatil di bulan tersebut.
--   Bulan dengan kurang dari 10 return diabaikan (mis. bulan pertama data / bulan berjalan yang baru mulai).
CREATE OR REPLACE VIEW v_volatilitas_bulanan AS
WITH per_bulan AS (
    SELECT
        kode,
        DATE_TRUNC('month', tanggal)::date AS bulan,
        STDDEV_SAMP(return_harian)         AS volatilitas,
        COUNT(return_harian)               AS jumlah_hari
    FROM v_return_harian
    GROUP BY kode, DATE_TRUNC('month', tanggal)
)
SELECT
    bulan,
    kode,
    ROUND(volatilitas, 6) AS volatilitas,
    jumlah_hari,
    RANK() OVER (PARTITION BY bulan ORDER BY volatilitas DESC) AS peringkat
FROM per_bulan
WHERE jumlah_hari >= 10;
