"""Dashboard saham IDX (LQ45). Jalankan: python -m streamlit run dashboard/app.py"""
from pathlib import Path

import streamlit as st

import ui

st.set_page_config(page_title="IDX LQ45", page_icon=":material/monitoring:", layout="wide")
st.logo(str(Path(__file__).parent / "assets" / "logo.svg"), size="large")
ui.pasang_gaya()

halaman = st.navigation({
    "Analisis": [
        st.Page("halaman/ringkasan.py", title="Ringkasan", icon=":material/dashboard:", default=True),
        st.Page("halaman/detail_saham.py", title="Detail saham", icon=":material/candlestick_chart:"),
        st.Page("halaman/sektor.py", title="Sektor", icon=":material/grid_view:"),
        st.Page("halaman/risiko.py", title="Risiko", icon=":material/trending_down:"),
        st.Page("halaman/volume_spike.py", title="Lonjakan volume", icon=":material/bar_chart:"),
    ],
    "Kontrol": [
        st.Page("halaman/kualitas_data.py", title="Kualitas data", icon=":material/fact_check:"),
    ],
})

st.sidebar.caption("Sumber: yfinance (tidak resmi). Konstituen LQ45 Agu–Okt 2026. Harga belum termasuk dividen.")
halaman.run()
