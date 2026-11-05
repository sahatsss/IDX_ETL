"""Komponen tampilan yang dipakai semua halaman: gaya, kotak metrik, tabel, dan grafik."""
from datetime import date
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import fmt
from db import query

NAIK = "#0f7f5a"
TURUN = "#c23a2e"
NAIK_LEMBUT = "#a3d1c0"
TURUN_LEMBUT = "#ecb5af"
AKSEN = "#2f4bc4"
TEKS = "#1c1d1f"
REDUP = "#6b6d70"
GARIS = "#e6e5e1"
GARIS_GRAFIK = "#eeede9"
FONT = "IBM Plex Sans, -apple-system, Segoe UI, Roboto, Arial, sans-serif"

SKALA_ARAH = [[0, TURUN], [0.5, "#f5f4f1"], [1, NAIK]]
BATAS_DATA_BASI_HARI = 4     # toleransi akhir pekan + satu hari libur sebelum data dianggap terlambat

CSS = f"""<style>
[data-testid="stMainBlockContainer"] {{ padding-top: 2.25rem; padding-bottom: 3rem; max-width: 1240px; }}
.idx-kepala {{ display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; flex-wrap: wrap; }}
.idx-judul {{ font-size: 1.5rem; font-weight: 600; color: {TEKS}; margin: 0; line-height: 1.3; }}
.idx-desk {{ color: {REDUP}; margin: 2px 0 0; }}
.idx-status {{ display: inline-flex; gap: 6px; align-items: center; white-space: nowrap; font-size: .8rem; color: {REDUP};
  background: #fff; border: 1px solid {GARIS}; border-radius: 4px; padding: 3px 8px; }}
.idx-titik {{ width: 7px; height: 7px; border-radius: 50%; display: inline-block; }}
.idx-kpi {{ display: grid; grid-template-columns: repeat(var(--n), minmax(0, 1fr)); gap: 1px; background: {GARIS};
  border: 1px solid {GARIS}; border-radius: 6px; }}
.idx-k {{ background: #fff; padding: 12px 16px; min-width: 0; }}
.idx-k:first-child {{ border-radius: 5px 0 0 5px; }}
.idx-k:last-child {{ border-radius: 0 5px 5px 0; }}
.idx-kl {{ color: {REDUP}; font-size: .8rem; display: flex; align-items: center; gap: 5px; }}
.idx-kv {{ font-size: 1.5rem; font-weight: 600; color: {TEKS}; margin: 2px 0 0; font-variant-numeric: tabular-nums; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; line-height: 1.35; }}
.idx-ks {{ color: {REDUP}; font-size: .8rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.idx-naik {{ color: {NAIK}; }}
.idx-turun {{ color: {TURUN}; }}
.idx-bantu {{ position: relative; display: inline-flex; width: 14px; height: 14px; border-radius: 50%; border: 1px solid #a9abae; color: {REDUP};
  font-size: 10px; line-height: 1; align-items: center; justify-content: center; cursor: help; flex: none; }}
.idx-bantu:hover::after, .idx-bantu:focus::after {{ content: attr(data-tip); position: absolute; top: 20px; left: -6px; z-index: 50; width: 230px;
  background: {TEKS}; color: #fff; font-size: .75rem; line-height: 1.45; padding: 7px 9px; border-radius: 4px; white-space: normal; }}
.idx-k:last-child .idx-bantu:hover::after, .idx-k:last-child .idx-bantu:focus::after {{ left: auto; right: -6px; }}
.idx-bagian {{ font-size: 1rem; font-weight: 600; color: {TEKS}; margin: 0; }}
.idx-sub {{ color: {REDUP}; font-size: .8rem; margin: 1px 0 0; }}
.idx-legenda {{ display: flex; flex-wrap: wrap; gap: 14px; color: {REDUP}; font-size: .8rem; margin: 4px 0 0; }}
.idx-legenda span {{ display: inline-flex; align-items: center; gap: 4px; }}
.idx-kotak {{ display: inline-block; width: 10px; height: 10px; border-radius: 2px; }}
.idx-tabel {{ width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; font-size: .875rem; margin-top: 4px; }}
.idx-tabel th {{ color: {REDUP}; font-weight: 400; font-size: .8rem; text-align: left; padding: 5px 0; border-bottom: 1px solid {GARIS}; }}
.idx-tabel td {{ padding: 6px 0; border-bottom: 1px solid #f0efec; }}
.idx-kanan {{ text-align: right !important; }}
@media (max-width: 760px) {{
  [data-testid="stMainBlockContainer"] {{ padding-top: 4.5rem; }}
  .idx-kpi {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .idx-k:first-child, .idx-k:last-child {{ border-radius: 0; }}
}}
</style>"""


