# AI Digital Health Assistant

A calm, multi-page web app that helps users understand their **symptoms** and
**medical / lab reports** in simple language — powered by Google Gemini.
Educational only; does not replace a real doctor.

🌐 **Live:** https://digital-health-assistant.onrender.com/

> ⚠️ **Disclaimer:** This tool provides general health education. It does **not**
> diagnose, prescribe, or replace a qualified healthcare professional. In an
> emergency, contact local emergency services immediately.

---

## ✨ Features

- **Three-page Medical Sky UI** — clean light theme with a marketing **home**
  page (hero + features), a dedicated **/symptoms.html** page for symptom intake
  + follow-up chat, and a dedicated **/report.html** page for PDF analysis.
- **Symptom analysis** — enter symptoms, age, gender, medical history, language;
  get a structured AI breakdown (Summary, Possible Causes, Severity, Suggested
  Doctor, Suggested Tests, Lifestyle Suggestions, Disclaimer).
- **ChatGPT-style follow-up chat** — every analysis and follow-up answer is
  appended to the conversation; previous results stay visible until you click
  **New chat**.
- **PDF medical-report analysis** — upload a lab/test report (PDF) and get a
  parameter-by-parameter table (Value · Normal Range · Status · What It Means),
  abnormal findings, the right specialist for each, follow-up tests, and a
  tailored **Eat / Avoid** lifestyle plan.
- **Scanned PDF support** — if the PDF has no text layer, pages are rendered
  to images and read by Gemini Vision automatically. No Tesseract / Poppler.
- **Multilingual** — English, Hindi, Hinglish.
- **Safe demo fallback** — if no AI key is configured (or the AI is rate-limited),
  a rule-based responder still returns safe educational guidance.
- **SEO-ready** — meta + Open Graph tags, JSON-LD `WebApplication` schema,
  `sitemap.xml`, `robots.txt`, custom favicon and OG image.

---

## 🧱 Tech Stack

- **Backend:** Python 3.10+, Flask, Flask-CORS, requests, python-dotenv,
  `pypdf` (text extraction), `pymupdf` (PDF-to-image for vision)
- **AI provider:** Google Gemini via OpenAI-compatible endpoint
  (`gemini-2.5-flash` by default — supports text + vision)
- **Frontend:** Static HTML / CSS / vanilla JS (no build step),
  `marked.js`, `DOMPurify`, Google Fonts (Inter + Space Grotesk),
  Medical Sky light theme (sky-blue / cyan palette on white)
- **Deployment:** Render (Procfile + render.yaml), gunicorn

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
│  ├─ index.html          # Landing page (hero + features)
│  ├─ symptoms.html       # Intake form + ChatGPT-style follow-up chat
│  ├─ report.html         # PDF upload + analysis
│  ├─ styles.css          # Medical Sky theme
│  ├─ favicon.svg
│  ├─ og-image.svg
│  ├─ sitemap.xml
│  ├─ robots.txt
│  └─ js/
│     ├─ home.js          # Health badge on the landing page
│     ├─ app.js           # Symptom analysis + follow-up chat
│     └─ report.js        # PDF upload flow
├─ Procfile               # Render / Heroku-style start command
├─ render.yaml            # Render blueprint (one-click deploy)
├─ runtime.txt            # Pinned Python version
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
read **"Live AI"**. If it says "Demo mode", your key is not being read.

The site has three pages:

| Path | Purpose |
|---|---|
| `/` | Landing page (hero + features) |
| `/symptoms.html` | Symptom intake form + follow-up chat |
| `/report.html` | PDF report upload + analysis |

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

### Deploy to Render (one-click)

This repo ships with `render.yaml`, `Procfile`, and `runtime.txt` for
zero-config deployment:

1. Push the repo to GitHub.
2. On https://render.com → **New +** → **Blueprint** → connect the repo.
3. Set `AI_API_KEY` in the environment variables.
4. Deploy — Render reads `render.yaml` and builds the service.

> ⚠️ Free tier instances sleep after 15 min of inactivity. Use a free uptime
> pinger (e.g. UptimeRobot) on `/api/health` if you need always-on availability.

---

## 📜 License

For educational and personal use. Not certified for clinical decision-making.
