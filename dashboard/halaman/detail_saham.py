"""Detail satu saham: candlestick + MA20/MA50, volume + lonjakan, drawdown."""
from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import fmt
import ui
from db import daftar_emiten, label_emiten, query

PERIODE = {"3 bulan": 92, "6 bulan": 183, "1 tahun": 365, "Semua": None}

ui.kepala("Detail saham", "Harga, tren, volume, dan risiko satu saham")

label = label_emiten(daftar_emiten())
if not label:
    st.info("Belum ada data emiten. Jalankan ETL terlebih dahulu.")
    st.stop()

kiri, kanan = st.columns([3, 2], vertical_alignment="bottom")
kode = kiri.selectbox("Saham", list(label), index=list(label).index("BBCA") if "BBCA" in label else 0, format_func=label.get)
pilihan = kanan.segmented_control("Periode", list(PERIODE), default="1 tahun") or "1 tahun"

batas = query("SELECT min(tanggal) AS awal, max(tanggal) AS akhir FROM harga_harian WHERE kode = :kode", kode=kode)
awal_data, akhir_data = batas["awal"][0], batas["akhir"][0]
if pd.isna(akhir_data):
    st.info("Saham ini belum punya data harga.")
    st.stop()
hari = PERIODE[pilihan]
mulai = max(awal_data, akhir_data - timedelta(days=hari)) if hari else awal_data

# MA, return, dan drawdown dihitung view atas SELURUH histori, lalu baru difilter per tanggal di sini,
# sehingga MA50 di awal periode tetap benar (bukan rata-rata dari data yang terpotong).
df = query("""
    SELECT h.tanggal, h.harga_buka, h.harga_tertinggi, h.harga_terendah, h.harga_tutup, h.volume,
           m.ma20, m.ma50, m.crossover, r.return_harian, d.drawdown, s.rasio AS rasio_lonjakan
    FROM harga_harian h
    JOIN v_moving_average m USING (kode, tanggal)
    JOIN v_return_harian  r USING (kode, tanggal)
    JOIN v_drawdown       d USING (kode, tanggal)
    LEFT JOIN v_volume_spike s USING (kode, tanggal)
    WHERE h.kode = :kode AND h.tanggal BETWEEN :mulai AND :akhir
    ORDER BY h.tanggal
""", kode=kode, mulai=mulai, akhir=akhir_data)
vol = query("SELECT volatilitas_30h_tahunan FROM v_volatilitas WHERE kode = :kode ORDER BY tanggal DESC LIMIT 1", kode=kode)

baris_akhir = df.iloc[-1]
return_periode = df["harga_tutup"].iloc[-1] / df["harga_tutup"].iloc[0] - 1
ui.kotak_metrik([
    ui.metrik("Harga tutup", fmt.angka(baris_akhir.harga_tutup), fmt.persen(baris_akhir.return_harian),
              f"Harga tutup {fmt.tanggal(baris_akhir.tanggal)} dan perubahannya dari hari bursa sebelumnya.",
              kelas_ket=ui.kelas_arah(baris_akhir.return_harian)),
    ui.metrik("Return periode", fmt.persen(return_periode, 1), pilihan,
              "Perubahan harga dari awal sampai akhir periode, belum termasuk dividen.",
              kelas_nilai=ui.kelas_arah(return_periode)),
    ui.metrik("Di bawah puncak", fmt.persen(baris_akhir.drawdown, 1), "Sejak awal data",
              "Jarak harga sekarang dari harga tutup tertinggi sejak awal data."),
    ui.metrik("Volatilitas", fmt.persen(vol["volatilitas_30h_tahunan"][0], 0, tanda=False) if not vol.empty else fmt.KOSONG, "Per tahun",
              "Standar deviasi return 30 hari bursa terakhir, disetahunkan. Makin tinggi, harga makin liar."),
])
st.space("small")

x = pd.to_datetime(df["tanggal"])
teks_tanggal = [fmt.tanggal(t) for t in df["tanggal"]]
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.62, 0.19, 0.19],
                    subplot_titles=("Harga dan moving average", "Volume", "Jarak dari puncak"))
