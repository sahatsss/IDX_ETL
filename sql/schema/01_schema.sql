-- Skema awal IDX pipeline.
-- Dijalankan otomatis oleh container Postgres saat volume database masih kosong.
-- Kalau skema diubah: `docker compose down -v` lalu `up -d` (menghapus data!) atau buat file migrasi baru.

CREATE TABLE IF NOT EXISTS emiten (
    kode        VARCHAR(10) PRIMARY KEY,          -- tanpa akhiran .JK
    nama        TEXT,
    sektor      TEXT,
    dibuat_pada TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS harga_harian (
    kode          VARCHAR(10) NOT NULL REFERENCES emiten(kode),
    tanggal       DATE        NOT NULL,
    harga_buka    NUMERIC(14,2),
    harga_tertinggi NUMERIC(14,2),
    harga_terendah  NUMERIC(14,2),
    harga_tutup   NUMERIC(14,2),
    volume        BIGINT,
    sumber        TEXT        NOT NULL DEFAULT 'yfinance',
    dimuat_pada   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (kode, tanggal)                   -- lihat DECISIONS.md #002
);

CREATE TABLE IF NOT EXISTS log_etl (
    id            BIGSERIAL PRIMARY KEY,
    mulai         TIMESTAMPTZ NOT NULL DEFAULT now(),
    selesai       TIMESTAMPTZ,
    status        TEXT NOT NULL DEFAULT 'running',   -- running | sukses | gagal
    tanggal_awal  DATE,
    tanggal_akhir DATE,
    baris_diambil INTEGER,
    baris_dimuat  INTEGER,
    jumlah_isu    INTEGER,
    pesan_error   TEXT
);

CREATE TABLE IF NOT EXISTS data_quality_issue (
    id          BIGSERIAL PRIMARY KEY,
    run_id      BIGINT REFERENCES log_etl(id),
    kode        VARCHAR(10),
    tanggal     DATE,
    aturan      TEXT NOT NULL,      -- nama aturan validasi, mis. 'harga_tidak_positif'
    keterangan  TEXT,
    dicatat_pada TIMESTAMPTZ NOT NULL DEFAULT now()
);
