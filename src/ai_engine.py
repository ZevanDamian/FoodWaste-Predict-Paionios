"""
ai_engine.py
------------
Otak AI dari FoodWaste Predictor. Modul ini membungkus seluruh interaksi
dengan Gemini API (model Gemini Flash terbaru: `gemini-3.7-flash`) melalui
Google Gen AI SDK (`google-genai`), meliputi:

1. Konstruksi prompt terstruktur dari parameter input pengguna.
2. Pemanggilan model dengan mode JSON output (`response_mime_type`)
   agar model condong mengembalikan JSON murni.
3. Sanitasi respons: membersihkan pagar markdown (```json ... ```), teks
   pembuka/penutup yang tidak diinginkan, trailing comma, dsb — sehingga
   `json.loads` tidak mudah gagal walau model sedikit "berhalusinasi".
4. Validasi & normalisasi skema output (tipe data, rentang nilai,
   kategori risiko) agar dashboard di ui_components.py selalu menerima
   struktur data yang konsisten.
5. Mekanisme retry dengan backoff sederhana, dan fallback otomatis ke
   model heuristik di data_processor.py apabila seluruh percobaan AI gagal,
   sehingga UI TIDAK PERNAH menampilkan stack trace mentah ke pengguna.

Desain ini secara sengaja memisahkan "AI call" dari "business fallback logic"
agar setiap lapisan bisa diuji dan dikembangkan secara independen.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Optional

from src.config import RISK_LEVELS, settings
from src.data_processor import heuristic_fallback_prediction

# --- Import SDK Google Gen AI secara defensif -------------------------------
# Jika package `google-genai` belum terpasang di environment (mis. saat unit
# test ringan tanpa dependency berat), modul ini tetap bisa di-import tanpa
# ImportError meledak di top-level. Error baru muncul saat client benar-benar
# dipakai, dan akan ditangani oleh AIEngineError + fallback heuristik.
try:
    from google import genai
    from google.genai import types as genai_types

    _GENAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    genai = None  # type: ignore
    genai_types = None  # type: ignore
    _GENAI_AVAILABLE = False


REQUIRED_KEYS = (
    "expected_demand",
    "recommended_production",
    "overstock_risk",
    "food_waste_reduction_est",
    "strategic_insight",
)

# Regex untuk mengekstrak blok JSON pertama dari teks apa pun, termasuk
# ketika model membungkusnya dengan ```json ... ``` atau menambahkan
# kalimat pembuka seperti "Berikut hasil analisisnya:".
_CODE_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)
_TRAILING_COMMA_PATTERN = re.compile(r",\s*([\}\]])")


class AIEngineError(Exception):
    """Exception khusus untuk seluruh kegagalan pada lapisan AI engine."""


@dataclass
class PredictionRequest:
    """Struktur input yang dikirim ke AI engine, merangkum seluruh parameter form."""

    historical_sales: float
    harga_produk: float
    hari: str
    jam_operasional: float
    status_promo: str
    musim: str
    sisa_stok_kemarin: float
    prakiraan_cuaca: str = "Tidak Diketahui"
    jenis_usaha: str = "Bakery"


def _clean_json_text(raw_text: str) -> str:
    """
    Membersihkan teks mentah dari model menjadi kandidat string JSON.

    Urutan strategi pembersihan:
    1. Coba ekstrak isi di dalam pagar ```json ... ``` jika ada.
    2. Jika tidak ada pagar, cari substring pertama yang diapit '{' dan '}'.
    3. Hapus trailing comma sebelum '}' atau ']' yang kadang muncul akibat
       halusinasi model (invalid JSON menurut spesifikasi standar).
    """
    text = raw_text.strip()

    fence_match = _CODE_FENCE_PATTERN.search(text)
    if fence_match:
        text = fence_match.group(1).strip()

    if not text.startswith("{"):
        obj_match = _JSON_OBJECT_PATTERN.search(text)
        if obj_match:
            text = obj_match.group(0).strip()

    text = _TRAILING_COMMA_PATTERN.sub(r"\1", text)
    return text


def _safe_int(value: Any, default: int = 0) -> int:
    """Konversi nilai apa pun menjadi int secara toleran (tanpa raise)."""
    try:
        if isinstance(value, str):
            value = re.sub(r"[^\d.\-]", "", value)
            if value in ("", "-", "."):
                return default
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _normalize_risk(value: Any) -> str:
    """Menormalisasi label risiko ke salah satu dari RISK_LEVELS ('LOW'/'MEDIUM'/'HIGH')."""
    text = str(value).strip().upper()
    if text in RISK_LEVELS:
        return text
    # Toleransi terhadap variasi seperti "TINGGI", "SEDANG", "RENDAH", atau
    # format gabungan aneh seperti "HIGH / LOW MEDIUM" pada contoh skema.
    if "HIGH" in text or "TINGGI" in text:
        return "HIGH"
    if "LOW" in text or "RENDAH" in text or "AMAN" in text:
        return "LOW"
    return "MEDIUM"


def _normalize_percentage(value: Any, default: str = "0%") -> str:
    """Memastikan nilai persentase selalu berformat string seperti '18%'."""
    text = str(value).strip()
    match = re.search(r"-?\d+(\.\d+)?", text)
    if not match:
        return default
    number = match.group(0)
    return f"{number}%"


def _validate_and_normalize(payload: dict) -> dict:
    """
    Memvalidasi bahwa seluruh key wajib ada, lalu menormalisasi tipe data
    setiap field agar konsisten dengan yang diharapkan ui_components.py.
    Field yang hilang akan diisi nilai default alih-alih melempar exception,
    supaya satu field yang meleset tidak menggagalkan seluruh respons.
    """
    normalized = {
        "expected_demand": _safe_int(payload.get("expected_demand"), default=0),
        "recommended_production": _safe_int(payload.get("recommended_production"), default=0),
        "overstock_risk": _normalize_risk(payload.get("overstock_risk", "MEDIUM")),
        "food_waste_reduction_est": _normalize_percentage(
            payload.get("food_waste_reduction_est"), default="0%"
        ),
        "strategic_insight": str(
            payload.get("strategic_insight")
            or "Analisis strategis tidak tersedia untuk kombinasi input ini."
        ).strip(),
        "source": "ai_model",
    }
    return normalized


def _build_prompt(request: PredictionRequest) -> str:
    """Menyusun prompt terstruktur berbahasa Indonesia untuk Gemini."""
    return f"""