def pasang_gaya() -> None:
    st.html(CSS)


def kelas_arah(x) -> str:
    if pd.isna(x) or x == 0:
        return ""
    return "idx-naik" if x > 0 else "idx-turun"


def status_data() -> str:
    """Lencana kondisi data: tanggal terakhir, jumlah isu run terakhir, dan warna status."""
    akhir = query("SELECT max(tanggal) AS akhir FROM harga_harian")["akhir"][0]
    run = query("SELECT status, jumlah_isu FROM log_etl ORDER BY id DESC LIMIT 1")
    status = run["status"][0] if not run.empty else None
    isu = run["jumlah_isu"][0] if not run.empty else None
    basi = pd.isna(akhir) or (date.today() - akhir).days > BATAS_DATA_BASI_HARI
    warna = TURUN if status == "gagal" else ("#b7791f" if basi else NAIK)
    catatan = "run terakhir gagal" if status == "gagal" else f"{0 if pd.isna(isu) else int(isu)} isu"
    return (f'<span class="idx-status"><span class="idx-titik" style="background:{warna}"></span>'
            f"Data {fmt.tanggal(akhir)} · {catatan}</span>")


def kepala(judul: str, deskripsi: str) -> None:
    st.html(f'<div class="idx-kepala"><div><h1 class="idx-judul">{escape(judul)}</h1>'
            f'<p class="idx-desk">{escape(deskripsi)}</p></div>{status_data()}</div>')


def bagian(judul: str, sub: str | None = None) -> None:
    keterangan = f'<p class="idx-sub">{escape(sub)}</p>' if sub else ""
    st.html(f'<p class="idx-bagian">{escape(judul)}</p>{keterangan}')


def metrik(label: str, nilai: str, ket: str = "", bantuan: str | None = None,
           kelas_nilai: str = "", kelas_ket: str = "") -> dict:
    return dict(label=label, nilai=nilai, ket=ket, bantuan=bantuan, kelas_nilai=kelas_nilai, kelas_ket=kelas_ket)


def kotak_metrik(daftar: list[dict]) -> None:
    """Satu baris metrik. Aturan isi: label dan keterangan maksimal 2-3 kata; definisi masuk ke `bantuan` (ikon i)."""
    isi = ""
    for m in daftar:
        ikon = (f'<span class="idx-bantu" tabindex="0" role="note" aria-label="{escape(m["bantuan"], quote=True)}" '
                f'data-tip="{escape(m["bantuan"], quote=True)}">i</span>') if m["bantuan"] else ""
        isi += (f'<div class="idx-k"><div class="idx-kl">{escape(m["label"])}{ikon}</div>'
                f'<div class="idx-kv {m["kelas_nilai"]}" title="{escape(m["nilai"], quote=True)}">{escape(m["nilai"])}</div>'
                f'<div class="idx-ks {m["kelas_ket"]}" title="{escape(m["ket"], quote=True)}">{escape(m["ket"]) or "&nbsp;"}</div></div>')
    st.html(f'<div class="idx-kpi" style="--n:{len(daftar)}">{isi}</div>')


