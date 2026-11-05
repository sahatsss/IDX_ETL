"""Risiko: volatilitas dan drawdown maksimum."""
import plotly.graph_objects as go
import streamlit as st

import fmt
import ui
from db import query

JUMLAH_LABEL = 6      # saham paling menonjol di tiap sumbu yang diberi label pada grafik

ui.kepala("Risiko", "Seberapa liar harga bergerak dan seberapa dalam pernah jatuh")

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
if risiko.empty:
    st.info("Belum ada data harga. Jalankan ETL terlebih dahulu.")
    st.stop()

terdalam = risiko.loc[risiko["drawdown_maksimum"].idxmin()]
ada_vol = risiko.dropna(subset=["volatilitas_30h_tahunan"])
terliar = ada_vol.loc[ada_vol["volatilitas_30h_tahunan"].idxmax()]
bantuan_dd = "Penurunan terdalam dari harga puncak ke harga dasar selama periode data."
bantuan_vol = "Standar deviasi return 30 hari bursa terakhir, disetahunkan. Makin tinggi, harga makin liar."

ui.kotak_metrik([
    ui.metrik("Median drawdown", fmt.persen(risiko["drawdown_maksimum"].median(), 0), f"{len(risiko)} saham", bantuan_dd),
    ui.metrik("Drawdown terdalam", fmt.persen(terdalam.drawdown_maksimum, 0), terdalam.kode, bantuan_dd, kelas_nilai="idx-turun"),
    ui.metrik("Median volatilitas", fmt.persen(ada_vol["volatilitas_30h_tahunan"].median(), 0, tanda=False), "Per tahun", bantuan_vol),
    ui.metrik("Volatilitas tertinggi", fmt.persen(terliar.volatilitas_30h_tahunan, 0, tanda=False), terliar.kode, bantuan_vol),
])
st.space("small")

ui.bagian("Volatilitas dan drawdown per saham", "Makin kanan makin liar, makin bawah makin dalam jatuhnya. Garis putus-putus: median.")
menonjol = (set(ada_vol.nlargest(JUMLAH_LABEL, "volatilitas_30h_tahunan")["kode"])
            | set(ada_vol.nsmallest(JUMLAH_LABEL, "volatilitas_30h_tahunan")["kode"])
            | set(ada_vol.nsmallest(JUMLAH_LABEL, "drawdown_maksimum")["kode"])
            | set(ada_vol.nlargest(JUMLAH_LABEL, "drawdown_maksimum")["kode"]))

# Label titik yang berdekatan bisa bertumpuk: tiap label memilih posisi yang belum dipakai tetangganya.
berlabel = ada_vol[ada_vol["kode"].isin(menonjol)].sort_values("drawdown_maksimum", ascending=False)
posisi_label: dict[str, str] = {}
titik_terpasang = []
for a in berlabel.itertuples():
    dipakai = {p for b, p in titik_terpasang
               if abs(a.volatilitas_30h_tahunan - b.volatilitas_30h_tahunan) < 0.03 and abs(a.drawdown_maksimum - b.drawdown_maksimum) < 0.05}
    posisi_label[a.kode] = next(p for p in ("top center", "bottom center", "middle left", "middle right", "top right") if p not in dipakai)
    titik_terpasang.append((a, posisi_label[a.kode]))
fig = go.Figure(go.Scatter(
    x=ada_vol["volatilitas_30h_tahunan"], y=ada_vol["drawdown_maksimum"], mode="markers+text",
    text=[k if k in menonjol else "" for k in ada_vol["kode"]],
    textposition=[posisi_label.get(k, "top center") for k in ada_vol["kode"]],
    textfont=dict(size=11, color=ui.TEKS),
    marker=dict(size=9, color=[ui.AKSEN if k in menonjol else "#c4c3be" for k in ada_vol["kode"]], line=dict(color="#ffffff", width=1)),
    customdata=list(zip(ada_vol["kode"], ada_vol["nama"], ada_vol["sektor"])),
    hovertemplate="<b>%{customdata[0]}</b> %{customdata[1]}<br>%{customdata[2]}<br>"
                  "Volatilitas %{x:.0%} · Drawdown %{y:.0%}<extra></extra>",
))
ui.rapikan_grafik(fig, 480)
fig.add_vline(x=ada_vol["volatilitas_30h_tahunan"].median(), line=dict(color="#a9a8a3", width=1, dash="dot"))
fig.add_hline(y=ada_vol["drawdown_maksimum"].median(), line=dict(color="#a9a8a3", width=1, dash="dot"))
fig.update_xaxes(tickformat=".0%", title_text="Volatilitas per tahun", showgrid=True, gridcolor=ui.GARIS_GRAFIK)
fig.update_yaxes(tickformat=".0%", title_text="Drawdown maksimum")
ui.tampilkan_grafik(fig)

kiri, kanan = st.columns([3, 2], gap="large")
with kiri:
    ui.bagian("Drawdown maksimum per saham")
    ui.tabel(risiko.sort_values("drawdown_maksimum"), {
        "kode": ("Kode", None),
        "drawdown_maksimum": ("Drawdown", lambda x: fmt.persen(x, 1)),
        "tanggal_puncak": ("Puncak", fmt.tanggal),
        "harga_puncak": ("Harga puncak", fmt.angka),
        "tanggal_dasar": ("Dasar", fmt.tanggal),
        "harga_dasar": ("Harga dasar", fmt.angka),
    }, tinggi=420)
with kanan:
    ui.bagian("Paling volatil tiap bulan")
    bulanan = query("""
        SELECT bulan, kode, volatilitas
        FROM v_volatilitas_bulanan WHERE peringkat = 1
        ORDER BY bulan DESC LIMIT 24
    """)
    ui.tabel(bulanan, {
        "bulan": ("Bulan", fmt.bulan_pendek),
        "kode": ("Kode", None),
        "volatilitas": ("Volatilitas harian", lambda x: fmt.persen(x, 2, tanda=False)),
    }, tinggi=420)

st.caption("Harga belum disesuaikan dividen dan spin-off, sehingga keduanya ikut terbaca sebagai drawdown (mis. spin-off ADRO, Nov 2024).")
