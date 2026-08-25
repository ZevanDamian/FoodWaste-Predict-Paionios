"""
ui_components.py
-----------------
Kumpulan komponen layout UI Gradio yang dipisahkan dari `app.py` agar
`app.py` tetap ringkas dan mudah dibaca sebagai "entry point" saja.

Modul ini dibagi menjadi tiga kelompok fungsi:
1. `load_custom_css()`      -> memuat isi assets/custom_style.css sebagai string.
2. `build_*()`              -> membangun komponen Gradio (dipanggil di dalam
                               `with gr.Blocks(): ...` pada app.py).
3. `render_*()`             -> membangun string HTML murni (dipakai untuk
                               mengisi komponen gr.HTML/gr.Markdown secara
                               dinamis setiap kali tombol prediksi ditekan).

Pemisahan ini membuat setiap bagian tampilan (header, form input, dashboard,
KPI card, gauge risiko) dapat diuji dan diubah secara independen tanpa
menyentuh logic AI di ai_engine.py maupun data di data_processor.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import gradio as gr

from src.config import RISK_COLOR_MAP, settings

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

# --- Ikon inline (SVG, gaya garis/"stroke" minimalis, tanpa dependensi CDN) --
_ICON_BOX = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round"><path d="M21 8L12 3 3 8v8l9 5 9-5V8z"/>'
    '<path d="M3 8l9 5 9-5"/><path d="M12 13v8"/></svg>'
)
_ICON_TREND = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round"><path d="M3 17l6-6 4 4 8-8"/>'
    '<path d="M15 7h6v6"/></svg>'
)
_ICON_LEAF = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M11 20A7 7 0 0 1 4 13c0-5 5-11 12-11 0 7-2 11-5 14a7 7 0 0 1-5 4z"/>'
    '<path d="M5 21c3-3 5-6 6-9"/></svg>'
)
_ICON_SPARK = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M12 3l1.8 4.9L19 9.7l-4.9 1.8L12 17l-1.8-4.9L5 10.3l4.9-1.8L12 3z"/></svg>'
)
_ICON_ALERT = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M12 9v4M12 17h.01M10.3 3.9L1.8 18a1.8 1.8 0 0 0 1.6 2.7h17.2a1.8 1.8 0 0 0 '
    '1.6-2.7L13.7 3.9a1.8 1.8 0 0 0-3.4 0z"/></svg>'
)


def load_custom_css() -> str:
    """Membaca isi assets/custom_style.css. Mengembalikan string kosong jika file tidak ada
    (agar aplikasi tetap bisa dijalankan meski tanpa styling khusus)."""
    css_path = _ASSETS_DIR / "custom_style.css"
    try:
        return css_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


# ---------------------------------------------------------------------------
# BUILDERS — dipanggil di dalam `with gr.Blocks(): ...` pada app.py
# ---------------------------------------------------------------------------

def build_header() -> gr.HTML:
    """Header aplikasi: judul, subjudul, dan badge tim."""
    html = f"""
    <div class="fwp-header">
        <div class="fwp-header__brand">
            <div class="fwp-header__logo">{_ICON_LEAF}</div>
            <div class="fwp-header__text">
                <h1>{settings.app_title}</h1>
                <p>{settings.app_subtitle}</p>
            </div>
        </div>
        <div class="fwp-header__badge">Tim {settings.team_name} &middot; COMPFEST 18</div>
    </div>
    """
    return gr.HTML(html)


def build_input_form() -> dict:
    """
    Membangun panel input (kartu putih di kolom kiri).
    Mengembalikan dict berisi seluruh komponen input agar mudah dirujuk
    oleh app.py saat wiring event (mis. `components["historical_sales"]`).
    """
    with gr.Column(elem_classes=["fwp-card", "fwp-input-panel"]):
        gr.HTML(
            f'<div class="fwp-card__title">{_ICON_BOX} '
            '<span>Parameter Operasional Harian</span></div>'
        )

        jenis_usaha = gr.Dropdown(
            label="Jenis Usaha",
            choices=["Bakery", "Restoran", "Supermarket"],
            value="Bakery",
        )

        with gr.Row():
            historical_sales = gr.Number(
                label="Rata-rata Penjualan Historis (unit/hari)",
                value=100,
                minimum=0,
                precision=0,
            )
            harga_produk = gr.Number(
                label="Harga Produk (Rp / unit)",
                value=15000,
                minimum=0,
                precision=0,
            )

        with gr.Row():
            hari = gr.Dropdown(
                label="Hari Prediksi",
                choices=["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"],
                value="Jumat",
            )
            status_promo = gr.Dropdown(
                label="Status Promo",
                choices=["Tidak Ada Promo", "Promo Aktif"],
                value="Tidak Ada Promo",
            )

        jam_operasional = gr.Slider(
            label="Jam Operasional (per hari)",
            minimum=1,
            maximum=24,
            step=1,
            value=10,
        )

        with gr.Row():
            musim = gr.Dropdown(
                label="Musim / Event",
                choices=[
                    "Normal",
                    "Ramadhan",
                    "Lebaran",
                    "Natal & Tahun Baru",
                    "Libur Sekolah",
                    "Cuaca Ekstrem",
                ],
                value="Normal",
            )
            prakiraan_cuaca = gr.Dropdown(
                label="Prakiraan Cuaca (opsional)",
                choices=["Cerah", "Berawan", "Hujan Ringan", "Hujan Lebat", "Tidak Diketahui"],
                value="Cerah",
            )

        sisa_stok_kemarin = gr.Number(
            label="Sisa Stok Kemarin (unit belum terjual)",
            value=10,
            minimum=0,
            precision=0,
        )

        predict_button = gr.Button(
            "🔮 Prediksi Produksi Ideal",
            elem_classes=["fwp-predict-btn"],
            variant="primary",
        )

    return {
        "jenis_usaha": jenis_usaha,
        "historical_sales": historical_sales,
        "harga_produk": harga_produk,
        "hari": hari,
        "status_promo": status_promo,
        "jam_operasional": jam_operasional,
        "musim": musim,
        "prakiraan_cuaca": prakiraan_cuaca,
        "sisa_stok_kemarin": sisa_stok_kemarin,
        "predict_button": predict_button,
    }


def build_dashboard_shell() -> Tuple[gr.HTML, gr.Plot, gr.HTML]:
    """
    Membangun kerangka kolom kanan (Dashboard Analytics): judul, slot chart
    historis, dan slot utama untuk KPI cards yang akan diisi secara dinamis.
    Mengembalikan tuple (title_html, history_plot, result_html) agar app.py
    dapat memperbarui `result_html` dan `history_plot` setelah prediksi.
    """
    with gr.Column(elem_classes=["fwp-dashboard-panel"]):
        title_html = gr.HTML(
            f'<div class="fwp-card__title">{_ICON_TREND} '
            '<span>Dashboard Analytics</span></div>'
        )
        with gr.Column(elem_classes=["fwp-card"]):
            gr.HTML('<div class="fwp-subtitle">Tren Penjualan Historis (14 Hari Terakhir)</div>')
            history_plot = gr.Plot(label=None, show_label=False)

        result_html = gr.HTML(render_empty_state())

    return title_html, history_plot, result_html


# ---------------------------------------------------------------------------
# RENDERERS — menghasilkan string HTML murni untuk gr.HTML
# ---------------------------------------------------------------------------

def render_empty_state() -> str:
    """Tampilan awal dashboard sebelum pengguna menekan tombol prediksi."""
    return f"""
    <div class="fwp-empty-state">
        <div class="fwp-empty-state__icon">{_ICON_SPARK}</div>
        <p><strong>Belum ada prediksi.</strong></p>
        <p>Isi parameter operasional di panel kiri, lalu klik
        <em>"Prediksi Produksi Ideal"</em> untuk melihat estimasi permintaan,
        rekomendasi produksi, dan tingkat risiko overstock.</p>
    </div>
    """


def render_error_state(message: str) -> str:
    """Tampilan error yang ramah pengguna (tidak pernah menampilkan stack trace mentah)."""
    return f"""
    <div class="fwp-error-state">
        <div class="fwp-error-state__icon">{_ICON_ALERT}</div>
        <p><strong>Prediksi tidak dapat diproses.</strong></p>
        <p>{message}</p>
    </div>
    """


def _risk_gauge_svg(risk_level: str) -> str:
    """
    Membangun gauge semi-circular (0°–180°) sebagai elemen visual utama
    ("signature element") kartu risiko overstock. Jarum menunjuk ke tengah
    zona LOW / MEDIUM / HIGH sesuai `risk_level`.
    """
    angle_map = {"LOW": 30, "MEDIUM": 90, "HIGH": 150}
    needle_angle = angle_map.get(risk_level, 90)
    colors = RISK_COLOR_MAP.get(risk_level, RISK_COLOR_MAP["MEDIUM"])

    # Titik pangkal jarum di (100, 100), panjang jarum 70px, arah 0° = ke kanan.
    import math

    radians = math.radians(180 - needle_angle)
    needle_x = 100 + 70 * math.cos(radians)
    needle_y = 100 - 70 * math.sin(radians)

    return f"""
    <svg viewBox="0 0 200 120" class="fwp-gauge">
        <path d="M20,100 A80,80 0 0,1 73,26" fill="none" stroke="#2F8F5B" stroke-width="14" stroke-linecap="round"/>
        <path d="M73,26 A80,80 0 0,1 127,26" fill="none" stroke="#D98E2B" stroke-width="14" stroke-linecap="round"/>
        <path d="M127,26 A80,80 0 0,1 180,100" fill="none" stroke="#C1443B" stroke-width="14" stroke-linecap="round"/>
        <line x1="100" y1="100" x2="{needle_x:.1f}" y2="{needle_y:.1f}"
              stroke="{colors['text']}" stroke-width="4" stroke-linecap="round"/>
        <circle cx="100" cy="100" r="8" fill="{colors['text']}"/>
    </svg>
    """


def render_dashboard(prediction: dict) -> str:
    """
    Merender seluruh hasil prediksi (dict dari ai_engine.generate_prediction
    atau data_processor.heuristic_fallback_prediction) menjadi HTML dashboard:
    gauge risiko, tiga KPI card, dan panel strategic insight.
    """
    risk_level = prediction.get("overstock_risk", "MEDIUM")
    colors = RISK_COLOR_MAP.get(risk_level, RISK_COLOR_MAP["MEDIUM"])
    is_fallback = prediction.get("source") == "fallback_heuristic"

    fallback_banner = ""
    if is_fallback:
        fallback_banner = f"""
        <div class="fwp-fallback-banner">
            {_ICON_ALERT}
            <span>Mode cadangan aktif: AI engine tidak tersedia, menampilkan estimasi
            berbasis aturan (rule-based). Periksa GEMINI_API_KEY pada file .env.</span>
        </div>
        """

    return f"""
    {fallback_banner}
    <div class="fwp-kpi-grid">
        <div class="fwp-kpi-card fwp-kpi-card--risk" style="--risk-bg:{colors['bg']};
             --risk-border:{colors['border']}; --risk-text:{colors['text']};">
            <div class="fwp-kpi-card__label">Risiko Overstock</div>
            {_risk_gauge_svg(risk_level)}
            <div class="fwp-kpi-card__risk-tag">{colors['label']}</div>
        </div>

        <div class="fwp-kpi-card">
            <div class="fwp-kpi-card__icon">{_ICON_TREND}</div>
            <div class="fwp-kpi-card__label">Estimasi Permintaan</div>
            <div class="fwp-kpi-card__value">{prediction.get('expected_demand', 0):,} <span>unit</span></div>
        </div>

        <div class="fwp-kpi-card">
            <div class="fwp-kpi-card__icon">{_ICON_BOX}</div>
            <div class="fwp-kpi-card__label">Rekomendasi Produksi</div>
            <div class="fwp-kpi-card__value">{prediction.get('recommended_production', 0):,} <span>unit</span></div>
        </div>

        <div class="fwp-kpi-card fwp-kpi-card--accent">
            <div class="fwp-kpi-card__icon">{_ICON_LEAF}</div>
            <div class="fwp-kpi-card__label">Estimasi Pengurangan Food Waste</div>
            <div class="fwp-kpi-card__value">{prediction.get('food_waste_reduction_est', '0%')}</div>
        </div>
    </div>

    <div class="fwp-insight-panel">
        <div class="fwp-insight-panel__title">{_ICON_SPARK} Strategic Insight</div>
        <p>{prediction.get('strategic_insight', '-')}</p>
    </div>
    """
