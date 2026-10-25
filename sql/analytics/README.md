# Query analitik

Setiap file membuat satu atau lebih **view** (`CREATE OR REPLACE VIEW`), sehingga dashboard dan analisis
cukup menjalankan `SELECT * FROM v_...`. Di atas setiap file ada komentar tentang pertanyaan yang dijawab
dan cara membaca hasilnya.

| File | View | Pertanyaan |
|---|---|---|
| `01_return_harian.sql` | `v_return_harian` | Return harian dan kumulatif per saham |
| `02_moving_average.sql` | `v_moving_average` | MA20, MA50, dan crossover (golden/death cross) |
| `03_volatilitas.sql` | `v_volatilitas`, `v_volatilitas_bulanan` | Volatilitas 30 hari bergulir; saham paling volatil per bulan |
| `04_ranking_sektor.sql` | `v_ranking_sektor_bulanan` | Ranking return bulanan dalam sektor dan antar sektor |
| `05_volume_spike.sql` | `v_volume_spike` | Hari dengan volume > 3x rata-rata 20 hari sebelumnya |
| `06_drawdown.sql` | `v_drawdown`, `v_drawdown_maksimum` | Drawdown harian dan drawdown maksimum per saham |

## Membuat / memperbarui view
Jalankan berurutan (file 03 dan 05 memakai `v_return_harian` dari file 01):

```bash
for f in sql/analytics/0*.sql; do docker compose exec -T db psql -U idx -d idx -v ON_ERROR_STOP=1 -q < "$f"; done
```

PowerShell:
```powershell
Get-ChildItem sql/analytics/0*.sql | ForEach-Object { Get-Content $_ -Raw | docker compose exec -T db psql -U idx -d idx -v ON_ERROR_STOP=1 -q }
```

Catatan: `CREATE OR REPLACE VIEW` tidak bisa menghapus/mengganti urutan kolom. Jika struktur kolom diubah,
jalankan `DROP VIEW nama_view CASCADE;` dulu (CASCADE ikut menghapus view yang bergantung padanya, lalu buat ulang semua).

## Konsep yang dipakai
- `LAG()` / `FIRST_VALUE()` dengan `PARTITION BY kode ORDER BY tanggal`: nilai baris sebelumnya / pertama per saham.
- Window frame `ROWS BETWEEN n PRECEDING AND CURRENT ROW`: moving average, volatilitas, puncak berjalan.
- `RANK()` vs `DENSE_RANK()`: lihat komentar di `04_ranking_sektor.sql`.
- `DISTINCT ON` (khas PostgreSQL): ambil satu baris per grup sesuai `ORDER BY`.
- Hari libur bursa bukan "baris hilang": 20 baris = 20 hari bursa, bukan 20 hari kalender.
