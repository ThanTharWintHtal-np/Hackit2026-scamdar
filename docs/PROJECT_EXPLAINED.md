# ScamDar explained for a student developer

This guide assumes you know HTML, CSS, JavaScript, Python, and basic MSSQL, and are newer to React, Vite, Tailwind, FastAPI, PostgreSQL, embeddings, and PWAs.

## 1. The main technologies

### React

React builds the browser interface from reusable components. `App.jsx` holds page state and composes the checker, report cards, feed, trends and dialogs. A component receives data through props and updates the screen when state changes. React does not replace HTML or CSS; JSX is JavaScript syntax for describing HTML-like elements.

### Vite

Vite is the frontend development server and build tool. `npm run dev` serves the app with fast reloads. `npm run build` bundles the files in `frontend/dist/` for a static host. It reads `VITE_API_BASE_URL` at build/dev time.

### Tailwind CSS

Tailwind provides utility classes that can be used directly in JSX. This starter includes the Tailwind Vite plugin and import. The visual identity also uses `styles.css` because named CSS rules make the larger responsive layout easier to learn and tune.

### FastAPI and Pydantic

FastAPI maps Python functions to HTTP endpoints and generates `/docs`. Pydantic request classes in `schemas.py` reject malformed or overlong input before route logic runs. For example, a report's region must be one of the allowed broad values.

### SQLAlchemy and PostgreSQL

SQLAlchemy maps Python classes in `models.py` to tables and builds parameterized SQL. This is an ORM (object-relational mapper): code works with `ScamReport` objects, while SQLAlchemy writes database statements safely. SQLite is the no-server local default. PostgreSQL is the intended multi-user database when `DATABASE_URL` is changed.

#### PostgreSQL compared with MSSQL

Both are relational databases. Tables, rows, primary keys, foreign keys, indexes, transactions, and constraints work similarly. PostgreSQL's driver and connection string differ: this app uses `psycopg` and a URL such as `postgresql+psycopg://user:password@host:5432/database`. MSSQL commonly uses Microsoft SQL Server's T-SQL dialect, `IDENTITY` columns, and drivers such as `pyodbc`; PostgreSQL uses its own SQL dialect and identity/serial options. SQLAlchemy hides many routine differences, but migrations, date/time behavior, JSON types, text search, and database-specific SQL still need checking. The prototype does not use MSSQL-specific syntax.

## 2. Frontend → backend → database

1. A user enters a message in the React form.
2. `frontend/src/api.js` sends `POST /api/analyze` as JSON using `fetch`.
3. FastAPI validates it as `AnalyzeIn` and calls `analyze_text`.
4. Similar reports are loaded using SQLAlchemy. Text similarity ranks them.
5. The API responds with score, level, signals, action, and matches as JSON.
6. React renders each response field as text. It does not treat user text as HTML.

When a signed-in user reports something, their browser adds a bearer token to the Authorization header. FastAPI verifies the signature and finds the account; SQLAlchemy stores the report. The database unique constraint on `(user_id, report_id)` prevents duplicate votes by one user.

## 3. Scoring engine

`backend/app/scoring.py` searches for named patterns: urgency, money, credentials, delivery wording, organization names, and risky URL patterns. Each matched rule returns a `code`, readable `label`, `points`, and explanation. Points sum to a maximum of 100. The level is Low, Medium, High, or Critical. The result includes careful next-step wording.

This is not a probability. The score does not say “92% chance.” It says the configured rules found enough warning signals to recommend a pause and independent verification. Rules can miss new tactics and can flag legitimate content. That limitation is explicit in the UI and docs.

## 4. Similarity matching (without fake AI)

The current method is cosine similarity over word tokens and character trigrams. For example, a phrase is represented by counts such as `w:parcel`, `w:delivery`, and `c:par`, `c:arc`, `c:rce`. Cosine compares two sparse vectors; it returns a value from zero to one. Character fragments can tolerate small edits. It is not a semantic embedding and cannot reliably understand paraphrases. The API converts the similarity to a percentage for the UI.

An embedding model would map meaning to a dense numeric vector, then compare vector direction. ScamDar does not claim to do that today. A future embedding model should be evaluated against labeled examples, versioned, and presented alongside interpretable evidence.

