"""
app.py
------
Entry point utama aplikasi FoodWaste Predictor (Tim Paionios — COMPFEST 18
AI Innovation Challenge).

File ini sengaja dibuat SETIPIS MUNGKIN: seluruh logika berat (styling,
komponen UI, prompting AI, dan pengolahan data) sudah dipisah ke dalam
paket `src/`. `app.py` hanya bertanggung jawab untuk:
1. Merakit layout Gradio Blocks menggunakan builder dari `src/ui_components.py`.
2. Menghubungkan (wiring) event tombol prediksi ke satu fungsi handler.
3. Menjalankan server Gradio dengan konfigurasi dari `src/config.py`.

Menjalankan aplikasi:
    python app.py
atau melalui Docker:
    docker-compose up --build
"""

from __future__ import annotations

import traceback

import gradio as gr

from src.ai_engine import AIEngineError, PredictionRequest, generate_prediction
from src.config import settings
from src.data_processor import build_history_figure, generate_mock_history
from src.ui_components import (
    build_dashboard_shell,
    build_header,
    build_input_form,
    load_custom_css,
    render_dashboard,
    render_error_state,
)


def handle_prediction(
    jenis_usaha: str,
    historical_sales: float,
    harga_produk: float,
    hari: str,
    status_promo: str,
    jam_operasional: float,
    musim: str,
    prakiraan_cuaca: str,
    sisa_stok_kemarin: float,
):
    """
    Handler utama yang dipanggil setiap kali tombol "Prediksi Produksi Ideal"
    ditekan. Fungsi ini SELALU mengembalikan output yang valid untuk kedua
    komponen output (grafik & HTML dashboard) — tidak pernah membiarkan
    exception merambat ke Gradio, sesuai prinsip "100% error-free UX".
    """
    # --- Validasi input dasar (guard clause, bukan exception mentah) -------
    try:
        historical_sales = max(float(historical_sales or 0), 0.0)
        harga_produk = max(float(harga_produk or 0), 0.0)
        jam_operasional = max(float(jam_operasional or 0), 0.0)
        sisa_stok_kemarin = max(float(sisa_stok_kemarin or 0), 0.0)
    except (TypeError, ValueError):
        empty_fig = build_history_figure(generate_mock_history(100, "Senin"))
        return empty_fig, render_error_state(
            "Input numerik tidak valid. Pastikan Penjualan Historis, Harga Produk, "
            "Jam Operasional, dan Sisa Stok Kemarin diisi dengan angka."
        )

    # --- Bangun grafik tren historis (selalu berhasil, murni mock data) ----
    history_points = generate_mock_history(
        historical_sales=historical_sales,
        hari_prediksi=hari,
        musim=musim,
    )
    history_fig = build_history_figure(history_points)

    # --- Panggil AI engine (sudah membungkus retry & fallback internal) ----
    try:
        request = PredictionRequest(
            historical_sales=historical_sales,
            harga_produk=harga_produk,
            hari=hari,
            jam_operasional=jam_operasional,
            status_promo=status_promo,
            musim=musim,
            sisa_stok_kemarin=sisa_stok_kemarin,
            prakiraan_cuaca=prakiraan_cuaca,
            jenis_usaha=jenis_usaha,
        )
        prediction = generate_prediction(request)
        dashboard_html = render_dashboard(prediction)
    except Exception as exc:  # noqa: BLE001 - lapisan pertahanan terakhir
        # Seharusnya jarang tercapai karena ai_engine.py sudah punya fallback
        # sendiri, tapi tetap disediakan agar UI tidak pernah menampilkan
        # traceback mentah ke pengguna apa pun penyebabnya.
        if settings.debug:
            traceback.print_exc()
        dashboard_html = render_error_state(
            f"Terjadi kesalahan tak terduga saat memproses prediksi: {exc}"
        )

    return history_fig, dashboard_html


def build_app() -> gr.Blocks:
    """Merakit seluruh layout aplikasi menjadi satu objek `gr.Blocks`."""
    with gr.Blocks(
        title=settings.app_title,
        css=load_custom_css(),
        theme=gr.themes.Soft(),
        analytics_enabled=False,
    ) as demo:
        build_header()

        with gr.Row(equal_height=False):
            with gr.Column(scale=2, min_width=340):
                inputs = build_input_form()

            with gr.Column(scale=3, min_width=420):
                _title_html, history_plot, result_html = build_dashboard_shell()

        inputs["predict_button"].click(
            fn=handle_prediction,
            inputs=[
                inputs["jenis_usaha"],
                inputs["historical_sales"],
                inputs["harga_produk"],
                inputs["hari"],
                inputs["status_promo"],
                inputs["jam_operasional"],
                inputs["musim"],
                inputs["prakiraan_cuaca"],
                inputs["sisa_stok_kemarin"],
            ],
            outputs=[history_plot, result_html],
            api_name="predict",
        )

        # Muat grafik tren historis default begitu aplikasi pertama kali dibuka,
        # agar dashboard tidak terlihat kosong sebelum pengguna menekan tombol.
        demo.load(
            fn=lambda: build_history_figure(generate_mock_history(100, "Jumat")),
            inputs=None,
            outputs=[history_plot],
        )

    return demo


if __name__ == "__main__":
    app = build_app()
    app.queue()
    app.launch(
        server_name=settings.server_name,
        server_port=settings.server_port,
        share=settings.share,
        show_api=False,
    )
