"""
config.py
---------
Manajemen konfigurasi terpusat untuk aplikasi FoodWaste Predictor.

Modul ini bertanggung jawab untuk:
1. Memuat environment variables (dari file .env saat development lokal,
   atau dari environment container saat berjalan di Docker).
2. Menyediakan nilai default yang aman apabila sebuah variabel tidak diset,
   sehingga aplikasi tetap bisa berjalan (fail-soft) alih-alih crash saat import.
3. Menjadi single-source-of-truth untuk konstanta lintas modul (nama model,
   batas retry, skema risiko, dsb).

Catatan penting terkait keandalan:
- Modul ini SENGAJA tidak melempar exception saat GEMINI_API_KEY kosong.
  Validasi "apakah API key valid" baru dilakukan saat pemanggilan AI
  benar-benar terjadi (di ai_engine.py). Ini membuat `docker-compose up`
  tidak pernah gagal hanya karena developer lupa mengisi .env — UI tetap
  terbuka dan akan menampilkan pesan error yang ramah saat tombol prediksi
  ditekan tanpa API key yang valid.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# python-dotenv bersifat opsional secara runtime: apabila package belum
# terpasang (mis. environment produksi yang inject env vars langsung),
# aplikasi tetap harus bisa berjalan tanpa ImportError.
try:
    from dotenv import load_dotenv

    _ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=_ENV_PATH, override=False)
except ImportError:  # pragma: no cover - fallback environment tanpa dotenv
    pass


def _get_bool(key: str, default: bool) -> bool:
    """Parse environment variable menjadi boolean secara toleran."""
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(key: str, default: int) -> int:
    """Parse environment variable menjadi integer, fallback ke default jika invalid."""
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def _get_float(key: str, default: float) -> float:
    """Parse environment variable menjadi float, fallback ke default jika invalid."""
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw.strip())
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Kontainer immutable untuk seluruh konfigurasi aplikasi."""

    # --- Kredensial & Model AI ---
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", "").strip())
    gemini_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.7-flash").strip()
        or "gemini-3.7-flash"
    )
    gemini_temperature: float = field(default_factory=lambda: _get_float("GEMINI_TEMPERATURE", 0.4))
    gemini_max_retries: int = field(default_factory=lambda: _get_int("GEMINI_MAX_RETRIES", 2))
    gemini_timeout_seconds: int = field(default_factory=lambda: _get_int("GEMINI_TIMEOUT_SECONDS", 30))

    # --- Identitas Aplikasi ---
    app_title: str = field(
        default_factory=lambda: os.getenv("APP_TITLE", "FoodWaste Predictor by Paionios")
    )
    app_subtitle: str = field(
        default_factory=lambda: os.getenv(
            "APP_SUBTITLE",
            "AI Demand & Food Waste Predictor untuk Bakery, Restoran, dan Supermarket",
        )
    )
    team_name: str = field(default_factory=lambda: os.getenv("TEAM_NAME", "Paionios"))

    # --- Server / Runtime ---
    server_name: str = field(default_factory=lambda: os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"))
    server_port: int = field(default_factory=lambda: _get_int("GRADIO_SERVER_PORT", 7860))
    share: bool = field(default_factory=lambda: _get_bool("GRADIO_SHARE", False))
    debug: bool = field(default_factory=lambda: _get_bool("APP_DEBUG", False))

    @property
    def has_valid_api_key(self) -> bool:
        """API key dianggap valid secara sintaksis jika tidak kosong dan bukan placeholder."""
        placeholder_values = {"", "your_api_key_here", "changeme", "xxxxxxxxxx"}
        return self.gemini_api_key.strip().lower() not in placeholder_values


# Skema kategori risiko overstock yang diizinkan. Dipakai untuk normalisasi
# output AI di ai_engine.py agar dashboard tidak pernah menerima nilai
# risiko yang tidak dikenal.
RISK_LEVELS = ("LOW", "MEDIUM", "HIGH")

# Palet warna per level risiko, dipakai oleh ui_components.py agar warna
# KPI card konsisten dengan assets/custom_style.css.
RISK_COLOR_MAP = {
    "LOW": {
        "bg": "#E7F4EC",
        "border": "#2F8F5B",
        "text": "#1E5C3B",
        "label": "AMAN",
    },
    "MEDIUM": {
        "bg": "#FCF1DE",
        "border": "#D98E2B",
        "text": "#8A5A12",
        "label": "WASPADA",
    },
    "HIGH": {
        "bg": "#FBE9E7",
        "border": "#C1443B",
        "text": "#7A241D",
        "label": "RISIKO TINGGI",
    },
}

# Instance tunggal yang diimpor oleh modul lain: `from src.config import settings`
settings = Settings()


def get_masked_api_key() -> str:
    """Mengembalikan representasi API key yang aman untuk ditampilkan di UI/log."""
    key = settings.gemini_api_key
    if not key:
        return "(tidak diset)"
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"