## 5. Authentication and authorization

Signup stores an email, display name, role, and salted PBKDF2 password hash. Login returns a signed, expiring bearer token. Requests include `Authorization: Bearer ...`. Roles are `user`, `trusted_contributor`, `moderator`, and `admin`. The database role is checked for moderator/admin work. Public checking is anonymous; reporting, voting, commenting, flagging, and asking a trusted contact require login.

This demo token is stateless. Browser logout deletes the local token; it cannot revoke a stolen token until expiry. Use a persistent random `AUTH_SECRET` outside source control. A production web app should consider HttpOnly same-site cookies and revocation.

## 6. Voting and comments

The three vote choices are “Scam,” “Not sure,” and “Likely legitimate.” One user can have one vote per report and can change it. The community-confidence percentage is the share of votes that say Scam. It remains separate from the technical risk score. Comments are plain text, may have a parent reply ID in the API, and can be hidden by moderators. Report owners receive an in-app notification when someone comments.

## 7. Moderation

Members can flag a report or comment with a reason. Moderators see open flags and can dismiss, hide, verify, or lock a report; hiding a comment is supported. A moderator action records who acted, what changed, and the target in `audit_logs`. A complete visual admin console is not yet built; the admin and moderation workflows are available through API endpoints and FastAPI `/docs`.

## 8. Notifications and trusted contacts

The prototype stores in-app notification records for replies and trusted-contact responses. A trusted-contact request creates a random response token that expires after seven days. The user shares the private link manually; the demo does not send an email. A response can be “Do not proceed,” “Looks safe,” or “I am unsure.” Real-time delivery, reminders, email, and link revocation should be added before public use.

## 9. Privacy and uploads

The checker analyzes text without saving it. If the user chooses to report it, the report becomes community-visible. The region list contains only Singapore-wide, Central, East, North, Northeast, and West. There is no location coordinate field. Screenshot uploads are type-checked and size-limited, held in memory, and not written to disk. OCR requires Pillow, pytesseract, and the Tesseract operating-system binary; it is off by default.

## 10. PWA

A Progressive Web App can be installed from a compatible browser. The manifest provides the app name, icon, colors, and display mode. The service worker caches the static shell so the app frame can open offline. It does not cache API responses or permit votes/checks offline; those actions need the server.

## 11. Deployment

Build the client using `npm run build`; host `frontend/dist` on a static hosting service. Run FastAPI using an ASGI server such as Uvicorn behind HTTPS. Set a production PostgreSQL URL, strong `AUTH_SECRET`, exact CORS origins, and `APP_ENV=production`. Configure database backups, security monitoring, OCR packages, email delivery, abuse handling, and privacy/retention policy separately. This repository does not configure cloud hosting.

## 12. Current limitations

Weights are hand-set heuristics; lexical similarity is not semantic; OCR and email are optional/incomplete integrations; the map is broad and illustrative; demo seed data is fictional; the rate limiter is single-process; multilingual JSON files are starter strings; the interface includes basic large-text mode but not full elder-oriented content review or speech; and there is no full admin UI. These limits should be stated in the pitch.

## 13. Likely mentor questions and suggested answers

**Why not rely on AI?**  
“We need the user to see why a warning appeared. Deterministic signals are auditable and work without an API key. Similarity helps connect repeated reports, but it is not presented as semantic AI.”

**Does 92 mean 92% likely to be a scam?**  
“No. It is a rule-based warning score, not a calibrated probability. We explain each point and recommend independently verifying the sender.”

**Can community votes make a legitimate message look fraudulent?**  
“They could be manipulated. We show that confidence separately, limit one vote per account, allow flags and moderator actions, and still need stronger account-abuse controls before launch.”

**Why not show a map pin?**  
“Exact victim locations could expose people. Broad regions can show community patterns while avoiding home addresses.”

**How would you improve matching?**  
“Evaluate lexical matching on reviewed examples first. Then compare a multilingual embedding model against it for recall and false matches, while keeping the final reasons visible.”

**What is ready for production?**  
“The project is a working student prototype. Production still needs calibrated data, persistent secrets, scaled rate limiting, a reviewed moderation policy, email recovery, monitoring, retention rules, and OCR deployment validation.”
