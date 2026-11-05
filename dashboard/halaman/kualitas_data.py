"""Kualitas data: riwayat run ETL (log_etl) dan isu validasi (data_quality_issue)."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import fmt
import ui
from db import query


def ke_wib(kolom: pd.Series) -> pd.Series:
    return pd.to_datetime(kolom, utc=True).dt.tz_convert("Asia/Jakarta").dt.tz_localize(None)


ui.kepala("Kualitas data", "Bukti setiap run ETL dan setiap pelanggaran aturan bisa ditelusuri")

run = query("""
    SELECT id AS run_id, mulai, selesai, status, tanggal_awal, tanggal_akhir,
           baris_diambil, baris_dimuat, jumlah_isu, pesan_error,
           EXTRACT(EPOCH FROM (selesai - mulai)) AS durasi_detik
    FROM log_etl ORDER BY id DESC
""")
isu = query("""
    SELECT run_id, kode, tanggal, aturan, keterangan, dicatat_pada
    FROM data_quality_issue ORDER BY id DESC
""")

if run.empty:
    st.info("Belum ada run ETL yang tercatat.")
    st.stop()

terakhir = run.iloc[0]
gagal = int((run["status"] == "gagal").sum())
ui.kotak_metrik([
    ui.metrik("Total run", fmt.angka(len(run)), f"Terakhir {fmt.tanggal(ke_wib(run['mulai']).iloc[0])}"),
    ui.metrik("Run gagal", fmt.angka(gagal), "Tidak ada" if gagal == 0 else "Perlu dicek", kelas_nilai="idx-turun" if gagal else ""),
    ui.metrik("Status terakhir", str(terakhir.status).capitalize(), f"{fmt.angka(terakhir.baris_dimuat)} baris dimuat",
              kelas_nilai={"sukses": "idx-naik", "gagal": "idx-turun"}.get(terakhir.status, "")),
    ui.metrik("Isu tercatat", fmt.angka(len(isu)), "Semua run",
              "Jumlah pelanggaran aturan validasi. Isu yang sama bisa tercatat lagi di run berikutnya."),
])
st.space("small")

ui.bagian("Riwayat run ETL", "Waktu dalam WIB")
tampil = run.assign(mulai=ke_wib(run["mulai"]), selesai=ke_wib(run["selesai"]), pesan_error=run["pesan_error"].fillna(fmt.KOSONG))
ui.tabel(tampil, {
    "run_id": ("Run", None),
    "mulai": ("Mulai", fmt.tanggal_waktu),
    "status": ("Status", None),
    "tanggal_awal": ("Data dari", fmt.tanggal),
    "tanggal_akhir": ("Data sampai", fmt.tanggal),
    "baris_diambil": ("Diambil", fmt.angka),
    "baris_dimuat": ("Dimuat", fmt.angka),
    "jumlah_isu": ("Isu", fmt.angka),
    "durasi_detik": ("Durasi", lambda x: f"{fmt.angka(x, 1)} dtk"),
    "pesan_error": ("Pesan error", None),
}, tinggi=320 if len(tampil) > 8 else None)

st.space("small")
kiri, kanan = st.columns([3, 2], gap="large")
with kiri:
    ui.bagian("Isu validasi")
    if isu.empty:
        st.success("Belum ada isu. Semua baris dari semua run lolos keenam aturan.")
    else:
        per_aturan = isu.groupby("aturan").size().sort_values()
        fig = go.Figure(go.Bar(x=per_aturan.values, y=per_aturan.index, orientation="h", marker_color=ui.AKSEN, marker_line_width=0,
                               text=per_aturan.values, textposition="outside", cliponaxis=False,
                               hovertemplate="<b>%{y}</b><br>%{x} isu<extra></extra>"))
        ui.rapikan_grafik(fig, 60 + 34 * len(per_aturan)).update_layout(bargap=0.35)
        fig.update_xaxes(visible=False)
        fig.update_yaxes(showgrid=False)
        ui.tampilkan_grafik(fig)
        ui.tabel(isu.assign(dicatat_pada=ke_wib(isu["dicatat_pada"])), {
            "run_id": ("Run", None),
            "tanggal": ("Tanggal data", fmt.tanggal),
            "kode": ("Kode", None),
            "aturan": ("Aturan", None),
            "keterangan": ("Keterangan", None),
        }, tinggi=320)
with kanan:
    ui.bagian("Aturan validasi di setiap run")
    st.html(
        '<table class="idx-tabel"><tr><th>Aturan</th><th>Perlakuan</th></tr>'
        "<tr><td>Tanggal masa depan</td><td>Dibuang, dicatat</td></tr>"
        "<tr><td>Harga tidak positif atau kosong</td><td>Dibuang, dicatat</td></tr>"
        "<tr><td>OHLC tidak konsisten</td><td>Dibuang, dicatat</td></tr>"
        "<tr><td>Volume negatif</td><td>Dibuang, dicatat</td></tr>"
        "<tr><td>Duplikat</td><td>Salinan pertama disimpan</td></tr>"
        "<tr><td>Lonjakan melebihi ARA/ARB</td><td>Disimpan, dicatat</td></tr></table>"
    )
