"""Detail satu saham: candlestick + MA20/MA50, volume + spike, drawdown."""
from datetime import timedelta

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from db import daftar_emiten, label_emiten, persen, query

st.title("Detail saham")

emiten = daftar_emiten()
label = label_emiten(emiten)
kode = st.selectbox("Saham", list(label), index=list(label).index("BBCA") if "BBCA" in label else 0,
                    format_func=label.get)

batas = query("SELECT min(tanggal) AS awal, max(tanggal) AS akhir FROM harga_harian WHERE kode = :kode", kode=kode)
awal_data, akhir_data = batas["awal"][0], batas["akhir"][0]
mulai, akhir = st.slider("Periode", min_value=awal_data, max_value=akhir_data,
                         value=(max(awal_data, akhir_data - timedelta(days=365)), akhir_data), format="DD MMM YYYY")

# MA, return, dan drawdown dihitung view atas SELURUH histori, lalu baru difilter per tanggal di sini,
# sehingga MA50 di awal periode tetap benar (bukan rata-rata dari data yang terpotong).
df = query("""
    SELECT h.tanggal, h.harga_buka, h.harga_tertinggi, h.harga_terendah, h.harga_tutup, h.volume,
           m.ma20, m.ma50, m.crossover, r.return_harian, d.drawdown, s.rasio AS rasio_spike
    FROM harga_harian h
    JOIN v_moving_average m USING (kode, tanggal)
    JOIN v_return_harian  r USING (kode, tanggal)
    JOIN v_drawdown       d USING (kode, tanggal)
    LEFT JOIN v_volume_spike s USING (kode, tanggal)
    WHERE h.kode = :kode AND h.tanggal BETWEEN :mulai AND :akhir
    ORDER BY h.tanggal
""", kode=kode, mulai=mulai, akhir=akhir)
vol = query("""
    SELECT volatilitas_30h_tahunan FROM v_volatilitas WHERE kode = :kode ORDER BY tanggal DESC LIMIT 1
""", kode=kode)

if df.empty:
    st.warning("Tidak ada data di periode ini.")
    st.stop()

akhir_baris = df.iloc[-1]
k1, k2, k3, k4 = st.columns(4)
k1.metric("Harga tutup", f"{akhir_baris['harga_tutup']:,.0f}", persen(akhir_baris["return_harian"], 2))
k2.metric("Return periode", persen(df["harga_tutup"].iloc[-1] / df["harga_tutup"].iloc[0] - 1))
k3.metric("Di bawah puncak", persen(akhir_baris["drawdown"]))
k4.metric("Volatilitas 30h (tahunan)", "–" if vol.empty else f"{vol['volatilitas_30h_tahunan'][0]:.0%}")

fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2],
                    subplot_titles=("Harga, MA20, MA50", "Volume", "Drawdown dari puncak"))
fig.add_trace(go.Candlestick(x=df["tanggal"], open=df["harga_buka"], high=df["harga_tertinggi"],
                             low=df["harga_terendah"], close=df["harga_tutup"], name="Harga"), row=1, col=1)
fig.add_trace(go.Scatter(x=df["tanggal"], y=df["ma20"], name="MA20", line=dict(width=1.5, color="#378ADD")), row=1, col=1)
fig.add_trace(go.Scatter(x=df["tanggal"], y=df["ma50"], name="MA50", line=dict(width=1.5, color="#BA7517")), row=1, col=1)
for jenis, simbol, warna in [("golden_cross", "triangle-up", "#1D9E75"), ("death_cross", "triangle-down", "#D85A30")]:
    titik = df[df["crossover"] == jenis]
    fig.add_trace(go.Scatter(x=titik["tanggal"], y=titik["ma20"], mode="markers", name=jenis.replace("_", " "),
                             marker=dict(symbol=simbol, size=12, color=warna)), row=1, col=1)

fig.add_trace(go.Bar(x=df["tanggal"], y=df["volume"], name="Volume", marker_color="#B4B2A9"), row=2, col=1)
spike = df.dropna(subset=["rasio_spike"])
fig.add_trace(go.Bar(x=spike["tanggal"], y=spike["volume"], name="Volume spike (>3×)", marker_color="#D85A30",
                     customdata=spike["rasio_spike"], hovertemplate="%{x}<br>%{y:,.0f} (%{customdata:.1f}×)"),
              row=2, col=1)

fig.add_trace(go.Scatter(x=df["tanggal"], y=df["drawdown"], name="Drawdown", fill="tozeroy",
                         line=dict(color="#A32D2D", width=1)), row=3, col=1)

fig.update_layout(height=800, xaxis_rangeslider_visible=False, barmode="overlay",
                  legend=dict(orientation="h", yanchor="top", y=-0.04), margin=dict(l=0, r=0, t=30, b=0))
fig.update_yaxes(tickformat=".0%", row=3, col=1)
st.plotly_chart(fig, width="stretch")

st.caption("Harga mentah (belum disesuaikan stock split / dividen / spin-off), sehingga lonjakan di tanggal "
           "corporate action ikut terbaca sebagai pergerakan harga.")
