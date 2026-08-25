# ==============================================================================
# Dockerfile — FoodWaste Predictor by Paionios
# ------------------------------------------------------------------------------
# Base image ringan (slim) untuk menjaga ukuran image tetap kecil, tetap
# menyediakan Python 3.11 yang kompatibel dengan seluruh dependency di
# requirements.txt (gradio, google-genai, plotly, pandas, numpy).
# ==============================================================================

FROM python:3.11-slim

# Mencegah Python menulis file .pyc & memastikan log langsung tampil (unbuffered)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Salin requirements terlebih dahulu agar layer cache Docker optimal:
# rebuild image tidak perlu install ulang dependency jika hanya source code
# yang berubah.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Salin seluruh source code aplikasi
COPY . .

# Port default Gradio
EXPOSE 7860

# Healthcheck sederhana: memastikan proses HTTP server merespons
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860', timeout=4)" || exit 1

# Jalankan sebagai non-root user demi keamanan
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

CMD ["python", "app.py"]
