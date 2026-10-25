-- Pertanyaan 4: bagaimana ranking return per sektor per bulan?
--
-- Return bulanan = harga tutup terakhir bulan ini / harga tutup terakhir bulan lalu - 1.
--
-- Cara membaca (satu baris per saham per bulan):
--   peringkat_dalam_sektor = posisi saham dibanding saham lain di sektor yang sama (RANK).
--   rata_rata_sektor       = rata-rata return bulanan saham-saham di sektor itu.
--   peringkat_sektor       = posisi sektor dibanding sektor lain di bulan itu (DENSE_RANK).
--
-- Kenapa RANK vs DENSE_RANK:
--   Di dalam sektor, dua saham dengan return sama sama-sama peringkat 1, saham berikutnya 3 (RANK).
--   Untuk sektor, semua baris satu sektor punya rata_rata_sektor yang sama; dengan RANK, sektor
--   berikutnya akan "melompat" sejumlah saham di sektor sebelumnya (1, 5, 6, ...). DENSE_RANK
--   memberi 1, 2, 3, ... sehingga peringkat sektor tetap berurutan.
--
-- Catatan: bulan berjalan berisi return month-to-date (belum final).

CREATE OR REPLACE VIEW v_ranking_sektor_bulanan AS
WITH akhir_bulan AS (
    -- DISTINCT ON (khas PostgreSQL): ambil satu baris per (kode, bulan), yaitu baris pertama
    -- sesuai ORDER BY = tanggal paling akhir di bulan itu.
    SELECT DISTINCT ON (kode, DATE_TRUNC('month', tanggal))
        kode,
        DATE_TRUNC('month', tanggal)::date AS bulan,
        harga_tutup
    FROM harga_harian
    ORDER BY kode, DATE_TRUNC('month', tanggal), tanggal DESC
),
return_bulanan AS (
    SELECT
        kode,
        bulan,
        harga_tutup / NULLIF(LAG(harga_tutup) OVER (PARTITION BY kode ORDER BY bulan), 0) - 1 AS return_bulanan
    FROM akhir_bulan
),
dengan_sektor AS (
    SELECT
        r.bulan,
        COALESCE(e.sektor, 'Tanpa sektor') AS sektor,
        r.kode,
        r.return_bulanan,
        AVG(r.return_bulanan) OVER (PARTITION BY e.sektor, r.bulan) AS rata_rata_sektor,
        COUNT(*)              OVER (PARTITION BY e.sektor, r.bulan) AS jumlah_saham_sektor,
        RANK() OVER (PARTITION BY e.sektor, r.bulan ORDER BY r.return_bulanan DESC) AS peringkat_dalam_sektor
    FROM return_bulanan r
    JOIN emiten e USING (kode)
    WHERE r.return_bulanan IS NOT NULL      -- bulan pertama tiap saham tidak punya bulan pembanding
)
SELECT
    bulan,
    sektor,
    kode,
    ROUND(return_bulanan, 4)   AS return_bulanan,
    peringkat_dalam_sektor,
    jumlah_saham_sektor,
    ROUND(rata_rata_sektor, 4) AS rata_rata_sektor,
    DENSE_RANK() OVER (PARTITION BY bulan ORDER BY rata_rata_sektor DESC) AS peringkat_sektor
FROM dengan_sektor;
