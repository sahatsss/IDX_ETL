"""Ringkasan: kondisi terakhir seluruh saham LQ45."""
import plotly.express as px
import streamlit as st

from db import persen, query

st.title("Ringkasan LQ45")

df = query("""
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
run = query("SELECT status, selesai FROM log_etl ORDER BY id DESC LIMIT 1")

tanggal_terakhir = df["tanggal"].max()
naik = int((df["return_harian"] > 0).sum())
turun = int((df["return_harian"] < 0).sum())

k1, k2, k3, k4 = st.columns(4)
k1.metric("Jumlah saham", len(df))
k2.metric("Data terakhir", tanggal_terakhir.strftime("%d/%m/%y"))
k3.metric("Naik / turun hari itu", f"{naik} / {turun}")
k4.metric("Median return hari itu", persen(df["return_harian"].median(), 2))
if not run.empty:
    st.caption(f"Run ETL terakhir: **{run['status'][0]}**, selesai {run['selesai'][0]:%d %b %Y %H:%M} UTC")

st.subheader(f"Return sejak awal tahun (YTD) {tanggal_terakhir.year}")
ytd = df.dropna(subset=["return_ytd"]).sort_values("return_ytd")
ytd["arah"] = ytd["return_ytd"].map(lambda x: "Naik" if x >= 0 else "Turun")
fig = px.bar(ytd, x="return_ytd", y="kode", orientation="h", color="arah",
             color_discrete_map={"Naik": "#1D9E75", "Turun": "#D85A30"},
             hover_data={"nama": True, "sektor": True, "arah": False},
             labels={"return_ytd": "Return YTD", "kode": ""})
fig.update_layout(height=900, showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
fig.update_xaxes(tickformat=".0%")
st.plotly_chart(fig, width="stretch")

st.subheader(f"Pergerakan {tanggal_terakhir:%d %b %Y}")
tampil = df.assign(return_harian=df["return_harian"] * 100, return_ytd=df["return_ytd"] * 100)
kolom = {
    "kode": "Kode", "nama": "Nama", "sektor": "Sektor",
    "harga_tutup": st.column_config.NumberColumn("Tutup", format="%,.0f"),
    "return_harian": st.column_config.NumberColumn("Return hari itu", format="%+.2f%%"),
    "return_ytd": st.column_config.NumberColumn("Return YTD", format="%+.2f%%"),
}
kiri, kanan = st.columns(2)
kiri.markdown("**5 naik terbesar**")
kiri.dataframe(tampil.nlargest(5, "return_harian")[list(kolom)], column_config=kolom, hide_index=True)
kanan.markdown("**5 turun terbesar**")
kanan.dataframe(tampil.nsmallest(5, "return_harian")[list(kolom)], column_config=kolom, hide_index=True)
