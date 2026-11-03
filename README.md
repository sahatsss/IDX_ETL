# IDX Stock Data Pipeline

Pipeline ETL harian untuk data harga saham Bursa Efek Indonesia (IDX) ke PostgreSQL, dengan validasi kualitas data dan query analitik.

## Tujuan proyek
1. Membangun ETL yang **idempotent** (aman dijalankan ulang tanpa duplikasi data).
2. Menerapkan **kontrol kualitas data** yang terdokumentasi (mirip kontrol di audit IT).
3. Menulis **query analitik SQL** (CTE, window function) untuk menjawab pertanyaan nyata.
4. Menyajikan hasil di dashboard sederhana dan menjalankan pipeline secara terjadwal.

## Arsitektur (rencana)
```
yfinance (.JK)  ──►  extract  ──►  validate  ──►  load (upsert)  ──►  PostgreSQL
                                      │                                  │
                                      └──► data_quality_issue            ├──► sql/analytics/*.sql
                                                                         └──► dashboard (Streamlit)
```

## Menjalankan
```bash
cp .env.example .env
docker compose up -d                 # PostgreSQL + skema otomatis dibuat
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m idx_pipeline.main --start 2023-01-01   # backfill
python -m idx_pipeline.main                      # load harian (default: 7 hari terakhir)
```
(Jalankan dari folder `src/` atau set `PYTHONPATH=src`.)

Membuat/memperbarui tabel dan view analitik (aman diulang), lalu membuka dashboard:
```bash
python -m idx_pipeline.setup_db
python -m streamlit run dashboard/app.py        # buka http://localhost:8501
```

## Deploy (database cloud + jadwal + dashboard online)
```
GitHub Actions (cron 17:00 WIB) ──► ETL ──► Neon (PostgreSQL cloud) ◄── Streamlit Community Cloud (dashboard)
```
1. **Neon**: buat proyek di https://neon.tech (region Singapore), salin connection string `postgresql://...?sslmode=require`.
2. **Isi database cloud dari nol** (dari laptop, sekali saja). PowerShell:
   ```powershell
   $env:PYTHONPATH="src"; $env:DATABASE_URL="<connection string Neon>"
   python -m idx_pipeline.setup_db
   python -m idx_pipeline.main --start 2023-10-01
   Remove-Item Env:DATABASE_URL          # kembali ke database lokal
   ```
3. **GitHub Actions**: repo → Settings → Secrets and variables → Actions → New repository secret
   `DATABASE_URL` = connection string Neon. Workflow `.github/workflows/etl.yml` berjalan Senin–Jumat 17:00 WIB
   (test dulu, lalu ETL); bisa juga dijalankan manual dari tab Actions → "ETL harian" → Run workflow.
4. **Streamlit Community Cloud**: https://share.streamlit.io → New app → repo ini, branch `main`,
   main file `dashboard/app.py` → Advanced settings → Secrets:
   ```toml
   DATABASE_URL = "<connection string Neon>"
   ```

## Roadmap
- [ ] **Fase 1 – Fondasi**: Docker + PostgreSQL jalan, skema dibuat, ETL bisa load 10 saham.
- [ ] **Fase 2 – Idempotency & logging**: jalankan ETL 2x untuk tanggal yang sama → jumlah baris tidak berubah. Setiap run tercatat di `log_etl`.
- [ ] **Fase 3 – Validasi data**: implementasikan aturan di `validate.py` (lihat TODO), simpan temuan ke `data_quality_issue`.
- [ ] **Fase 4 – Analitik SQL**: tulis query di `sql/analytics/` (lihat daftar pertanyaan di bawah).
- [ ] **Fase 5 – Perluas data**: ±40 saham, backfill ≥3 tahun, isi sektor emiten.
- [ ] **Fase 6 – Dashboard & jadwal**: Streamlit + GitHub Actions/cron.
- [ ] **Fase 7 – Dokumentasi akhir**: hasil, keterbatasan, apa yang akan diperbaiki.

## Pertanyaan analitik yang harus dijawab dengan SQL
1. Return harian dan kumulatif per saham.
2. Moving average 20 dan 50 hari; kapan terjadi crossover?
3. Volatilitas 30 hari bergulir; saham mana paling volatil per bulan?
4. Ranking return per sektor per bulan (`RANK()` / `DENSE_RANK()`).
5. Hari dengan volume > 3× rata-rata 20 hari (volume spike).
6. Drawdown maksimum per saham.

## Keterbatasan yang sudah diketahui
- Data yfinance tidak resmi; bisa ada tanggal hilang atau penyesuaian harga (corporate action).
- Daftar saham di `config/tickers.csv` hanya contoh — komposisi LQ45 berubah tiap periode, verifikasi sendiri.

## Menjalankan Conda

- Masuk ke direktori projek IDX_ETL
- jalankan `conda activate idx-etl`