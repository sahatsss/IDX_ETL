-- Pertanyaan 6: berapa drawdown maksimum tiap saham?
--
-- Drawdown = seberapa jauh harga hari ini di bawah harga tertinggi yang pernah dicapai sebelumnya.
-- Drawdown maksimum = penurunan terdalam dari puncak ke dasar sepanjang periode data
-- ("kerugian terburuk jika membeli di puncak dan menjual di dasar").

-- 6a. Drawdown harian.
--   puncak_sebelumnya = harga tutup tertinggi dari awal data sampai hari ini.
--   drawdown          = 0 saat harga di puncak baru; -0.25 = 25% di bawah puncak.
CREATE OR REPLACE VIEW v_drawdown AS
WITH puncak AS (
    SELECT
        kode,
        tanggal,
        harga_tutup,
        MAX(harga_tutup) OVER (PARTITION BY kode ORDER BY tanggal
                               ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS puncak_sebelumnya
    FROM harga_harian
)
SELECT
    kode,
    tanggal,
    harga_tutup,
    puncak_sebelumnya,
    ROUND(harga_tutup / NULLIF(puncak_sebelumnya, 0) - 1, 6) AS drawdown
FROM puncak;

-- 6b. Drawdown maksimum per saham, beserta tanggal puncak dan dasarnya.
--   Catatan: harga mentah (auto_adjust=False), jadi stock split / spin-off ikut terbaca sebagai drawdown.
CREATE OR REPLACE VIEW v_drawdown_maksimum AS
WITH terdalam AS (
    -- Satu baris per saham: hari dengan drawdown paling negatif (jika seri, ambil yang paling awal).
    SELECT DISTINCT ON (kode)
        kode,
        tanggal           AS tanggal_dasar,
        harga_tutup       AS harga_dasar,
        puncak_sebelumnya AS harga_puncak,
        drawdown
    FROM v_drawdown
    ORDER BY kode, drawdown ASC, tanggal ASC
)
SELECT
    t.kode,
    t.drawdown AS drawdown_maksimum,
    (   -- tanggal puncak = hari terakhir sebelum dasar ketika harga mencapai harga_puncak
        SELECT MAX(h.tanggal)
        FROM harga_harian h
        WHERE h.kode = t.kode
          AND h.tanggal <= t.tanggal_dasar
          AND h.harga_tutup = t.harga_puncak
    ) AS tanggal_puncak,
    t.harga_puncak,
    t.tanggal_dasar,
    t.harga_dasar
FROM terdalam t;
