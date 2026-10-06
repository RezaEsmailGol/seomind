# SeoMind

**Local-first AI SEO intelligence for Google Search Console.**

SeoMind is an open-source Python project that connects to Google Search Console, analyzes search performance locally, detects SEO opportunities with deterministic rules, and optionally uses a local LLM through Ollama to explain findings and recommend actions.

> Goal: go from zero to your first AI-powered Search Console audit through one guided setup flow.

## Why SeoMind?

Most SEO dashboards show charts. SeoMind is designed to answer questions and surface actions:

- Which pages are losing clicks?
- Which queries have high impressions but weak CTR?
- Which pages rank between positions 4–20 and have realistic growth potential?
- Are multiple pages competing for the same query?
- Which URLs should be inspected first?
- What changed between the current and previous period?
- Why did organic traffic drop?

## Core principles

- **Local-first** — your SEO data can stay on your machine.
- **Deterministic analysis first** — opportunity detection is testable and not dependent on an LLM.
- **AI as an explanation layer** — use Ollama locally, or optionally connect another provider later.
- **Simple installation** — Windows, Linux and macOS setup scripts.
- **Open source** — transparent code and extensible architecture.

## Planned stack

- Python 3.11+
- FastAPI
- Google Search Console API
- OAuth 2.0
- SQLite
- Pandas / Polars
- Ollama
- React / Next.js dashboard
- Docker
- MCP server (planned)

## Current status

**Early development / v0.1 bootstrap**

The current repository contains the installable Python/FastAPI foundation. Google OAuth, Search Console import, the Opportunity Engine and the graphical setup wizard are the next milestones.

## Quick start

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
chmod +x setup.sh
./setup.sh
```

Then open:

```text
http://127.0.0.1:8787
```

Health check:

```text
http://127.0.0.1:8787/health
```

API docs:

```text
http://127.0.0.1:8787/docs
```

## Planned setup wizard

SeoMind will guide users through:

1. Environment check
2. Google Cloud / Search Console credentials
3. Google OAuth connection
4. Search Console property selection
5. AI engine selection
6. First data import and audit

## Roadmap

### v0.1 — Foundation
- [x] Public repository
- [x] Python project structure
- [x] FastAPI bootstrap
- [x] Windows setup script
- [x] Linux/macOS setup script
- [x] Local health/status endpoints
- [ ] Setup wizard UI

### v0.2 — Google Search Console
- [ ] Google OAuth 2.0
- [ ] Property listing
- [ ] Search Analytics import
- [ ] Date/device/country/query/page dimensions
- [ ] Local data storage

### v0.3 — Opportunity Engine
- [ ] High-impression / low-CTR detector
- [ ] Position 4–20 opportunity detector
- [ ] Click/impression decay detector
- [ ] Cannibalization detector
- [ ] Period comparison
- [ ] Opportunity scoring

### v0.4 — Local AI
- [ ] Ollama detection
- [ ] Guided model installation
- [ ] Local explanation layer
- [ ] Ask-your-SEO-data chat

### v0.5 — Technical SEO
- [ ] URL Inspection integration
- [ ] Sitemap reader
- [ ] Local crawler
- [ ] Title / description / H1 / canonical / robots analysis

### Later
- [ ] MCP server
- [ ] Docker one-command install
- [ ] Windows installer
- [ ] Export to CSV / Markdown / PDF
- [ ] Multi-property workspaces

## Architecture

```text
seomind/
├── src/seomind/
│   ├── main.py
│   ├── config.py
│   ├── api/
│   ├── gsc/
│   ├── analyzer/
│   ├── ai/
│   └── storage/
├── tests/
├── setup.bat
├── setup.sh
├── pyproject.toml
└── .env.example
```

## Privacy

SeoMind is designed so that Google credentials, Search Console exports and local AI prompts do not need to leave the user's computer.

Never commit Google OAuth secrets or generated tokens to Git.

## فارسی

**SeoMind** یک ابزار متن‌باز و Local-first برای تحلیل Google Search Console با Python و AI است.

هدف پروژه این است که کاربر بدون درگیرشدن با تنظیمات پیچیده، مرحله‌به‌مرحله Search Console را متصل کند، داده‌ها را روی سیستم خودش تحلیل کند و فرصت‌های واقعی سئو را ببیند. هسته تحلیل وابسته به هوش مصنوعی نخواهد بود؛ AI برای توضیح بهتر یافته‌ها و پیشنهاد اقدام استفاده می‌شود.

## Author

**Mohammad Reza Esmail Gol**

- GitHub: https://github.com/RezaEsmailGol
- Portfolio: https://rezagol.ir

## License

MIT
