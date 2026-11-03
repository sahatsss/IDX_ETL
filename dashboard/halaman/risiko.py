"""Risiko: volatilitas dan drawdown maksimum."""
import plotly.express as px
import streamlit as st

from db import query

st.title("Risiko")

risiko = query("""
    WITH vol AS (
        SELECT DISTINCT ON (kode) kode, volatilitas_30h_tahunan
        FROM v_volatilitas
        ORDER BY kode, tanggal DESC
    )
    SELECT d.kode, e.nama, e.sektor, v.volatilitas_30h_tahunan, d.drawdown_maksimum,
           d.tanggal_puncak, d.harga_puncak, d.tanggal_dasar, d.harga_dasar
    FROM v_drawdown_maksimum d
    JOIN emiten e USING (kode)
    LEFT JOIN vol v USING (kode)
""")

st.subheader("Volatilitas saat ini vs drawdown maksimum")
st.caption("Kanan = harga bergerak makin liar (volatilitas 30 hari, disetahunkan). "
           "Bawah = kejatuhan terdalam dari puncak selama periode data.")
fig = px.scatter(risiko, x="volatilitas_30h_tahunan", y="drawdown_maksimum", color="sektor", text="kode",
                 hover_data={"nama": True, "sektor": False},
                 labels={"volatilitas_30h_tahunan": "Volatilitas 30h (tahunan)", "drawdown_maksimum": "Drawdown maksimum"})
fig.update_traces(textposition="top center", marker=dict(size=10))
fig.update_xaxes(tickformat=".0%")
fig.update_yaxes(tickformat=".0%")
fig.update_layout(height=550, margin=dict(l=0, r=0, t=10, b=0))
st.plotly_chart(fig, width="stretch")

kiri, kanan = st.columns(2)
with kiri:
    st.subheader("Drawdown maksimum")
    tampil = risiko.sort_values("drawdown_maksimum").assign(drawdown_maksimum=risiko["drawdown_maksimum"] * 100)
    st.dataframe(
        tampil[["kode", "drawdown_maksimum", "tanggal_puncak", "harga_puncak", "tanggal_dasar", "harga_dasar"]],
        column_config={
            "kode": "Kode",
            "drawdown_maksimum": st.column_config.NumberColumn("Drawdown", format="%.1f%%"),
            "tanggal_puncak": st.column_config.DateColumn("Puncak", format="DD MMM YYYY"),
            "harga_puncak": st.column_config.NumberColumn("Harga puncak", format="%,.0f"),
            "tanggal_dasar": st.column_config.DateColumn("Dasar", format="DD MMM YYYY"),
            "harga_dasar": st.column_config.NumberColumn("Harga dasar", format="%,.0f"),
        },
        hide_index=True, height=460,
    )
with kanan:
    st.subheader("Saham paling volatil tiap bulan")
    bulanan = query("""
        SELECT bulan, kode, volatilitas, jumlah_hari
        FROM v_volatilitas_bulanan WHERE peringkat = 1
        ORDER BY bulan DESC LIMIT 24
    """)
    st.dataframe(
        bulanan.assign(volatilitas=bulanan["volatilitas"] * 100),
        column_config={
            "bulan": st.column_config.DateColumn("Bulan", format="MMM YYYY"),
            "kode": "Kode",
            "volatilitas": st.column_config.NumberColumn("Volatilitas harian", format="%.2f%%"),
            "jumlah_hari": st.column_config.NumberColumn("Hari bursa"),
        },
        hide_index=True, height=460,
    )
st.caption("Harga belum disesuaikan dividen dan spin-off, sehingga keduanya ikut terbaca sebagai drawdown (mis. spin-off ADRO, Nov 2024).")
