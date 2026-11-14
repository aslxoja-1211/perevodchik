# Ovozli Tarjimon — O'zbekcha ➔ Ruscha AI Ovozli Tarjimon

**Ovozli Tarjimon** — foydalanuvchi o'zbek tilida gapirganida, uni bir zumda aniqlab, tabiiy rus tiliga tarjima qiluvchi va yuqori sifatli ruscha neyron ovozda (`Edge-TTS` Svetlana / Dmitry) eshittiruvchi zamonaviy Speech-to-Speech (S2ST) sun'iy intellekt tizimi.

Ushbu loyiha **Aqua Voice** arxitekturasining mantiqiy davomi bo'lib, ovozli matn tahrirlash mexanizmi o'rniga to'liq ovozli tarjimonlik (Speech-to-Speech Translation) yo'nalishiga moslashtirilgan.

---

## 🚀 Asosiy Imkoniyatlar

1. **Jonli Ovozli Kiritish (Web Audio API 16kHz PCM)**:
   - Brauzerdan to'g'ridan-to'g'ri mikrofon oqimini yozib olish (Push-to-Talk yoki Toggle).
   - Jonli HTML5 Canvas to'lqin vizualizatsiyasi (Waveform Visualizer).
2. **O'zbek Tili Nutqini Aniqlash (STT)**:
   - **Gemini Multimodal Audio**: O'zbek tili lotin alifbosi, apostroflar (`o'`, `g'`) va shevalarni mukammal tushunadi.
   - **Local Faster-Whisper** va **OpenAI Whisper** zaxira provayderlari.
3. **Tabiiy Kontekstual Tarjima**:
   - So'zma-so'z emas, balki jonli va grammatik to'g'ri rus tiliga o'girish.
   - Modellar nosozligi yoki limitlarida avtomatik failover (`gemini-3.8-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`).
   - Ikki tomonlama yo'nalish: **🇺🇿 O'zbekcha ➔ 🇷🇺 Ruscha** (asosiy) va **🇷🇺 Ruscha ➔ 🇺🇿 O'zbekcha**.
4. **Yuqori Sifatli Neyron Ovozlashtirish (TTS)**:
   - **Microsoft Edge Neural TTS**: Bepul, yuqori sifatli va cheksiz.
   - Ruscha ovozlar: `ru-RU-SvetlanaNeural` (ayol), `ru-RU-DmitryNeural` (erkak), `ru-RU-EkaterinaNeural`.
   - O'zbekcha ovozlar: `uz-UZ-MadinaNeural`, `uz-UZ-SardorNeural`.
   - Avtomatik audio ijro (`Auto-play`) va MP3 yuklab olish.
5. **Tezkorlik (Single-Shot Multimodal Pipeline)**:
   - Gemini Multimodal orqali bitta so'rovda audiodan ham o'zbekcha matn, ham ruscha tarjimani olish orqali kechikishni 2 barobar qisqartirish.
6. **Fayl Yuklash va Qo'lda Kiritish**:
   - Tayyor audio fayllarni (`.wav`, `.mp3`, `.m4a`, `.ogg`, `.webm`) yuklab tarjima qilish.
   - Matn ko'rinishida yozib ovozlashtirish.
7. **Suhbat Jurnali (History Feed)**:
   - Oldingi ovozli tarjimalar tarixi va istalgan tarjimani bir tugma bilan qayta eshitish.

---

## 🏗 Arxitektura

```text
[Brauzer Mikrofoni / Audio Fayl]
             │ (Web Audio API 16kHz PCM / Audio Chunks)
             ▼
[FastAPI Backend (/ws/translator yoki /api/v1/translate-audio)]
             │
             ├── 1. Audio Processing (PCM16 -> WAV, RMS Silence Check)
             ├── 2. Multimodal STT (Gemini Flash / Faster-Whisper)
             ├── 3. Kontekstual Tarjima (Gemini 3.1-flash-lite / Failover)
             └── 4. Neyron TTS (Edge-TTS Svetlana / Dmitry / Madina)
             │
             ▼ (MP3 Base64 / Oqimli Audio + Matnlar + Latency)
[Web UI Interfeysi (Canvas Waveform + Audio Player + Suhbat Jurnali)]
```

---

## 📁 Loyiha Tuzilmasi

```text
perevodchik/
├── app/
│   ├── audio/
│   │   ├── __init__.py
│   │   └── pcm_utils.py          # PCM16 -> WAV, RMS va davomiylik hisoblagich
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py            # Pydantic modellar va WebSocket sxemalari
│   ├── services/
│   │   ├── gemini_client.py      # Gemini klienti, model failover va xatoliklar filtri
│   │   ├── stt/                  # Speech-to-Text adapterlari (Gemini, Whisper, Mock)
│   │   ├── translation/          # O'zbekcha <-> Ruscha tarjimon xizmati
│   │   └── tts/                  # Edge-TTS va ovozlar boshqaruvi
│   ├── static/
│   │   └── index.html            # Zamonaviy Tailwind Web UI
│   ├── config.py                 # Pydantic ilova sozlamalari
│   ├── main.py                   # FastAPI server, REST API va WebSocket
│   └── pipeline.py               # Asosiy audio-tarjima-ovoz konveyeri
├── tests/                        # Pytest avtomatlashtirilgan testlari
├── .env                          # Muhit o'zgaruvchilari (API kalitlar)
├── .env.example
├── requirements.txt
├── start.ps1                     # 1-klikda ishga tushirish skripti
└── README.md
```

---

## ⚡️ Tezkor Ishga Tushirish

### 1-usul: PowerShell Skripti Orqali (Tavsiya etiladi)

```powershell
.\start.ps1
```

Skript avtomatik ravishda muhitni tekshiradi va serverni `http://127.0.0.1:8000` manzilida ishga tushiradi.

### 2-usul: Qo'lda Ishga Tushirish

```powershell
# 1. Virtual muhitni faollashtiring yoki aqua voice muhitidan foydalaning:
& "..\aqua voice\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Ishga tushgach:
- **Asosiy Ovozli Tarjimon Sahifasi:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Swagger API Hujjatlari:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Tizim Holati (Health Check):** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 🧪 Testlarni Ishga Tushirish

Loyiha to'liq `pytest` testlari bilan qamrab olingan:

```powershell
& "..\aqua voice\backend\.venv\Scripts\python.exe" -m pytest -v tests
```

---

## 📡 API Endpointlari

| Metod | Manzil | Tavsif |
|---|---|---|
| `GET` | `/` | Asosiy veb-interfeys sahifasi |
| `GET` | `/health` | Server va AI provayderlari holati |
| `GET` | `/api/v1/voices` | Mavjud neyron ovozlar ro'yxati |
| `POST` | `/api/v1/translate-text` | Matnni tarjima qilish va ovozlashtirish |
| `POST` | `/api/v1/translate-audio` | Audio faylni tarjima qilish va ovozlashtirish |
| `GET` | `/api/v1/tts` | To'g'ridan-to'g'ri MP3 ovoz hosil qilish |
| `WS` | `/ws/translator` | Jonli audio oqimi va real-vaqt tarjima WebSocket |
