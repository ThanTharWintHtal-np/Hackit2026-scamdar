# Demo runbook

## 3-minute demo

1. **Set the problem (20 sec):** “A suspicious delivery message can reach anyone. ScamDar lets one person’s encounter warn the next person.”
2. **Check anonymously (45 sec):** paste the exact SingPost message from the README and click **Check for scam**. Point to the separate score and the urgency, payment, delivery, organisation, domain, and campaign signals.
3. **Show evidence (35 sec):** open a similar synthetic report; explain its match percentage, broad region, technical score, community votes, and discussion. Emphasize that community confidence is separate.
4. **Join the community (45 sec):** create an account; submit a report; show duplicate review; vote and post a comment.
5. **Share and zoom out (35 sec):** use WhatsApp share; open Trends and Regional map. Explain that map intensity is region-aggregated, never a home-location pin.

For moderation, promote a demo account using `python -m app.manage promote email moderator`, sign in again, then exercise the moderation API at `/docs` or use the API tests. Admin tools are API endpoints; a full admin UI is not part of this prototype.

## Exact demo input

```text
Your SingPost parcel has been detained. Pay $2.03 today to arrange delivery at http://example-suspicious-link.test
```

Expected on a seeded database: **High risk — 92/100**, with visible urgency, payment, delivery impersonation, organisation impersonation, suspicious domain, and similar campaign evidence. Similar report counts may vary if the seed data or user reports have changed.

## Recovery notes

- If the checker says the API is disconnected, start Uvicorn from the `backend/` directory and confirm `http://localhost:8000/api/health`.
- If reports are missing, run `python -m app.seed` from `backend/`.
- If browser CORS blocks a request, set root `.env` `FRONTEND_ORIGINS=http://localhost:5173` and restart the backend.
- If login sessions invalidate after restarting in local demo, set a persistent `AUTH_SECRET` in `.env`.
- OCR may return a clear “disabled” message unless Tesseract is installed and enabled. Use paste-text for the core demo.
