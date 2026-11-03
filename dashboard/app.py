"""Dashboard saham IDX (LQ45). Jalankan: streamlit run dashboard/app.py"""
import streamlit as st

st.set_page_config(page_title="IDX LQ45 Dashboard", page_icon=":material/monitoring:", layout="wide")

halaman = st.navigation({
    "Analisis": [
        st.Page("halaman/ringkasan.py", title="Ringkasan", icon=":material/dashboard:", default=True),
        st.Page("halaman/detail_saham.py", title="Detail saham", icon=":material/candlestick_chart:"),
        st.Page("halaman/sektor.py", title="Sektor", icon=":material/grid_view:"),
        st.Page("halaman/risiko.py", title="Risiko", icon=":material/trending_down:"),
        st.Page("halaman/volume_spike.py", title="Volume spike", icon=":material/bar_chart:"),
    ],
    "Kontrol": [
        st.Page("halaman/kualitas_data.py", title="Kualitas data", icon=":material/fact_check:"),
    ],
})

st.sidebar.caption("Sumber: yfinance (data tidak resmi), konstituen LQ45 periode Agu–Okt 2026. Harga sudah disesuaikan stock split, belum disesuaikan dividen dan spin-off.")
halaman.run()
