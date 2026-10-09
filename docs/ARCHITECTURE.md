# ScamDar architecture

## Components

- **React + Vite client:** checker, report feed/detail, voting, discussion, trends, broad-region visual, sign-in, and sharing. Tailwind is available through the Vite plugin; the visual system also uses a small hand-written stylesheet.
- **FastAPI:** typed HTTP routes, request validation with Pydantic, session bearer-token checks, rate limiting, upload validation, and CORS.
- **SQLAlchemy:** parameterized database operations and table mapping. The local default is SQLite; PostgreSQL is supported with psycopg.
- **Similarity:** normalized word and character trigram counts compared with cosine similarity. This is an interpretable lexical matching baseline; it does not understand meaning like a transformer model.
- **Scoring:** deterministic signal rules. The API returns signals, points, level, category, action guidance, and similar reports.

## Request flow

1. The browser sends JSON to `/api/analyze`; no account is required.
2. FastAPI validates length and shape, then compares the message with up to 250 active/verified reports.
3. The scorer computes signal contributions. Closely matching community activity can add a capped campaign signal.
4. The response includes technical score and community matches. Aggregate votes are only shown as a distinct community-confidence value.
5. If the user chooses to report, sign-in is required. The API checks for likely duplicates and returns candidates before a new campaign report is created.
6. Votes, comments, flags, moderation actions, and trusted-contact responses are stored using SQLAlchemy. Moderator actions add an audit record.

## Data model

`User`, `ScamReport`, `Vote`, `Comment`, `Flag`, `TrustedContact`, `Notification`, and `AuditLog` are the core tables. The report stores a broad region only. There is no victim location coordinate, postal code, or home address column. Seed content is fictional and marked `is_seed`.

## Similarity and campaigns

Each text becomes a sparse count vector of word tokens and character trigrams. Cosine similarity ranks reports. Word terms catch shared phrases; character trigrams can tolerate small spelling or punctuation changes. Matching thresholds are heuristics and need human evaluation before production. `ml/README.md` explains how to experiment without replacing explainable scoring.

## Deployment shape

Serve the built Vite client from a static host and the FastAPI service behind HTTPS. Set a fixed list of client origins, a persistent random `AUTH_SECRET` (32+ characters), a managed PostgreSQL URL, and production environment flags. Configure backups, monitoring, email delivery, OCR system packages, and abuse response separately. No hosting provider or email service is configured in this source package.
