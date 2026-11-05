-- Pertanyaan 7: bagaimana pergerakan umum saham LQ45 per hari?
--
-- Cara membaca (satu baris per hari bursa):
--   median_return = nilai tengah return harian semua saham; separuh saham di atas angka ini, separuh di bawahnya.
--                   Bukan indeks LQ45 resmi: setiap saham berbobot sama, tanpa bobot kapitalisasi pasar.
--   saham_naik / saham_turun / saham_tetap = jumlah saham menurut arah pergerakannya hari itu.
-- Butuh v_return_harian (01_return_harian.sql) sudah dibuat.

CREATE OR REPLACE VIEW v_pasar_harian AS
SELECT
    tanggal,
    ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY return_harian))::numeric, 6) AS median_return,
    COUNT(*) FILTER (WHERE return_harian > 0) AS saham_naik,
    COUNT(*) FILTER (WHERE return_harian < 0) AS saham_turun,
    COUNT(*) FILTER (WHERE return_harian = 0) AS saham_tetap
FROM v_return_harian
WHERE return_harian IS NOT NULL
GROUP BY tanggal;