def legenda(butir: list[tuple[list[str], str]]) -> None:
    """Legenda kecil di atas grafik: [([warna, ...], teks), ...]."""
    isi = ""
    for warna, teks in butir:
        kotak = "".join(f'<i class="idx-kotak" style="background:{w}"></i>' for w in warna)
        isi += f"<span>{kotak}{escape(teks)}</span>"
    st.html(f'<div class="idx-legenda">{isi}</div>')


def tabel_ringkas(df: pd.DataFrame, kolom_arah: str) -> None:
    """Tabel kecil tanpa interaksi: kolom saham, tutup, return."""
    baris = "".join(
        f'<tr><td title="{escape(str(r.nama or ""), quote=True)}">{escape(r.kode)}</td>'
        f'<td class="idx-kanan">{fmt.angka(r.harga_tutup)}</td>'
        f'<td class="idx-kanan {kelas_arah(getattr(r, kolom_arah))}">{fmt.persen(getattr(r, kolom_arah))}</td></tr>'
        for r in df.itertuples())
    st.html('<table class="idx-tabel"><tr><th>Saham</th><th class="idx-kanan">Tutup</th>'
            f'<th class="idx-kanan">Return</th></tr>{baris}</table>')


def _warna_arah(x) -> str:
    if pd.isna(x) or x == 0:
        return ""
    return f"color: {NAIK if x > 0 else TURUN}"


def tabel(df: pd.DataFrame, kolom: dict, arah: list[str] | None = None, tinggi: int | None = None) -> None:
    """Tabel interaktif. kolom = {nama: (label, fungsi_format atau None)}.

    Lewat Styler: tampilan memakai format Indonesia, tapi pengurutan tetap memakai nilai aslinya.
    """
    data = df[list(kolom)].reset_index(drop=True)
    format_kolom = {k: f or (lambda v: fmt.KOSONG if pd.isna(v) else v) for k, (_, f) in kolom.items()}
    gaya = data.style.format(format_kolom, na_rep=fmt.KOSONG)
    if arah:
        gaya = gaya.map(_warna_arah, subset=arah)
    opsi = {"height": tinggi} if tinggi else {}
    st.dataframe(gaya, column_config={k: label for k, (label, _) in kolom.items()},
                 hide_index=True, width="stretch", **opsi)


def rapikan_grafik(fig: go.Figure, tinggi: int, legenda_tampil: bool = False) -> go.Figure:
    fig.update_layout(
        height=tinggi, separators=",.", font=dict(family=FONT, size=12, color=REDUP),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=8, t=8, b=0),
        showlegend=legenda_tampil, legend=dict(orientation="h", yanchor="top", y=-0.08, x=0, title_text=""),
        hoverlabel=dict(bgcolor=TEKS, bordercolor=TEKS, font=dict(family=FONT, size=12, color="#ffffff"), align="left"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, showline=False, ticks="", title_text="", automargin=True)
    fig.update_yaxes(gridcolor=GARIS_GRAFIK, zeroline=False, showline=False, ticks="", title_text="", automargin=True)
    return fig


def sumbu_tanggal(fig: go.Figure, tanggal: pd.Series, maks_label: int = 8) -> None:
    """Label bulan berbahasa Indonesia di sumbu X; label bawaan Plotly selalu berbahasa Inggris."""
    tanggal = pd.to_datetime(pd.Series(tanggal)).sort_values()
    # Hari bursa pertama tiap bulan, bukan tanggal 1: tanggal 1 bisa jatuh di akhir pekan yang disembunyikan sumbu.
    bulan = tanggal.groupby(tanggal.dt.to_period("M")).min()
    langkah = max(1, -(-len(bulan) // maks_label))
    pilih = bulan.iloc[::langkah]
    fig.update_xaxes(tickmode="array", tickvals=list(pilih), ticktext=[fmt.bulan_pendek(b) for b in pilih], hoverformat="%d/%m/%Y")


def tampilkan_grafik(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", theme=None, config={"displayModeBar": False})
