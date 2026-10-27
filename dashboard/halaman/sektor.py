"""Sektor: ranking return bulanan antar sektor dan di dalam sektor."""
import plotly.express as px
import streamlit as st

from db import query

st.title("Kinerja sektor")

df = query("SELECT * FROM v_ranking_sektor_bulanan ORDER BY bulan, peringkat_sektor, peringkat_dalam_sektor")
bulan_list = sorted(df["bulan"].unique(), reverse=True)
bulan = st.selectbox("Bulan", bulan_list, format_func=lambda b: b.strftime("%B %Y"))
st.caption("Return bulanan = harga tutup akhir bulan ÷ akhir bulan sebelumnya − 1. Bulan berjalan masih month-to-date.")

pilih = df[df["bulan"] == bulan]
sektor = (pilih.drop_duplicates("sektor")[["sektor", "rata_rata_sektor", "peringkat_sektor", "jumlah_saham_sektor"]]
          .sort_values("peringkat_sektor"))

kiri, kanan = st.columns([3, 2])
with kiri:
    st.subheader("Rata-rata return per sektor")
    grafik = sektor.assign(label=sektor["sektor"] + " (" + sektor["jumlah_saham_sektor"].astype(str) + ")")
    fig = px.bar(grafik.sort_values("rata_rata_sektor"), x="rata_rata_sektor", y="label", orientation="h",
                 color="rata_rata_sektor", color_continuous_scale=["#D85A30", "#F1EFE8", "#1D9E75"],
                 color_continuous_midpoint=0,
                 labels={"rata_rata_sektor": "Rata-rata return", "label": ""})
    fig.update_layout(coloraxis_showscale=False, height=420, margin=dict(l=0, r=0, t=10, b=0))
    fig.update_xaxes(tickformat=".0%")
    st.plotly_chart(fig, width="stretch")
with kanan:
    st.subheader("Saham per sektor")
    tampil = pilih.assign(return_bulanan=pilih["return_bulanan"] * 100)
    st.dataframe(
        tampil[["peringkat_sektor", "sektor", "peringkat_dalam_sektor", "kode", "return_bulanan"]],
        column_config={
            "peringkat_sektor": st.column_config.NumberColumn("#Sektor"),
            "sektor": "Sektor",
            "peringkat_dalam_sektor": st.column_config.NumberColumn("#Dalam sektor"),
            "kode": "Kode",
            "return_bulanan": st.column_config.NumberColumn("Return", format="%+.2f%%"),
        },
        hide_index=True, height=420,
    )

st.subheader("Peta panas 12 bulan terakhir")
dua_belas = df[df["bulan"].isin(bulan_list[:12])].drop_duplicates(["sektor", "bulan"])
peta = dua_belas.pivot(index="sektor", columns="bulan", values="rata_rata_sektor").sort_index()
fig = px.imshow(peta, color_continuous_scale=["#D85A30", "#F1EFE8", "#1D9E75"], color_continuous_midpoint=0,
                aspect="auto", text_auto=".1%", labels={"color": "Return", "x": "", "y": ""})
fig.update_xaxes(tickformat="%b %y")
fig.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0), coloraxis_colorbar_tickformat=".0%")
st.plotly_chart(fig, width="stretch")
st.caption("Sektor dengan sedikit saham (mis. Kesehatan: 1 saham) sangat dipengaruhi satu emiten.")
