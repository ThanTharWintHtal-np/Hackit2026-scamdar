# ScamDar

**ScamDar turns every scam encounter into protection for the next person.**

> Waze crowdsources road danger. ScamDar crowdsources digital danger.

ScamDar is a Singapore community scam-awareness prototype for the HackIT 2026 problem **Reducing Scam Harm through Shared Community Awareness**. It helps people check an unexpected message, understand visible warning signs, compare it with synthetic or community reports, and share a caution with someone else.

The checker is public. Signing in is needed for reports, community votes, comments, flags, and trusted-contact requests. The technical risk estimate is always shown separately from community opinion. ScamDar is not a bank, government service, or guarantee that a message is safe.

## Run locally

Prerequisites: Python 3.11+, Node.js 20+, and (for the PostgreSQL path) PostgreSQL 15+.

```bash
cp .env.example .env
# Edit .env and set AUTH_SECRET to a random value of at least 32 characters.
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open <http://localhost:5173>. FastAPI docs are at <http://localhost:8000/docs>. The default local database is SQLite so the prototype starts without a database server. To use PostgreSQL, change `DATABASE_URL` in the root `.env` to `postgresql+psycopg://scamdar:YOUR_PASSWORD@localhost:5432/scamdar` and create that database/user first. Never put a production secret in the frontend `.env`.

## Main demo

Use the “Try the demo message” shortcut, then check:

> Your SingPost parcel has been detained. Pay $2.03 today to arrange delivery at http://example-suspicious-link.test

The expected result is **High risk — 92/100** when related community reports are available. The result lists delivery impersonation, urgency, payment, organisation impersonation, suspicious domain, and repeated campaign activity separately. Open a similar report to see its community votes, broad region, discussion, and share action.

## What is implemented

- Explainable deterministic scorer, visible point contributions, recommended next steps, and cautious wording.
- Word and character trigram cosine similarity; this is a transparent text-matching method, not an embedding model or “AI detector.”
- 62 fictional reports spanning delivery, banks, government, job/task, investment, marketplace, refund, tech-support, and phishing examples.
- Public checker and feed; signup/login; report creation with duplicate review; one vote per account/report; comments/replies API; reporting/flags; moderator resolution; broad region trends; WhatsApp share links; trusted-contact response links; in-app notification records; admin summary/role endpoints.
- Screenshot MIME and size validation. OCR runs only when `OCR_ENABLED=true`, Python OCR dependencies are installed, and the host has the Tesseract binary.
- Installable PWA shell and an offline shell fallback. API actions need a connection.
- Locale resource files for English, Chinese, Malay, and Tamil. The current interface is primarily English; translations are starter strings, not a complete reviewed translation.

## Checks

```bash
cd backend && python -m unittest discover -s tests -v
cd backend && pytest -q
cd frontend && npm test && npm run build
```

The API tests use an in-memory SQLite database. Startup seeds 60 synthetic reports into the configured local database if they are not already present. To bootstrap a moderator locally, create an account, then run from `backend/`: `python -m app.manage promote you@example.com moderator`. Promote only people who should moderate.

## Repository map

```text
frontend/        React + Vite + Tailwind UI and PWA shell
backend/         FastAPI + Pydantic + SQLAlchemy API and tests
ml/              Similarity/classifier experiment notes
docs/            Architecture, safety, scoring, demo, mentorship, learning guide
scripts/         Local setup and verification helpers
```

## Hackathon context

- Mentorship: **9 October 2026, 4:00–4:20 PM Singapore Time**.
- Final deadline: **21 October 2026, 12:00 AM Singapore Time**.
- Judging: Innovation & Creativity 25%; Technical Implementation 25%; Problem-Solution Fit & Value 20%; Presentation 20%; Usability 10%.

See [the demo runbook](docs/DEMO.md), [mentorship notes](docs/MENTORSHIP.md), and [student project guide](docs/PROJECT_EXPLAINED.md).
