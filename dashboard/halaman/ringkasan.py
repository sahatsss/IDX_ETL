"""Ringkasan: kondisi pasar pada hari bursa terakhir dan pergerakan 30 hari bursa."""
import plotly.graph_objects as go
import streamlit as st

import fmt
import ui
from db import query

HARI_GRAFIK = 30
BATAS_EKSTREM = 0.04     # |median| >= 4%: sekitar 2% hari bursa sejak Okt 2023

ui.kepala("Ringkasan pasar", "Kondisi 45 saham LQ45 pada hari bursa terakhir")

saham = query("""
    WITH akhir AS (
        SELECT DISTINCT ON (kode) kode, tanggal, harga_tutup, return_harian
        FROM v_return_harian
        ORDER BY kode, tanggal DESC
    ),
    awal_tahun AS (   -- harga tutup terakhir tahun lalu, sebagai dasar return YTD
        SELECT DISTINCT ON (kode) kode, harga_tutup AS tutup_awal_tahun
        FROM harga_harian
        WHERE tanggal < date_trunc('year', (SELECT max(tanggal) FROM harga_harian))
        ORDER BY kode, tanggal DESC
    )
    SELECT a.kode, e.nama, e.sektor, a.tanggal, a.harga_tutup, a.return_harian,
           a.harga_tutup / NULLIF(y.tutup_awal_tahun, 0) - 1 AS return_ytd
    FROM akhir a
    JOIN emiten e USING (kode)
    LEFT JOIN awal_tahun y USING (kode)
""")
pasar = query("SELECT * FROM v_pasar_harian ORDER BY tanggal")
lonjakan = query("""
    SELECT DISTINCT kode FROM v_volume_spike
    WHERE tanggal > (SELECT max(tanggal) - 7 FROM harga_harian)
    ORDER BY kode
""")

if pasar.empty or saham.empty:
    st.info("Belum ada data harga. Jalankan ETL terlebih dahulu.")
    st.stop()

hari_ini = pasar.iloc[-1]
terakhir = pasar.tail(HARI_GRAFIK)
terlemah = saham.nsmallest(1, "return_harian").iloc[0]
daftar_lonjakan = lonjakan["kode"].tolist()

ui.kotak_metrik([
    ui.metrik("Naik / turun", f"{hari_ini.saham_naik} / {hari_ini.saham_turun}", f"{hari_ini.saham_tetap} saham tetap"),
    ui.metrik("Median return", fmt.persen(hari_ini.median_return),
              fmt.posisi_hari(hari_ini.median_return, terakhir["median_return"]),
              f"Nilai tengah return harian semua saham, tanggal {fmt.tanggal(hari_ini.tanggal)}. "
              f"Posisinya dibandingkan dengan {len(terakhir)} hari bursa terakhir.",
              kelas_nilai=ui.kelas_arah(hari_ini.median_return)),
    ui.metrik("Turun terbesar", terlemah.kode if terlemah.return_harian < 0 else "Tidak ada",
              fmt.persen(terlemah.return_harian) if terlemah.return_harian < 0 else "", kelas_ket="idx-turun"),
    ui.metrik("Lonjakan volume", f"{len(daftar_lonjakan)} saham",
              ", ".join(daftar_lonjakan[:3]) + (f" +{len(daftar_lonjakan) - 3}" if len(daftar_lonjakan) > 3 else "") or "Tidak ada",
              "Saham dengan volume lebih dari 3 kali rata-rata 20 hari bursa sebelumnya, dalam 7 hari terakhir."),
])

st.space("small")
ui.bagian("Pergerakan umum saham LQ45 per hari", f"Median return harian, {len(terakhir)} hari bursa terakhir")
porsi_ekstrem = (pasar["median_return"].abs() >= BATAS_EKSTREM).mean()
ui.legenda([
    ([ui.NAIK, ui.TURUN], f"Ekstrem: ±4% atau lebih, {fmt.persen(porsi_ekstrem, 0, tanda=False)} hari bursa sejak {fmt.bulan_pendek(pasar['tanggal'].iloc[0])}"),
    ([ui.NAIK_LEMBUT, ui.TURUN_LEMBUT], "Biasa"),
])

ekstrem = terakhir["median_return"].abs() >= BATAS_EKSTREM
warna = [(ui.NAIK if m >= 0 else ui.TURUN) if e else (ui.NAIK_LEMBUT if m >= 0 else ui.TURUN_LEMBUT)
         for m, e in zip(terakhir["median_return"], ekstrem)]
label = [fmt.tanggal_pendek(t) for t in terakhir["tanggal"]]
fig = go.Figure(go.Bar(
    x=label, y=terakhir["median_return"], marker_color=warna, marker_line_width=0,
    customdata=list(zip([fmt.tanggal(t) for t in terakhir["tanggal"]],
                        [fmt.persen(m) for m in terakhir["median_return"]],
                        terakhir["saham_naik"], terakhir["saham_turun"])),
    hovertemplate="<b>%{customdata[0]}</b><br>Median return %{customdata[1]}<br>"
                  "%{customdata[2]} saham naik, %{customdata[3]} turun<extra></extra>",
))
ui.rapikan_grafik(fig, 300).update_layout(bargap=0.3)
bawah = int(terakhir["median_return"].min() * 20 - 1) / 20       # sumbu Y per 5%
atas = int(terakhir["median_return"].max() * 20 + 1) / 20
titik_y = [i / 20 for i in range(int(round(bawah * 20)), int(round(atas * 20)) + 1)]
fig.update_yaxes(tickvals=titik_y, ticktext=[fmt.persen(v, 0) for v in titik_y], range=[bawah - 0.012, atas])
fig.add_hline(y=0, line_color="#a9a8a3", line_width=1)
fig.update_xaxes(type="category", tickvals=label[::5] + [label[-1]] if (len(label) - 1) % 5 else label[::5])
# Nilai hari paling ekstrem ditulis langsung di grafik.
for baris in (terakhir.loc[terakhir["median_return"].idxmin()], terakhir.loc[terakhir["median_return"].idxmax()]):
    if abs(baris.median_return) >= BATAS_EKSTREM:
        fig.add_annotation(x=fmt.tanggal_pendek(baris.tanggal), y=baris.median_return, text=f"<b>{fmt.persen(baris.median_return)}</b>",
                           showarrow=False, xanchor="left", xshift=11, yanchor="middle",
                           font=dict(color=ui.NAIK if baris.median_return > 0 else ui.TURUN, size=12))
ui.tampilkan_grafik(fig)

kiri, kanan = st.columns(2, gap="large")
with kiri:
    ui.bagian("Turun terbesar")
    ui.tabel_ringkas(saham.nsmallest(5, "return_harian"), "return_harian")
with kanan:
    ui.bagian("Paling kuat")
    ui.tabel_ringkas(saham.nlargest(5, "return_harian"), "return_harian")

st.space("small")
ui.bagian("Semua saham", "Klik judul kolom untuk mengurutkan")
ui.tabel(saham.sort_values("kode"), {
    "kode": ("Kode", None),
    "nama": ("Nama", None),
    "sektor": ("Sektor", None),
    "harga_tutup": ("Tutup", fmt.angka),
    "return_harian": ("Return hari itu", fmt.persen),
    "return_ytd": ("Return sejak awal tahun", fmt.persen),
}, arah=["return_harian", "return_ytd"], tinggi=420)
