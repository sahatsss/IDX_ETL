"""Kualitas data: riwayat run ETL (log_etl) dan isu validasi (data_quality_issue)."""
import plotly.express as px
import streamlit as st

from db import query

st.title("Kualitas data dan audit trail")
st.caption("Setiap run ETL tercatat di log_etl; setiap pelanggaran aturan validasi tercatat di data_quality_issue "
           "beserta run_id-nya, sehingga data yang dibuang atau ditandai selalu bisa ditelusuri.")

run = query("""
    SELECT id AS run_id, mulai, selesai, status, tanggal_awal, tanggal_akhir,
           baris_diambil, baris_dimuat, jumlah_isu, pesan_error,
           EXTRACT(EPOCH FROM (selesai - mulai)) AS durasi_detik
    FROM log_etl ORDER BY id DESC
""")
isu = query("""
    SELECT i.run_id, i.kode, i.tanggal, i.aturan, i.keterangan, i.dicatat_pada
    FROM data_quality_issue i ORDER BY i.id DESC
""")

terakhir = run.iloc[0] if not run.empty else None
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total run", len(run))
k2.metric("Run gagal", int((run["status"] == "gagal").sum()))
k3.metric("Status run terakhir", "–" if terakhir is None else terakhir["status"])
k4.metric("Total isu tercatat", len(isu))

st.subheader("Riwayat run ETL")
st.dataframe(
    run,
    column_config={
        "run_id": st.column_config.NumberColumn("Run"),
        "mulai": st.column_config.DatetimeColumn("Mulai (UTC)", format="DD MMM YYYY HH:mm"),
        "selesai": st.column_config.DatetimeColumn("Selesai (UTC)", format="DD MMM YYYY HH:mm"),
        "status": "Status",
        "tanggal_awal": st.column_config.DateColumn("Data dari", format="DD MMM YYYY"),
        "tanggal_akhir": st.column_config.DateColumn("Data s.d.", format="DD MMM YYYY"),
        "baris_diambil": st.column_config.NumberColumn("Diambil", format="%,d"),
        "baris_dimuat": st.column_config.NumberColumn("Dimuat", format="%,d"),
        "jumlah_isu": st.column_config.NumberColumn("Isu"),
        "pesan_error": "Pesan error",
        "durasi_detik": st.column_config.NumberColumn("Durasi", format="%.1f s"),
    },
    hide_index=True,
)

st.subheader("Isu validasi")
if isu.empty:
    st.success("Belum ada isu validasi yang tercatat. Semua baris dari semua run lolos keenam aturan.")
else:
    per_aturan = isu.groupby("aturan").size().reset_index(name="jumlah").sort_values("jumlah")
    fig = px.bar(per_aturan, x="jumlah", y="aturan", orientation="h", labels={"aturan": "", "jumlah": "Jumlah isu"})
    fig.update_layout(height=260, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, width="stretch")
    st.dataframe(isu, hide_index=True)

with st.expander("Aturan validasi yang berjalan di setiap run"):
    st.markdown("""
| Aturan | Perlakuan |
|---|---|
| `tanggal_masa_depan` | dibuang + dicatat |
| `harga_tidak_positif` | dibuang + dicatat |
| `ohlc_tidak_konsisten` | dibuang + dicatat |
| `volume_negatif` | dibuang + dicatat |
| `duplikat` | salinan pertama disimpan, sisanya dibuang + dicatat |
| `lonjakan_ekstrem` | **disimpan** + dicatat (batas ARA/ARB BEI per periode) |
""")
