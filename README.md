# 🍞 FoodWaste Predictor — by Paionios

**AI Demand & Food Waste Predictor** untuk sektor F&B (Bakery, Restoran, Supermarket).
Dikembangkan oleh Tim **Paionios** untuk **COMPFEST 18 — AI Innovation Challenge**.

> MVP level mikro dari riset makro *"Prediksi Timbulan Sampah Makanan di Kabupaten/Kota
> di Indonesia Menggunakan Machine Learning Berbasis Data SIPSN"*. Jika riset makro
> menjawab skala nasional, produk ini menjawab skala operasional harian: **berapa
> unit yang sebaiknya diproduksi hari ini** agar tidak *overstock* (food waste &
> kerugian) maupun *understock* (kehilangan penjualan)?

---

## 📋 Daftar Isi

- [Ringkasan Produk](#-ringkasan-produk)
- [Pratinjau Tampilan (UI/UX)](#-pratinjau-tampilan-uiux)
- [Arsitektur Repositori](#-arsitektur-repositori)
- [Alur Kerja Sistem](#-alur-kerja-sistem)
- [Cara Menjalankan](#-cara-menjalankan)
  - [Opsi A — Docker Compose (Direkomendasikan)](#opsi-a--docker-compose-direkomendasikan)
  - [Opsi B — Lokal Tanpa Docker](#opsi-b--lokal-tanpa-docker)
- [Konfigurasi Environment Variables](#-konfigurasi-environment-variables)
- [Struktur Output AI (JSON Schema)](#-struktur-output-ai-json-schema)
- [Mekanisme Keandalan (Error Handling)](#-mekanisme-keandalan-error-handling)
- [Tech Stack](#-tech-stack)
- [Tim Paionios](#-tim-paionios)

---

## 🎯 Ringkasan Produk

Pemilik usaha F&B setiap hari menghadapi dilema klasik: **produksi berlebih**
berujung pada sampah makanan dan kerugian modal, sementara **produksi kurang**
berujung pada kehilangan penjualan dan pelanggan kecewa. FoodWaste Predictor
membantu mengambil keputusan produksi harian secara berbasis data dengan
mengombinasikan input operasional sederhana (penjualan historis, hari, promo,
musim/event, sisa stok, cuaca) dengan analisis Generative AI (Google Gemini)
untuk menghasilkan:

| Output | Deskripsi |
|---|---|
| **Estimasi Permintaan** | Prediksi jumlah unit yang kemungkinan terjual pada hari target |
| **Rekomendasi Produksi** | Jumlah unit ideal yang sebaiknya diproduksi, memperhitungkan sisa stok |
| **Risiko Overstock** | Klasifikasi LOW / MEDIUM / HIGH, divisualisasikan sebagai gauge analog |
| **Estimasi Pengurangan Food Waste** | Potensi pengurangan food waste dibanding tanpa prediksi AI |
| **Strategic Insight** | Analisis singkat korelasi cuaca/promo/hari terhadap rekomendasi |

---

## 🎨 Pratinjau Tampilan (UI/UX)

**Skema warna** — palet "dapur segar & berkelanjutan": latar belakang putih
hangat bernuansa sage (`#F5F6F1`), header bergradasi hijau pinus tua
(`#1F4B3F → #163329`) yang mengevokasi kesegaran bahan pangan, aksen amber
hangat (`#E8A33D`) terinspirasi warna roti panggang, dan warna status risiko
yang tenang: hijau (`#2F8F5B`, aman), amber (`#D98E2B`, waspada), merah-bata
lembut (`#C1443B`, tinggi) — bukan merah alarm yang mencolok.

**Tipografi** — *Plus Jakarta Sans* (tebal, untuk judul & label) dipadu
*Inter* (untuk teks body) sesuai brief. Angka-angka KPI secara khusus
ditampilkan dengan *IBM Plex Mono*, memberi kesan "instrumen presisi" —
selaras dengan tema forecasting/prediksi.

**Layout** — Header elegan bergradasi hijau di bagian atas, menampilkan nama
produk dan badge "Tim Paionios · COMPFEST 18". Di bawahnya, layout dua kolom:

```
┌──────────────────────────────────────────────────────────────────────┐
│  🌿  FoodWaste Predictor by Paionios              [Tim Paionios · C18]│
│      AI Demand & Food Waste Predictor untuk F&B                      │
├───────────────────────────┬────────────────────────────────────────--┤
│ 📦 PARAMETER OPERASIONAL   │  📈 DASHBOARD ANALYTICS                  │
│ ┌───────────────────────┐ │  ┌─────────────────────────────────────┐ │
│ │ Jenis Usaha (dropdown)│ │  │ Tren Penjualan Historis (14 hari)   │ │
│ │ Penjualan | Harga     │ │  │        ╭─╮      ╭─╮                 │ │
│ │ Hari      | Promo     │ │  │   ╭─╮  │ │  ╭─╮  │ │                 │ │
│ │ Jam Operasional ▬▬●▬▬ │ │  │ ──╯ ╰──╯ ╰──╯ ╰──╯ ╰────            │ │
│ │ Musim     | Cuaca     │ │  └─────────────────────────────────────┘ │
│ │ Sisa Stok Kemarin     │ │  ┌──────────────── RISIKO OVERSTOCK ───┐ │
│ │                       │ │  │        ╭───────────╮                │ │
│ │ [🔮 Prediksi Produksi │ │  │      ╱   gauge dial   ╲   ← jarum    │ │
│ │      Ideal]           │ │  │   (hijau·amber·merah)                │ │
│ └───────────────────────┘ │  │        "AMAN / WASPADA / TINGGI"     │ │
│                            │  └──────────────────────────────────────┘ │
│                            │  ┌──────────┐ ┌──────────┐ ┌───────────┐│
│                            │  │ Estimasi │ │ Rekomen  │ │ Pengurang ││
│                            │  │ Permintaan│ │ Produksi │ │ Food Waste││
│                            │  │  187 unit│ │ 165 unit │ │    18%   ││
│                            │  └──────────┘ └──────────┘ └───────────┘│
│                            │  ┌─────────────────────────────────────┐ │
│                            │  │ ✨ Strategic Insight                │ │
│                            │  │ "Permintaan hari Sabtu meningkat... │ │
│                            │  └─────────────────────────────────────┘ │
└───────────────────────────┴────────────────────────────────────────--┘
```

**Elemen signature** — kartu "Risiko Overstock" menampilkan **gauge
semi-circular** (mirip jarum termometer oven) yang terbagi tiga zona warna
(hijau–amber–merah); jarum otomatis mengarah ke zona sesuai klasifikasi AI,
sehingga risiko langsung terasa secara visual, bukan sekadar teks berwarna.

**Interaksi & animasi** — tombol prediksi memiliki efek *hover* terangkat
halus (`translateY(-1px)` + shadow membesar), kartu KPI memiliki efek
*hover* serupa, dan seluruh transisi dinonaktifkan otomatis bila pengguna
mengaktifkan preferensi *reduced motion* di sistem operasinya. Sebelum
prediksi pertama dilakukan, panel dashboard menampilkan *empty state* yang
ramah alih-alih kosong tanpa penjelasan; apabila AI engine gagal total,
tampil *banner* kuning transparan yang menjelaskan bahwa sistem beralih ke
mode cadangan (rule-based), tanpa pernah menampilkan pesan error teknis
mentah ke pengguna.

---

## 🏗️ Arsitektur Repositori

```
/FoodWaste-Predict-Paionios
│
├── /src
│   ├── __init__.py
│   ├── config.py          # Manajemen API Key & environment variables (fail-soft)
│   ├── ai_engine.py       # Prompting Gemini, sanitasi JSON, retry & fallback
│   ├── data_processor.py  # Mock data historis & model fallback rule-based
│   └── ui_components.py   # Builder komponen Gradio & renderer HTML/KPI/gauge
│
├── /assets
│   └── custom_style.css   # Design token, Google Fonts, KPI card, gauge, animasi
│
├── .env.example           # Template environment variables
├── .gitignore
├── app.py                 # Entry point: merakit layout & wiring event
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

Prinsip desain arsitektur:

- **Separation of concerns** — `app.py` tidak berisi logic AI maupun styling;
  hanya merakit komponen dan menghubungkan event.
- **Fail-soft by design** — setiap lapisan (`config` → `ai_engine` →
  `data_processor`) punya jalur fallback sendiri, sehingga kegagalan satu
  komponen (mis. API key kosong) tidak pernah membuat seluruh aplikasi crash.
- **Testable in isolation** — setiap modul di `src/` dapat di-*unit test*
  tanpa perlu menjalankan Gradio server maupun memanggil API eksternal
  sungguhan (lihat fungsi `heuristic_fallback_prediction` sebagai contoh
  logic yang sepenuhnya deterministik/lokal).

---

## 🔄 Alur Kerja Sistem

1. Pengguna mengisi 8 parameter operasional pada panel kiri (Historical
   Sales, Harga Produk, Hari, Jam Operasional, Status Promo, Musim/Event,
   Sisa Stok Kemarin, Prakiraan Cuaca) lalu menekan **"Prediksi Produksi
   Ideal"**.
2. `app.py` memvalidasi input numerik dasar, lalu memanggil
   `data_processor.generate_mock_history()` untuk membangun grafik tren
   14 hari terakhir sebagai konteks visual.
3. `app.py` membangun `PredictionRequest` dan memanggil
   `ai_engine.generate_prediction()`.
4. `ai_engine.py` menyusun prompt terstruktur, memanggil Gemini API
   (`gemini-3.7-flash`) dengan mode `response_mime_type="application/json"`,
   lalu membersihkan (`regex`) dan memvalidasi respons.
   - Jika berhasil → hasil dinormalisasi dan dikembalikan (`source: ai_model`).
   - Jika gagal setelah beberapa kali retry (API key kosong, kuota habis,
     JSON tidak valid, dsb.) → otomatis memanggil
     `data_processor.heuristic_fallback_prediction()` sebagai jaring
     pengaman (`source: fallback_heuristic`).
5. `ui_components.render_dashboard()` mengubah hasil (dari sumber mana pun)
   menjadi HTML dashboard: gauge risiko, 3 KPI card, dan panel insight.
6. Gradio merender ulang komponen `gr.Plot` dan `gr.HTML` di kolom kanan
   tanpa me-refresh seluruh halaman.

---

## 🚀 Cara Menjalankan

### Opsi A — Docker Compose (Direkomendasikan)

```bash
# 1. Clone repositori
git clone <url-repositori-anda>
cd FoodWaste-Predict-Paionios

# 2. Siapkan environment variables
cp .env.example .env
# lalu buka .env dan isi GEMINI_API_KEY dengan API key Anda
# (dapatkan gratis di https://aistudio.google.com/apikey)

# 3. Build & jalankan
docker-compose up --build
```

Aplikasi dapat diakses di **http://localhost:7860**.

> Catatan: apabila `.env` belum dibuat atau `GEMINI_API_KEY` masih kosong,
> aplikasi **tetap akan berjalan normal** — dashboard akan menampilkan
> estimasi dari mode cadangan (rule-based) beserta banner penjelasan,
> sehingga proses instalasi tidak pernah gagal hanya karena API key belum
> tersedia (sesuai persyaratan replikasi juri kompetisi).

Untuk menghentikan aplikasi:

```bash
docker-compose down
```

### Opsi B — Lokal Tanpa Docker

Membutuhkan Python 3.11+.

```bash
# 1. Buat virtual environment
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Siapkan environment variables
cp .env.example .env
# isi GEMINI_API_KEY pada file .env

# 4. Jalankan aplikasi
python app.py
```

Aplikasi akan tersedia di **http://localhost:7860**.

---

## ⚙️ Konfigurasi Environment Variables

Seluruh variabel dijelaskan lengkap pada [`.env.example`](./.env.example).
Ringkasannya:

| Variabel | Wajib | Default | Keterangan |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ | *(kosong)* | API key Google Gemini. Tanpa ini, sistem otomatis memakai mode fallback rule-based |
| `GEMINI_MODEL` | ❌ | `gemini-3.7-flash` | Model Gemini Flash yang dipakai |
| `GEMINI_TEMPERATURE` | ❌ | `0.4` | Kreativitas output model |
| `GEMINI_MAX_RETRIES` | ❌ | `2` | Jumlah percobaan ulang sebelum fallback |
| `GEMINI_TIMEOUT_SECONDS` | ❌ | `30` | Batas waktu panggilan API |
| `APP_TITLE` / `APP_SUBTITLE` / `TEAM_NAME` | ❌ | — | Identitas yang tampil di header UI |
| `GRADIO_SERVER_PORT` | ❌ | `7860` | Port server aplikasi |
| `APP_DEBUG` | ❌ | `false` | Tampilkan traceback di log container untuk debugging |

---

## 📦 Struktur Output AI (JSON Schema)

`ai_engine.py` memaksa model untuk selalu mengembalikan objek JSON dengan
struktur berikut (divalidasi & dinormalisasi ulang di sisi kode, bukan
hanya dipercaya mentah-mentah dari model):

```json
{
  "expected_demand": 187,
  "recommended_production": 165,
  "overstock_risk": "MEDIUM",
  "food_waste_reduction_est": "18%",
  "strategic_insight": "Permintaan hari Sabtu meningkat karena akhir pekan dan promo aktif, namun prakiraan hujan ringan sedikit menahan lonjakan. Produksi disarankan naik moderat dari rata-rata harian, dengan mempertimbangkan sisa stok kemarin agar tidak menumpuk."
}
```

`overstock_risk` selalu dinormalisasi ke salah satu dari `"LOW"`, `"MEDIUM"`,
atau `"HIGH"` — termasuk apabila model mengembalikan variasi seperti
`"HIGH / LOW MEDIUM"`, `"Tinggi"`, atau format tak terduga lainnya.

---

## 🛡️ Mekanisme Keandalan (Error Handling)

Sistem dirancang berlapis agar UI **tidak pernah** menampilkan halaman
error mentah / stack trace ke pengguna akhir:

1. **Sanitasi JSON** (`ai_engine._clean_json_text`) — menghapus pagar
   ```` ```json ... ``` ````, mengekstrak blok `{...}` pertama jika model
   menambahkan kalimat pembuka/penutup, serta membersihkan trailing comma.
2. **Validasi & normalisasi skema** (`ai_engine._validate_and_normalize`) —
   memastikan setiap field bertipe data yang benar dan tidak melempar
   exception meski satu field hilang atau salah format.
3. **Retry dengan backoff** — mencoba ulang panggilan API sebanyak
   `GEMINI_MAX_RETRIES` kali sebelum menyerah.
4. **Fallback heuristik** (`data_processor.heuristic_fallback_prediction`) —
   model rule-based transparan yang tetap memberi angka & insight yang
   masuk akal ketika seluruh percobaan AI gagal.
5. **Guard clause di `app.py`** — validasi input dasar & lapisan
   `try/except` terakhir yang menangkap error tak terduga apa pun dan
   mengubahnya menjadi pesan ramah melalui `ui_components.render_error_state`.

---

## 🧰 Tech Stack

| Layer | Teknologi |
|---|---|
| UI Framework | [Gradio](https://www.gradio.app/) Blocks (custom CSS injection) |
| Generative AI | Google Gemini API (`gemini-3.7-flash`) via `google-genai` SDK |
| Visualisasi Data | Plotly |
| Styling | Custom CSS, Google Fonts (Plus Jakarta Sans, Inter, IBM Plex Mono) |
| Containerization | Docker & Docker Compose |
| Bahasa | Python 3.11 |

---

## 👥 Tim Paionios

Dikembangkan untuk **COMPFEST 18 — AI Innovation Challenge**, sebagai
implementasi mikro dari riset *Food Waste Prediction* berbasis data SIPSN,
Bappenas, dan FAOSTAT.

---

*README ini dan seluruh kode dalam repositori disusun agar dapat langsung
di-*copy-paste* dan dieksekusi dengan `docker-compose up --build` tanpa
konfigurasi tambahan.*