fig.add_trace(go.Candlestick(x=x, open=df["harga_buka"], high=df["harga_tertinggi"], low=df["harga_terendah"], close=df["harga_tutup"],
                             name="Harga", increasing_line_color=ui.NAIK, increasing_fillcolor=ui.NAIK,
                             decreasing_line_color=ui.TURUN, decreasing_fillcolor=ui.TURUN, line_width=1, hoverinfo="text",
                             hovertext=[f"Buka {fmt.angka(r.harga_buka)}<br>Tertinggi {fmt.angka(r.harga_tertinggi)}<br>"
                                        f"Terendah {fmt.angka(r.harga_terendah)}<br>Tutup {fmt.angka(r.harga_tutup)}" for r in df.itertuples()]),
              row=1, col=1)
fig.add_trace(go.Scatter(x=x, y=df["ma20"], name="MA20", line=dict(width=1.5, color=ui.AKSEN),
                         hovertemplate="MA20 %{y:,.0f}<extra></extra>"), row=1, col=1)
fig.add_trace(go.Scatter(x=x, y=df["ma50"], name="MA50", line=dict(width=1.5, color="#8a8c8f"),
                         hovertemplate="MA50 %{y:,.0f}<extra></extra>"), row=1, col=1)
for jenis, nama, simbol, warna in [("golden_cross", "Golden cross", "triangle-up", ui.NAIK), ("death_cross", "Death cross", "triangle-down", ui.TURUN)]:
    titik = df[df["crossover"] == jenis]
    fig.add_trace(go.Scatter(x=pd.to_datetime(titik["tanggal"]), y=titik["ma20"], mode="markers", name=nama,
                             marker=dict(symbol=simbol, size=11, color=warna, line=dict(color="#ffffff", width=1)),
                             hovertemplate=nama + "<extra></extra>"), row=1, col=1)

warna_volume = ["#cfcec9" if pd.isna(r) else ui.AKSEN for r in df["rasio_lonjakan"]]
fig.add_trace(go.Bar(x=x, y=df["volume"], name="Volume", marker_color=warna_volume, marker_line_width=0, showlegend=False,
                     customdata=[fmt.ringkas(v) + (f" ({fmt.rasio(r)} rata-rata)" if pd.notna(r) else "")
                                 for v, r in zip(df["volume"], df["rasio_lonjakan"])],
                     hovertemplate="Volume %{customdata}<extra></extra>"), row=2, col=1)
fig.add_trace(go.Scatter(x=x, y=df["drawdown"], name="Jarak dari puncak", fill="tozeroy", showlegend=False,
                         line=dict(color=ui.TURUN, width=1), fillcolor="rgba(194,58,46,0.12)",
                         customdata=teks_tanggal, hovertemplate="%{y:.1%}<extra></extra>"), row=3, col=1)

ui.rapikan_grafik(fig, 720, legenda_tampil=True)
fig.update_layout(xaxis_rangeslider_visible=False, hovermode="x unified", margin=dict(t=24), legend=dict(y=-0.05), bargap=0.15)
fig.update_annotations(font=dict(size=12, color=ui.TEKS), x=0, xanchor="left")
fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])], showspikes=True, spikecolor="#c9c8c3", spikethickness=1, spikedash="solid", spikemode="across")
ui.sumbu_tanggal(fig, df["tanggal"])
fig.update_yaxes(tickformat=",.0f", row=1, col=1)
titik_volume = [df["volume"].max() * p for p in (0.5, 1)]
fig.update_yaxes(tickvals=titik_volume, ticktext=[fmt.ringkas(round(v, -7)) for v in titik_volume], row=2, col=1)
fig.update_yaxes(tickformat=".0%", row=3, col=1)
ui.tampilkan_grafik(fig)

st.caption("Harga sudah disesuaikan stock split, belum disesuaikan dividen dan spin-off. "
           "Batang biru pada volume menandai lonjakan: lebih dari 3 kali rata-rata 20 hari bursa sebelumnya.")
