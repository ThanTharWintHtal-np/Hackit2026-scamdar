# ScamDar contributor guide

ScamDar turns every scam encounter into protection for the next person.

## Working rules

- Keep the checker explainable: every score point must come from a named signal.
- Keep technical risk and community opinion as separate values.
- Only store broad Singapore regions; never ask for a victim's precise location.
- Treat user submitted text, links, images, and comments as untrusted input.
- Never commit `.env`, passwords, tokens, real victim data, or API keys.
- Use synthetic data for development and demos.
- Prefer a small, understandable change and run the related checks.

## Project map

- `frontend/`: React, Vite, Tailwind and PWA client.
- `backend/`: FastAPI, Pydantic, SQLAlchemy API.
- `ml/`: optional similarity and classifier experiments; production scoring stays deterministic.
- `docs/`: architecture, scoring, security, demo, mentorship and learning notes.

## Local checks

- Backend: `cd backend && python -m unittest discover -s tests` and `uvicorn app.main:app --reload`.
- Frontend: `cd frontend && npm install && npm run build`.
- Seed synthetic reports: `cd backend && python -m app.seed`.
