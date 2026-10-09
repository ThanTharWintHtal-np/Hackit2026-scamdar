# HackIT 2026 mentorship briefing

**Organisation mentorship: 9 October 2026, 4:00–4:20 PM Singapore Time**  
**Final deadline: 21 October 2026, 12:00 AM Singapore Time**

## Two-minute problem explanation

People often receive suspicious messages alone and under pressure. One person may recognize a fake parcel fee, bank login page, job task, or government impersonation, but their experience does not automatically help the next person. Existing warnings can be hard to find and do not always explain why a message looks risky.

ScamDar is a community scam-awareness platform inspired by traffic reporting tools. Anyone can paste a suspicious message and receive a visible risk assessment. Signals include urgency, requests for payment or credentials, organisation impersonation, suspicious domains, and similar community reports. The user sees the reasons and recommended action instead of an unexplained AI score. With an account, they can add a report, vote, comment, flag misinformation, and share a WhatsApp-friendly warning. A regional view uses only broad areas, never precise victim locations.

ScamDar cannot prove that a message is fraudulent or safe. It helps people pause, compare evidence, and verify through official channels. Community votes remain separate from the technical score so popularity does not masquerade as evidence.

## Three-minute demo

Use the steps in [DEMO.md](DEMO.md): anonymous check → explain the 92/100 result → open related reports → show community discussion and confidence → report/vote/comment → share → trends and broad regions.

## Architecture summary

React/Vite renders the responsive frontend. FastAPI validates requests and runs deterministic scoring plus word/character trigram cosine similarity. SQLAlchemy stores users, reports, votes, comments, flags, trusted-contact requests, notifications, and audit records in local SQLite or PostgreSQL. The PWA caches its static shell; API workflows remain online-only.

## Key design decisions

- A rule-based score with point contributions is easier to audit than an unexplained black-box score.
- Similarity is a transparent lexical baseline; there is no claim of semantic AI.
- Community confidence stays distinct from technical risk.
- Broad region aggregation supports awareness while limiting location exposure.
- Anonymous checking lowers friction; login gates actions that can change community data.
- Duplicate review is offered before publishing another report about the same campaign.
- Synthetic seed data demonstrates workflows without exposing victims.

## Limitations to say clearly

- The weights are prototype heuristics, not calibrated probabilities.
- Word and character similarity can miss paraphrases and match unrelated short text.
- OCR requires a Tesseract host installation; email sending, password recovery, and live alerts are not configured.
- Trends are synthetic/demo values until real, moderated reports exist.
- Full multilingual translation and a complete moderator interface remain future work.
- Rate limiting is in-memory and not suitable for a multi-worker public service.

## Questions for the NCS mentor

1. What is the biggest weakness in this concept?
2. Should community evidence influence the risk score or remain separate?
3. Is our explainable scoring approach understandable enough?
4. Is regional trending valuable?
5. What misinformation risks should we prioritize?
6. Would WhatsApp sharing improve adoption?
7. What should we simplify for elderly users?
8. If you were judging this, what would stop it from winning?

## Judging focus

The demo should show concrete user value and a working end-to-end path. Explain the technical choices simply, then acknowledge the limits. The judging weights are Innovation & Creativity 25%, Technical Implementation 25%, Problem-Solution Fit & Value 20%, Presentation 20%, and Usability 10%.
