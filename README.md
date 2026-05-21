# AI Digital Health Assistant

A calm, document-style web app that helps users understand their **symptoms** and
**medical / lab reports** in simple language — powered by Google Gemini.
Educational only; does not replace a real doctor.

> ⚠️ **Disclaimer:** This tool provides general health education. It does **not**
> diagnose, prescribe, or replace a qualified healthcare professional. In an
> emergency, contact local emergency services immediately.

---

## ✨ Features

- **Symptom analysis** — enter symptoms, age, gender, medical history, language;
  get a structured AI breakdown (Summary, Possible Causes, Severity, Suggested
  Doctor, Suggested Tests, Lifestyle Suggestions, Disclaimer).
- **Free-form follow-up chat** — keep asking questions about the same case.
- **PDF medical-report analysis** — upload a lab/test report (PDF) and get a
  parameter-by-parameter table (Value · Normal Range · Status · What It Means),
  abnormal findings, the right specialist for each, follow-up tests, and a
  tailored **Eat / Avoid** lifestyle plan.
- **Scanned PDF support** — if the PDF has no text layer, pages are rendered
  to images and read by Gemini Vision automatically. No Tesseract / Poppler.
- **Multilingual** — English, Hindi, Hinglish.
- **Safe demo fallback** — if no AI key is configured (or the AI is rate-limited),
  a rule-based responder still returns safe educational guidance.
- **Cinematic dark-mode UI** — glassmorphism panels, animated background orbs,
  GitHub-flavored markdown rendering with `marked.js` + `DOMPurify`.

---

## 🧱 Tech Stack

- **Backend:** Python 3.10+, Flask, Flask-CORS, requests, python-dotenv,
  `pypdf` (text extraction), `pymupdf` (PDF-to-image for vision)
- **AI provider:** Google Gemini via OpenAI-compatible endpoint
  (`gemini-2.5-flash` by default — supports text + vision)
- **Frontend:** Static HTML / CSS / vanilla JS (no build step),
  `marked.js`, `DOMPurify`, Google Fonts (Inter + Space Grotesk)

---

## 📁 Project Structure

```
digital health assistant/
├─ backend/
│  ├─ app.py              # Flask app + all API endpoints
│  ├─ prompt.py           # Master system prompt + report-analysis prompt
│  ├─ fallback.py         # Safe rule-based responder (demo mode)
│  ├─ requirements.txt
│  ├─ .env                # ← your real API key lives here (gitignored)
│  └─ .env.example        # template (no real secret)
├─ frontend/
│  ├─ index.html
│  ├─ styles.css
│  └─ js/app.js
├─ .gitignore
└─ README.md
```

---

## 🚀 Local Setup

### 1. Install Python dependencies

```powershell
cd backend
python -m pip install -r requirements.txt
```

### 2. Get a free Google Gemini API key

1. Go to https://aistudio.google.com/app/apikey
2. Sign in → **Create API key** → copy it (starts with `AIza...`).

### 3. Configure your key

Copy the template and fill in your key:

```powershell
copy backend\.env.example backend\.env
notepad backend\.env
```

`.env` should look like:

```ini
AI_API_BASE=https://generativelanguage.googleapis.com/v1beta/openai
AI_API_MODEL=gemini-2.5-flash
AI_API_KEY=AIzaSy...your-key-here
HOST=127.0.0.1
PORT=5000
```

### 4. Run the server

```powershell
cd backend
python app.py
```

Open **http://127.0.0.1:5000/** in your browser. The badge in the header should
read **"Live AI (gemini-2.5-flash)"**. If it says "Demo mode", your key is not
being read.

---

## 🔌 API Endpoints

All endpoints return JSON.

| Method | Path                  | Body                                                       | Description                                            |
|--------|-----------------------|------------------------------------------------------------|--------------------------------------------------------|
| GET    | `/api/health`         | —                                                          | `{ ok, mode, model }`                                  |
| POST   | `/api/analyze`        | JSON: `{ symptoms, age, gender, history, language, reportText }` | Full structured symptom analysis (markdown).     |
| POST   | `/api/chat`           | JSON: `{ intake, question, history }`                      | Follow-up Q&A with conversation history.               |
| POST   | `/api/analyze-report` | `multipart/form-data`: `report` (PDF file), `language`     | PDF report analysis (text-layer or vision). Max 10 MB. |

---

## 🛡️ Safety Rules Enforced in the Prompt

- Never gives a final diagnosis or prescribes medicines / dosages.
- Uses safe wording (*"may be associated with…"*, *"please consult a doctor"*).
- Detects possible emergencies and clearly advises immediate medical attention.
- Always appends a disclaimer.

---

## 🔐 Secrets & Deployment Notes

- `.env` is **gitignored**. Never commit your real key.
- For hosted deployments (Render, Railway, Hugging Face Spaces, etc.), set
  `AI_API_BASE`, `AI_API_MODEL`, `AI_API_KEY` as **platform environment
  variables** — do not bake them into the repo.
- A production WSGI server like `gunicorn` is recommended instead of
  `python app.py` for hosting.

---

## 📜 License

For educational and personal use. Not certified for clinical decision-making.
