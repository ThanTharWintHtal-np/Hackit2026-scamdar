# Security and privacy notes

## Implemented safeguards

- SQLAlchemy binds query values; no SQL strings are assembled from user input.
- Pydantic constrains message, name, URL, phone, comment, region, category, and vote fields.
- Plain text is stored and React renders it as text. Do not render community content with `dangerouslySetInnerHTML`.
- Passwords use PBKDF2-HMAC-SHA256 with a random 16-byte salt and 310,000 iterations.
- Signed bearer tokens expire. With no configured `AUTH_SECRET`, the demo generates a process-local key and all sessions expire on restart. Production startup requires an explicit 32+ character secret.
- Important API routes have a simple per-IP, per-route in-memory rate limiter; auth is required for contributions and moderation. One vote per user/report is enforced by a database unique constraint.
- CORS allows only configured origins. Security response headers are set. Bearer tokens are sent in an Authorization header; cookie auth is not used, so browser CSRF is not the current token transport risk.
- Screenshot uploads are size-limited, MIME-allowlisted, checked against file signatures, held in memory, and never saved with a user-controlled filename.
- Region input is an enum-like broad value. Precise locations are neither required nor stored.
- Moderator changes create audit records. Moderators can hide, verify, lock, or dismiss flagged content.
- `.env` and local databases are ignored; only `.env.example` is included.

## Limits before production

- In-memory throttling resets on restart and does not coordinate multiple server workers. Use a shared rate-limit store at scale.
- Tokens are stateless. Logout removes the token from the current browser but does not revoke a stolen token early; use short expiry and add revocation/session storage before launch.
- The example stores the token in localStorage. A production web client should add a strict CSP and consider a same-site HttpOnly cookie plus CSRF defenses.
- No password reset/email provider, email verification, MFA, automated alert sending, malware scanning, or external domain reputation integration is configured.
- OCR depends on a system Tesseract installation. Keep image processing isolated and resource-limited in a real deployment.
- Moderation, duplicate merging, helpful marking, notifications, and trusted-contact link distribution need further abuse and privacy review before use with real users.
- Seed reports are synthetic; trend totals are for demonstration and must never be represented as current Singapore scam statistics.

## Deployment checklist

Use HTTPS; set `APP_ENV=production`, a random `AUTH_SECRET` (32+ characters), and exact `FRONTEND_ORIGINS`; use managed PostgreSQL with least-privilege credentials; enable backups and monitoring; keep secrets out of browser code and logs; set upload limits; establish a moderation escalation path; and publish a clear data retention and deletion policy.
