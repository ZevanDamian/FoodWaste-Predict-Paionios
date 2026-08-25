"""
data_processor.py
------------------
Modul pengolahan data untuk FoodWaste Predictor.

Tanggung jawab modul ini:
1. Menghasilkan mock data historis penjualan (14 hari terakhir) berdasarkan
   parameter yang diinput pengguna, untuk divisualisasikan di dashboard
   sebagai konteks tren sebelum prediksi AI ditampilkan.
2. Menyediakan `heuristic_fallback_prediction()`, sebuah model rule-based
   sederhana yang dipakai sebagai jaring pengaman (safety net) apabila
   AI engine gagal total (mis. API key tidak valid, kuota habis, atau
   respons tidak bisa di-parse setelah seluruh mekanisme retry). Dengan
   adanya fallback ini, dashboard TIDAK PERNAH kosong / error mentah —
   selalu ada angka yang bisa ditampilkan ke pengguna, disertai penanda
   bahwa angka tersebut berasal dari mode cadangan, bukan AI.
3. Fungsi bantu untuk membangun grafik tren historis (Plotly) yang
   mengikuti palet warna aplikasi.

Semua fungsi di modul ini murni deterministik / berbasis random seed lokal
sehingga aman dipanggil berulang kali tanpa side effect ke luar aplikasi
(tidak ada I/O ke disk maupun jaringan).
"""

from __future__ import annotations

import datetime as _dt
import random
from dataclasses import dataclass
from typing import List

import plotly.graph_objects as go

# Palet warna dashboard — harus konsisten dengan assets/custom_style.css
COLOR_PRIMARY = "#1F4B3F"
COLOR_PRIMARY_LIGHT = "#2F8F5B"
COLOR_ACCENT_AMBER = "#E8A33D"
COLOR_MUTED = "#6B7568"
COLOR_GRID = "#E3E1D8"

_DAY_ORDER = [
    "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu",
]

_WEEKEND_MULTIPLIER = {
    "Senin": 0.95, "Selasa": 0.92, "Rabu": 0.97, "Kamis": 1.0,
    "Jumat": 1.15, "Sabtu": 1.35, "Minggu": 1.2,
}

_SEASON_MULTIPLIER = {
    "Normal": 1.0,
    "Ramadhan": 1.25,
    "Lebaran": 1.5,
    "Natal & Tahun Baru": 1.35,
    "Libur Sekolah": 1.15,
    "Cuaca Ekstrem": 0.8,
}

_WEATHER_MULTIPLIER = {
    "Cerah": 1.05,
    "Berawan": 1.0,
    "Hujan Ringan": 0.92,
    "Hujan Lebat": 0.78,
    "Tidak Diketahui": 1.0,
}


@dataclass
class HistoricalPoint:
    """Satu titik data historis harian untuk keperluan chart."""

    date: _dt.date
    day_name: str
    units_sold: int


def generate_mock_history(
    historical_sales: float,
    hari_prediksi: str,
    musim: str = "Normal",
    n_days: int = 14,
    seed: int | None = None,
) -> List[HistoricalPoint]:
    """
    Menghasilkan mock data historis `n_days` hari terakhir yang "masuk akal"
    di sekitar angka `historical_sales` yang diinput pengguna, dengan pola
    mingguan (weekend uplift) dan sedikit noise acak agar terlihat natural
    pada grafik tren.

    Parameter
    ---------
    historical_sales : angka rata-rata penjualan harian yang diinput user,
        dipakai sebagai basis (baseline) mock data.
    hari_prediksi : nama hari (Indonesia) yang menjadi acuan hari terakhir
        pada rentang historis yang dihasilkan.
    musim : event/musim yang memengaruhi sedikit variasi baseline.
    n_days : jumlah hari historis yang dihasilkan (default 14 hari).
    seed : seed random opsional untuk hasil yang reproducible (mis. saat testing).
    """
    rng = random.Random(seed)
    baseline = max(float(historical_sales), 1.0)
    season_factor = _SEASON_MULTIPLIER.get(musim, 1.0)

    try:
        anchor_index = _DAY_ORDER.index(hari_prediksi)
    except ValueError:
        anchor_index = 0

    points: List[HistoricalPoint] = []
    today = _dt.date.today()

    for offset in range(n_days - 1, -1, -1):
        day_index = (anchor_index - offset) % 7
        day_name = _DAY_ORDER[day_index]
        weekday_factor = _WEEKEND_MULTIPLIER.get(day_name, 1.0)
        noise = rng.uniform(0.88, 1.12)

        value = baseline * weekday_factor * season_factor * noise
        points.append(
            HistoricalPoint(
                date=today - _dt.timedelta(days=offset),
                day_name=day_name,
                units_sold=max(int(round(value)), 0),
            )
        )

    return points


