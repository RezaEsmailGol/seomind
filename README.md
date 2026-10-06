<div align="center">

# 🧠 SeoMind

### Local-first AI SEO intelligence for Google Search Console

**Search Console data → deterministic opportunities → optional local AI explanations**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=flat-square&logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_AI-111827?style=flat-square)](https://ollama.com/)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)

**English** · [فارسی](#فارسی)

</div>

---

## What is SeoMind?

SeoMind is an open-source, local-first SEO application that connects to **Google Search Console**, imports your search-performance data and turns it into a prioritized action queue.

It is deliberately built with two layers:

1. **Deterministic SEO engine** — testable rules detect opportunities and declines.
2. **Optional local AI layer** — Ollama explains findings and suggests actions without making the core detection dependent on an LLM.

Your OAuth file, Google token and imported audit data are stored inside your local `.seomind` directory and are ignored by Git.

## Current features

- ✅ Bilingual interface: **English / فارسی** with RTL support
- ✅ Modern local dashboard with **Lucide icons**
- ✅ Guided setup wizard
- ✅ Google OAuth 2.0 with **read-only Search Console scope**
- ✅ Search Console property discovery and selection
- ✅ 28-day import with previous-period comparison
- ✅ Clicks / Impressions / CTR / Average Position
- ✅ Search-performance trend chart
- ✅ Deterministic Opportunity Engine
  - High impressions + low CTR
  - Ranking “striking distance” (positions 4–20)
  - Click decay vs previous period
  - Possible query cannibalization
- ✅ Local audit persistence in SQLite
- ✅ Google URL Inspection (indexed version)
- ✅ Optional local explanations via Ollama
- ✅ Windows, Linux and macOS setup scripts
- ✅ Docker Compose
- ✅ Backend test suite and GitHub Actions CI

> Search Console APIs can return top rows rather than every possible data row. SeoMind surfaces this limitation instead of pretending the imported dataset is exhaustive.

---

## Screens / flow

```text
Welcome
   ↓
System Check
   ↓
Google OAuth JSON
   ↓
Google Sign-in (read-only Search Console)
   ↓
Choose Property
   ↓
Optional Ollama
   ↓
Dashboard → Import Audit → Opportunity Queue → URL Inspection
```

---

## Quick installation

### Requirements

- Python **3.11+**
- Node.js **20+**
- Git
- A Google account with access to at least one Search Console property
- Optional: Ollama for local AI explanations

### Windows

```bat
git clone https://github.com/RezaEsmailGol/seomind.git
cd seomind
setup.bat
```

### Linux / macOS

```bash
git clone https://github.com/RezaEsmailGol/seomind.git
cd seomind
chmod +x setup.sh run.sh
./setup.sh
```

After installation:

- UI: `http://127.0.0.1:3000`
- API: `http://127.0.0.1:8787`
- API docs: `http://127.0.0.1:8787/docs`

Later launches:

```text
Windows: run.bat
Linux/macOS: ./run.sh
```

---

## Google Search Console setup

SeoMind does **not** ship with anyone's Google credentials. Every user creates their own OAuth client.

1. Open **Google Cloud Console**.
2. Create or select a project.
3. Enable **Google Search Console API**.
4. Configure the OAuth consent screen if Google asks for it.
5. Create an OAuth 2.0 Client ID of type **Web application**.
6. Add this exact Authorized redirect URI:

```text
http://127.0.0.1:8787/api/google/oauth/callback
```

7. Download the OAuth JSON file.
8. Open SeoMind and upload that JSON in the setup wizard.
9. Click **Continue with Google**.

SeoMind requests only:

```text
https://www.googleapis.com/auth/webmasters.readonly
```

That permission allows SeoMind to view Search Console data for sites your account can already access. It does not grant write access.

### OAuth data location

Local secrets are written under:

```text
.seomind/
├── google_client_secret.json
├── google_token.json
└── seomind.db
```

Never commit this directory.

---

## Optional local AI with Ollama

The SEO engine does not need an LLM. Ollama is only used for human-friendly explanations.

Install Ollama, then pull a small model, for example:

```bash
ollama pull qwen3:4b
```

Keep Ollama running on its default address:

```text
http://127.0.0.1:11434
```

SeoMind automatically detects installed models. If the configured model is not installed, it uses the first local model reported by Ollama.

---

## Opportunity Engine

SeoMind intentionally keeps detection separate from AI.

Example deterministic finding:

```text
Query: odoo developer
Page:  https://example.com/odoo
Position: 8.4
Impressions: 4,820
CTR: 1.2%

Finding:
High impressions + page-one visibility + low CTR

Opportunity Score:
87 / 100
```

An LLM can explain this finding, but it does not decide whether the finding exists.

---

## URL Inspection

SeoMind can call Google's URL Inspection API for the selected Search Console property.

It reports Google's indexed-version information such as:

- verdict
- coverage state
- indexing state
- page fetch state
- robots.txt state
- last crawl time

This is **not** a live URL test.

---

## Architecture

```text
seomind/
├── apps/
│   └── web/                 # Next.js + Tailwind + Lucide
│       ├── app/
│       ├── components/
│       └── lib/
│
├── src/seomind/
│   ├── main.py              # FastAPI routes
│   ├── config.py            # Local configuration
│   ├── storage.py           # SQLite + local secrets
│   ├── google_oauth.py      # OAuth 2.0 + token refresh
│   ├── gsc.py               # Search Console + URL Inspection
│   ├── analyzer.py          # Deterministic opportunity engine
│   ├── ollama.py            # Optional local AI
│   └── schemas.py
│
├── tests/
├── setup.bat / setup.sh
├── run.bat / run.sh
├── Dockerfile
└── docker-compose.yml
```

---

## Development

Backend:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
seomind
```

Frontend:

```bash
cd apps/web
cp .env.local.example .env.local
npm install
npm run dev
```

Tests:

```bash
pytest -q
```

---

## Docker

```bash
docker compose up --build
```

Then open `http://127.0.0.1:3000`.

> When the API runs in Docker and Ollama runs on the host, SeoMind uses `host.docker.internal:11434`.

---

## Privacy & security design

- Search Console permission is **read-only**.
- Google OAuth state is validated before token exchange.
- OAuth and token files are stored locally with restricted file permissions where supported.
- Secrets and `.seomind/` are ignored by Git.
- Core SEO detection is local and deterministic.
- Ollama is optional; no cloud LLM is required.
- SeoMind never needs to upload your Search Console dataset to a third-party AI provider.

---

## Roadmap

- [x] Local-first FastAPI backend
- [x] Bilingual Next.js UI
- [x] Google OAuth + property selection
- [x] Search Analytics import
- [x] Opportunity Engine
- [x] SQLite audit persistence
- [x] Ollama explanations
- [x] URL Inspection
- [ ] Sitemap reader + crawler
- [ ] Title / description / H1 / canonical audit
- [ ] Query clustering
- [ ] Export CSV / Markdown / PDF
- [ ] MCP server
- [ ] Signed desktop installer

---

<a id="فارسی"></a>

## 🇮🇷 معرفی فارسی

**SeoMind** یک ابزار متن‌باز برای تحلیل Google Search Console با تمرکز بر **حریم خصوصی، اجرای محلی و هوش مصنوعی اختیاری** است.

هدف این پروژه فقط نمایش نمودار نیست. SeoMind داده Search Console را دریافت می‌کند و با یک موتور تحلیلی قابل‌تست، مواردی مثل این‌ها را پیدا می‌کند:

- صفحات یا Queryهای دارای ایمپرشن بالا و CTR پایین
- رتبه‌های ۴ تا ۲۰ که شانس رشد دارند
- افت کلیک نسبت به دوره قبل
- رقابت احتمالی چند صفحه روی یک Query
- وضعیت URL در نسخه موجود در ایندکس گوگل

سپس اگر **Ollama** روی سیستم فعال باشد، AI محلی می‌تواند دلیل و اقدام‌های پیشنهادی را به فارسی یا انگلیسی توضیح دهد. اصل تشخیص فرصت‌ها وابسته به AI نیست.

### نصب در ویندوز

```bat
git clone https://github.com/RezaEsmailGol/seomind.git
cd seomind
setup.bat
```

پس از نصب، مرورگر را روی این آدرس باز کنید:

```text
http://127.0.0.1:3000
```

رابط برنامه از داخل خود SeoMind بین **فارسی و انگلیسی** تغییر می‌کند و در حالت فارسی RTL است.

### اتصال گوگل

در Google Cloud یک OAuth Client از نوع **Web application** بسازید و Redirect URI زیر را ثبت کنید:

```text
http://127.0.0.1:8787/api/google/oauth/callback
```

فایل JSON را دانلود و در Wizard برنامه انتخاب کنید. دسترسی درخواستی فقط خواندنی است.

---

## Author

**Mohammad Reza Esmail Gol**

- GitHub: https://github.com/RezaEsmailGol
- Portfolio: https://rezagol.ir

## License

MIT
