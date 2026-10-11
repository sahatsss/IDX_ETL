# Instruksi untuk Claude Code

## Konteks
Ini proyek **portofolio** milik Sahat (mahasiswa Teknik Komputer, fokus data/ML, melamar posisi tech risk & data).
Tujuannya bukan sekadar kode yang jalan, tapi **pemilik proyek harus bisa menjelaskan setiap keputusan di wawancara.**

## Aturan kerja (penting)
1. **Jangan menulis query analitik SQL di `sql/analytics/` atau aturan validasi di `validate.py` secara utuh.**
   Itu bagian yang harus ditulis sendiri oleh pemilik. Boleh: memberi petunjuk, menjelaskan konsep
   (window function, CTE), me-review, menunjukkan bug, atau memberi contoh di tabel lain yang tidak terkait.
2. Untuk boilerplate (config, logging, Docker, test setup, CLI, CI) boleh langsung ditulis.
3. Setiap kali ada keputusan desain (skema, library, strategi load), **tanyakan dulu atau tawarkan opsi + trade-off**,
   jangan langsung memutuskan. Ingatkan untuk mencatat keputusan di `DECISIONS.md`.
4. Jelaskan perubahan secara singkat setelah mengedit file: apa yang berubah dan kenapa.
5. Jangan menambah dependency baru tanpa menyebutkannya.

## Stack
- Python 3.11+, pandas, yfinance, SQLAlchemy + psycopg2
- PostgreSQL 16 (via Docker Compose)
- Test: pytest

## Konvensi
- Kode di `src/idx_pipeline/`, SQL skema di `sql/schema/`, query analitik di `sql/analytics/`.
- Nama tabel & kolom: bahasa Indonesia, snake_case (mengikuti skema yang ada).
- Load ke database harus **idempotent** (upsert `ON CONFLICT`).
- Kode saham disimpan tanpa akhiran `.JK` di database; akhiran hanya dipakai saat memanggil yfinance.

## Perintah
- Jalankan DB: `docker compose up -d`
- Jalankan ETL: `PYTHONPATH=src python -m idx_pipeline.main --start 2024-01-01`
- Test: `PYTHONPATH=src pytest`
- Masuk psql: `docker compose exec db psql -U idx -d idx`