def build_history_figure(history: List[HistoricalPoint]) -> go.Figure:
    """Membangun grafik tren historis (Plotly) bergaya minimal, selaras tema aplikasi."""
    x_labels = [f"{p.day_name[:3]}\n{p.date.strftime('%d/%m')}" for p in history]
    y_values = [p.units_sold for p in history]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=y_values,
            mode="lines+markers",
            line=dict(color=COLOR_PRIMARY, width=3, shape="spline"),
            marker=dict(size=6, color=COLOR_PRIMARY_LIGHT),
            fill="tozeroy",
            fillcolor="rgba(31, 75, 63, 0.08)",
            hovertemplate="%{x}<br>Unit terjual: %{y}<extra></extra>",
            name="Penjualan Historis",
        )
    )

    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=260,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=COLOR_MUTED, size=12),
        xaxis=dict(showgrid=False, showline=True, linecolor=COLOR_GRID),
        yaxis=dict(showgrid=True, gridcolor=COLOR_GRID, zeroline=False),
        showlegend=False,
        hovermode="x unified",
    )
    return fig


def heuristic_fallback_prediction(
    historical_sales: float,
    harga_produk: float,
    hari: str,
    jam_operasional: float,
    status_promo: str,
    musim: str,
    sisa_stok_kemarin: float,
    prakiraan_cuaca: str = "Tidak Diketahui",
) -> dict:
    """
    Model rule-based sederhana sebagai fallback ketika AI engine gagal total.

    Logika (transparan & auditable, cocok untuk demo/juri):
    1. Mulai dari baseline historical_sales.
    2. Kalikan dengan faktor hari (weekend uplift), faktor musim/event,
       dan faktor cuaca.
    3. Jika status promo aktif, tambahkan uplift permintaan.
    4. Kurangi target produksi dengan sisa stok kemarin (agar tidak dobel
       produksi atas stok yang masih ada).
    5. Estimasi risiko overstock berdasarkan rasio (stok kemarin + produksi)
       terhadap ekspektasi permintaan.
    """
    day_factor = _WEEKEND_MULTIPLIER.get(hari, 1.0)
    season_factor = _SEASON_MULTIPLIER.get(musim, 1.0)
    weather_factor = _WEATHER_MULTIPLIER.get(prakiraan_cuaca, 1.0)
    promo_factor = 1.2 if str(status_promo).strip().lower().startswith(("ya", "aktif", "yes")) else 1.0

    expected_demand = historical_sales * day_factor * season_factor * weather_factor * promo_factor
    expected_demand = max(expected_demand, 0.0)

    recommended_production = max(expected_demand - max(sisa_stok_kemarin, 0.0), 0.0)
    # Buffer keamanan kecil (5%) agar understock tidak terlalu agresif dipangkas.
    recommended_production *= 1.05

    total_available = recommended_production + max(sisa_stok_kemarin, 0.0)
    overstock_ratio = total_available / expected_demand if expected_demand > 0 else 1.0

    if overstock_ratio >= 1.25:
        risk = "HIGH"
        waste_reduction = "5%"
    elif overstock_ratio >= 1.08:
        risk = "MEDIUM"
        waste_reduction = "12%"
    else:
        risk = "LOW"
        waste_reduction = "22%"

    insight = (
        f"Berdasarkan perhitungan cadangan (bukan AI): permintaan pada hari {hari} "
        f"diproyeksikan {'naik' if day_factor * season_factor * weather_factor * promo_factor >= 1 else 'turun'} "
        f"dipengaruhi kombinasi pola hari, musim '{musim}', dan cuaca '{prakiraan_cuaca}'. "
        f"Produksi disarankan disesuaikan dengan sisa stok kemarin sebesar {sisa_stok_kemarin:.0f} unit "
        "agar tidak terjadi kelebihan produksi."
    )

    return {
        "expected_demand": int(round(expected_demand)),
        "recommended_production": int(round(recommended_production)),
        "overstock_risk": risk,
        "food_waste_reduction_est": waste_reduction,
        "strategic_insight": insight,
        "source": "fallback_heuristic",
    }
