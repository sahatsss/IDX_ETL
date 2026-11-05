"""Lonjakan volume: hari dengan volume > 3x rata-rata 20 hari bursa sebelumnya."""
from datetime import timedelta

import plotly.graph_objects as go
import streamlit as st

import fmt
import ui
from db import daftar_emiten, query

ui.kepala("Lonjakan volume", "Hari ketika saham jauh lebih ramai dari biasanya")

df = query("""
    SELECT s.kode, e.sektor, s.tanggal, s.volume, s.rata_volume_20h, s.rasio, s.return_harian
    FROM v_volume_spike s JOIN emiten e USING (kode)
    ORDER BY s.tanggal DESC
""")
if df.empty:
    st.info("Belum ada lonjakan volume yang tercatat.")
    st.stop()

awal, akhir = df["tanggal"].min(), df["tanggal"].max()
f1, f2, f3 = st.columns([2, 1, 1])
kode = f1.multiselect("Saham", daftar_emiten()["kode"], placeholder="Semua saham")
rasio_min = f2.number_input("Rasio minimum", min_value=3.0, max_value=50.0, value=3.0, step=1.0, format="%.0f",
                            help="Volume hari itu dibanding rata-rata 20 hari bursa sebelumnya.")
sejak = f3.date_input("Sejak", value=max(awal, akhir - timedelta(days=365)), min_value=awal, max_value=akhir, format="DD/MM/YYYY")

pilih = df[(df["rasio"] >= rasio_min) & (df["tanggal"] >= sejak)]
if kode:
    pilih = pilih[pilih["kode"].isin(kode)]
if pilih.empty:
    st.info("Tidak ada lonjakan volume yang cocok dengan filter ini. Coba longgarkan filternya.")
    st.stop()

puncak = pilih.loc[pilih["rasio"].idxmax()]
ui.kotak_metrik([
    ui.metrik("Jumlah lonjakan", fmt.angka(len(pilih)), f"{pilih['kode'].nunique()} saham",
              "Hari dengan volume lebih dari 3 kali rata-rata 20 hari bursa sebelumnya."),
    ui.metrik("Harga naik / turun", f"{(pilih['return_harian'] > 0).sum()} / {(pilih['return_harian'] < 0).sum()}", "Saat lonjakan"),
    ui.metrik("Rasio tertinggi", fmt.rasio(puncak.rasio), f"{puncak.kode}, {fmt.tanggal(puncak.tanggal)}"),
    ui.metrik("Pergerakan harga", fmt.persen(pilih["return_harian"].abs().median(), 1, tanda=False), "Median saat lonjakan",
              "Median besar perubahan harga pada hari lonjakan, tanpa melihat arah."),
])
st.space("small")

ui.bagian("Lonjakan volume per tanggal", "Skala rasio logaritmik, karena sebagian lonjakan jauh lebih besar dari yang lain")
ui.legenda([([ui.NAIK], "Harga naik"), ([ui.TURUN], "Harga turun"), (["#a9a8a3"], "Harga tetap")])
warna = [ui.NAIK if r > 0 else (ui.TURUN if r < 0 else "#a9a8a3") for r in pilih["return_harian"]]
fig = go.Figure(go.Scatter(
    x=pilih["tanggal"], y=pilih["rasio"], mode="markers",
    marker=dict(size=8, color=warna, opacity=0.8, line=dict(color="#ffffff", width=0.5)),
    customdata=list(zip(pilih["kode"], [fmt.tanggal(t) for t in pilih["tanggal"]], [fmt.rasio(r) for r in pilih["rasio"]],
                        [fmt.persen(r) for r in pilih["return_harian"]])),
    hovertemplate="<b>%{customdata[0]}</b>, %{customdata[1]}<br>Volume %{customdata[2]} rata-rata<br>Return %{customdata[3]}<extra></extra>",
))
ui.rapikan_grafik(fig, 380)
fig.update_yaxes(type="log", tickvals=[3, 5, 10, 20, 50, 100, 200, 300], ticksuffix="×", title_text="Volume ÷ rata-rata 20 hari")
ui.sumbu_tanggal(fig, pilih["tanggal"])
ui.tampilkan_grafik(fig)

ui.bagian("Daftar lonjakan", "Klik judul kolom untuk mengurutkan")
ui.tabel(pilih, {
    "tanggal": ("Tanggal", fmt.tanggal),
    "kode": ("Kode", None),
    "sektor": ("Sektor", None),
    "volume": ("Volume", fmt.angka),
    "rata_volume_20h": ("Rata-rata 20 hari", fmt.angka),
    "rasio": ("Rasio", fmt.rasio),
    "return_harian": ("Return", fmt.persen),
}, arah=["return_harian"], tinggi=420)
