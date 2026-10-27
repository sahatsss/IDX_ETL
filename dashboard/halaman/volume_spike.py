"""Volume spike: hari dengan volume > 3x rata-rata 20 hari sebelumnya."""
import plotly.express as px
import streamlit as st

from db import daftar_emiten, query

st.title("Volume spike")
st.caption("Hari dengan volume lebih dari 3× rata-rata 20 hari bursa sebelumnya. "
           "Sering menandai berita, laporan keuangan, atau corporate action.")

df = query("""
    SELECT s.kode, e.sektor, s.tanggal, s.volume, s.rata_volume_20h, s.rasio, s.return_harian
    FROM v_volume_spike s JOIN emiten e USING (kode)
    ORDER BY s.tanggal DESC
""")

f1, f2, f3 = st.columns([2, 1, 1])
kode = f1.multiselect("Saham", daftar_emiten()["kode"], placeholder="Semua saham")
rasio_min = f2.slider("Rasio minimum", 3.0, 20.0, 3.0, 0.5)
sejak = f3.date_input("Sejak", value=df["tanggal"].min(), min_value=df["tanggal"].min(), max_value=df["tanggal"].max())

pilih = df[(df["rasio"] >= rasio_min) & (df["tanggal"] >= sejak)]
if kode:
    pilih = pilih[pilih["kode"].isin(kode)]

st.metric("Jumlah kejadian", len(pilih))
pilih = pilih.assign(arah=pilih["return_harian"].map(lambda r: "Harga naik" if r > 0 else ("Harga turun" if r < 0 else "Tetap")))
fig = px.scatter(pilih, x="tanggal", y="rasio", color="arah", hover_data=["kode", "volume", "return_harian"],
                 color_discrete_map={"Harga naik": "#1D9E75", "Harga turun": "#D85A30", "Tetap": "#888780"},
                 labels={"rasio": "Volume ÷ rata-rata 20 hari", "tanggal": "", "arah": ""})
fig.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0))
st.plotly_chart(fig, width="stretch")

st.dataframe(
    pilih.drop(columns="arah").assign(return_harian=pilih["return_harian"] * 100),
    column_config={
        "kode": "Kode", "sektor": "Sektor",
        "tanggal": st.column_config.DateColumn("Tanggal", format="DD MMM YYYY"),
        "volume": st.column_config.NumberColumn("Volume", format="%,.0f"),
        "rata_volume_20h": st.column_config.NumberColumn("Rata-rata 20h", format="%,.0f"),
        "rasio": st.column_config.NumberColumn("Rasio", format="%.1f×"),
        "return_harian": st.column_config.NumberColumn("Return hari itu", format="%+.2f%%"),
    },
    hide_index=True,
)