Anda adalah sistem AI ahli manajemen rantai pasok dan operasional F&B
(Food & Beverage) yang bertugas memprediksi permintaan harian dan
merekomendasikan jumlah produksi ideal untuk mencegah OVERSTOCK
(kelebihan produksi yang berujung pada food waste dan kerugian finansial)
maupun UNDERSTOCK (kekurangan stok yang berujung pada kehilangan penjualan).

Data operasional yang diberikan oleh pengguna:
- Jenis usaha: {request.jenis_usaha}
- Rata-rata penjualan historis harian: {request.historical_sales} unit
- Harga produk per unit: Rp{request.harga_produk:,.0f}
- Hari prediksi: {request.hari}
- Jam operasional: {request.jam_operasional} jam per hari
- Status promo: {request.status_promo}
- Musim/Event: {request.musim}
- Sisa stok kemarin (belum terjual): {request.sisa_stok_kemarin} unit
- Prakiraan cuaca: {request.prakiraan_cuaca}

Tugas Anda:
1. Hitung estimasi permintaan (expected_demand) untuk hari yang diprediksi,
   dengan mempertimbangkan pola hari, promo, musim/event, dan cuaca.
2. Tentukan jumlah produksi yang direkomendasikan (recommended_production),
   dengan memperhitungkan sisa stok kemarin agar tidak terjadi duplikasi
   produksi atas stok yang masih tersedia.
3. Klasifikasikan tingkat risiko overstock (overstock_risk) menjadi salah
   satu dari: "LOW", "MEDIUM", atau "HIGH".
4. Estimasikan potensi pengurangan food waste (food_waste_reduction_est)
   dibandingkan skenario tanpa prediksi AI, dalam format persentase string
   (misalnya "18%").
