"""Sektor: ranking return bulanan antar sektor dan di dalam sektor."""
from datetime import timedelta

import plotly.graph_objects as go
import streamlit as st

import fmt
import ui
from db import query

ui.kepala("Kinerja sektor", "Sektor dan saham mana yang paling unggul tiap bulan")

df = query("SELECT * FROM v_ranking_sektor_bulanan ORDER BY bulan, peringkat_sektor, peringkat_dalam_sektor")
if df.empty:
    st.info("Belum ada data bulanan. Dibutuhkan data minimal dua bulan.")
    st.stop()

daftar_bulan = sorted(df["bulan"].unique(), reverse=True)
akhir_data = query("SELECT max(tanggal) AS akhir FROM harga_harian")["akhir"][0]
terbaru = daftar_bulan[0]
# Bulan masih berjalan jika tanggal data terakhir belum mendekati akhir bulan: angkanya belum final,
# jadi halaman dibuka pada bulan penuh terakhir.
berjalan = (terbaru.year, terbaru.month) == (akhir_data.year, akhir_data.month) and (akhir_data + timedelta(days=3)).month == akhir_data.month


def label_bulan(b) -> str:
    return f"{fmt.bulan(b)} (berjalan)" if berjalan and b == terbaru else fmt.bulan(b)


kolom_bulan, _ = st.columns([1, 2])
bulan = kolom_bulan.selectbox("Bulan", daftar_bulan, index=1 if berjalan and len(daftar_bulan) > 1 else 0, format_func=label_bulan)

pilih = df[df["bulan"] == bulan]
sektor = pilih.drop_duplicates("sektor").sort_values("rata_rata_sektor", ascending=False)
terbaik, terlemah = sektor.iloc[0], sektor.iloc[-1]
saham_atas = pilih.loc[pilih["return_bulanan"].idxmax()]
saham_bawah = pilih.loc[pilih["return_bulanan"].idxmin()]
bantuan_sektor = "Rata-rata return bulanan saham di sektor itu: harga tutup akhir bulan dibanding akhir bulan sebelumnya."

ui.kotak_metrik([
    ui.metrik("Sektor terbaik", fmt.persen(terbaik.rata_rata_sektor, 1), terbaik.sektor, bantuan_sektor,
              kelas_nilai=ui.kelas_arah(terbaik.rata_rata_sektor)),
    ui.metrik("Sektor terlemah", fmt.persen(terlemah.rata_rata_sektor, 1), terlemah.sektor, bantuan_sektor,
              kelas_nilai=ui.kelas_arah(terlemah.rata_rata_sektor)),
    ui.metrik("Saham terbaik", fmt.persen(saham_atas.return_bulanan, 1), saham_atas.kode, kelas_nilai=ui.kelas_arah(saham_atas.return_bulanan)),
    ui.metrik("Saham terlemah", fmt.persen(saham_bawah.return_bulanan, 1), saham_bawah.kode, kelas_nilai=ui.kelas_arah(saham_bawah.return_bulanan)),
])
st.space("small")

kiri, kanan = st.columns([3, 2], gap="large")
with kiri:
    ui.bagian("Rata-rata return per sektor", f"{label_bulan(bulan)}. Angka dalam kurung: jumlah saham.")
    urut = sektor.sort_values("rata_rata_sektor")
    fig = go.Figure(go.Bar(
        x=urut["rata_rata_sektor"], y=[f"{r.sektor} ({r.jumlah_saham_sektor})" for r in urut.itertuples()], orientation="h",
        marker_color=[ui.NAIK if v >= 0 else ui.TURUN for v in urut["rata_rata_sektor"]], marker_line_width=0,
        text=[fmt.persen(v, 1) for v in urut["rata_rata_sektor"]], textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>%{x:+.2%}<extra></extra>",
    ))
    ui.rapikan_grafik(fig, 380).update_layout(bargap=0.35)
    # Ruang di kedua sisi agar label nilai di luar batang tidak menabrak nama sektor.
    rendah, tinggi = min(urut["rata_rata_sektor"].min(), 0), max(urut["rata_rata_sektor"].max(), 0)
    ruang = max(tinggi - rendah, 0.01) * 0.2
    fig.update_xaxes(tickformat=".0%", gridcolor=ui.GARIS_GRAFIK, showgrid=True, zeroline=True, zerolinecolor="#a9a8a3",
                     range=[rendah - ruang if rendah < 0 else 0, tinggi + ruang if tinggi > 0 else 0])
    fig.update_yaxes(showgrid=False)
    ui.tampilkan_grafik(fig)
with kanan:
    ui.bagian("Peringkat saham", "Klik judul kolom untuk mengurutkan")
    ui.tabel(pilih, {
        "kode": ("Kode", None),
        "sektor": ("Sektor", None),
        "peringkat_dalam_sektor": ("Peringkat di sektor", None),
        "return_bulanan": ("Return", fmt.persen),
    }, arah=["return_bulanan"], tinggi=380)

st.space("small")
ui.bagian("Peta 12 bulan terakhir", "Rata-rata return bulanan per sektor")
dua_belas = df[df["bulan"].isin(daftar_bulan[:12])].drop_duplicates(["sektor", "bulan"])
peta = dua_belas.pivot(index="sektor", columns="bulan", values="rata_rata_sektor").sort_index(ascending=False)
batas = max(abs(peta.min().min()), abs(peta.max().max()))
kolom = [fmt.bulan_pendek(b) for b in peta.columns]
fig = go.Figure(go.Heatmap(
    z=peta.values, x=kolom, y=peta.index, colorscale=ui.SKALA_ARAH, zmid=0, zmin=-batas, zmax=batas, xgap=2, ygap=2, showscale=False,
    text=[[fmt.persen(v, 1) for v in baris] for baris in peta.values], texttemplate="%{text}", textfont=dict(size=11),
    hovertemplate="<b>%{y}</b>, %{x}<br>%{text}<extra></extra>",
))
ui.rapikan_grafik(fig, 380)
fig.update_xaxes(type="category", side="top")
fig.update_yaxes(showgrid=False)
ui.tampilkan_grafik(fig)
st.caption("Sektor dengan sedikit saham sangat dipengaruhi satu emiten. Bulan berjalan belum final.")