5. Berikan strategic_insight berupa analisis singkat (maksimal 3 kalimat)
   yang menjelaskan korelasi antara cuaca/promo/hari terhadap rekomendasi
   produksi tersebut, ditulis dalam Bahasa Indonesia yang mudah dipahami
   oleh pemilik usaha non-teknis.

ATURAN OUTPUT SANGAT PENTING:
- Kembalikan HANYA satu objek JSON valid, TANPA teks pembuka, TANPA teks
  penutup, dan TANPA pagar markdown (```).
- Gunakan PERSIS struktur berikut:

{{
  "expected_demand": <integer>,
  "recommended_production": <integer>,
  "overstock_risk": "<LOW|MEDIUM|HIGH>",
  "food_waste_reduction_est": "<string persentase, misal 18%>",
  "strategic_insight": "<string, maksimal 3 kalimat>"
}}
""".strip()


def _call_gemini(prompt: str) -> str:
    """Memanggil Gemini API dan mengembalikan teks respons mentah."""
    if not _GENAI_AVAILABLE:
        raise AIEngineError(
            "Package 'google-genai' belum terpasang. Jalankan "
            "`pip install -r requirements.txt` terlebih dahulu."
        )

    if not settings.has_valid_api_key:
        raise AIEngineError(
            "GEMINI_API_KEY belum diset atau masih placeholder. "
            "Silakan isi file .env berdasarkan .env.example."
        )

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=settings.gemini_temperature,
                response_mime_type="application/json",
            ),
        )
    except Exception as exc:  # noqa: BLE001 - dibungkus ulang jadi error domain kita
        raise AIEngineError(f"Gagal memanggil Gemini API: {exc}") from exc

    text = getattr(response, "text", None)
    if not text:
        raise AIEngineError("Gemini API mengembalikan respons kosong.")
    return text


def generate_prediction(request: PredictionRequest) -> dict:
    """
    Titik masuk utama modul ini. Mengembalikan dict hasil prediksi yang
    sudah tervalidasi & ternormalisasi, siap dikonsumsi oleh ui_components.py.

    Alur eksekusi:
    1. Bangun prompt dari `request`.
    2. Coba panggil Gemini hingga `settings.gemini_max_retries + 1` kali.
       Setiap kegagalan parsing JSON akan mencoba membersihkan ulang teks
       sebelum menyerah pada percobaan tersebut.
    3. Jika seluruh percobaan AI gagal, jatuh ke `heuristic_fallback_prediction`
       (data_processor.py) sehingga pengguna tetap mendapatkan angka yang
       masuk akal beserta insight, dengan penanda `source: fallback_heuristic`.
    """
    prompt = _build_prompt(request)
    last_error: Optional[Exception] = None

    total_attempts = max(settings.gemini_max_retries + 1, 1)
    for attempt in range(1, total_attempts + 1):
        try:
            raw_text = _call_gemini(prompt)
            cleaned = _clean_json_text(raw_text)
            payload = json.loads(cleaned)

            missing_keys = [key for key in REQUIRED_KEYS if key not in payload]
            if missing_keys:
                raise AIEngineError(
                    f"Respons AI kehilangan field wajib: {', '.join(missing_keys)}"
                )

            return _validate_and_normalize(payload)

        except (AIEngineError, json.JSONDecodeError, TypeError, ValueError) as exc:
            last_error = exc
            if attempt < total_attempts:
                time.sleep(min(0.6 * attempt, 2.0))  # backoff sederhana
                continue
            break

    # Seluruh percobaan AI gagal → gunakan fallback heuristik agar UI tetap hidup.
    fallback = heuristic_fallback_prediction(
        historical_sales=request.historical_sales,
        harga_produk=request.harga_produk,
        hari=request.hari,
        jam_operasional=request.jam_operasional,
        status_promo=request.status_promo,
        musim=request.musim,
        sisa_stok_kemarin=request.sisa_stok_kemarin,
        prakiraan_cuaca=request.prakiraan_cuaca,
    )
    fallback["_error_detail"] = str(last_error) if last_error else "Unknown error"
    return fallback
