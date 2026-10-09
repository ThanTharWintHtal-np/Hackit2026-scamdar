# Explainable scoring

ScamDar uses deterministic rules first. It does not use an LLM or classifier as the source of its numeric score. The API returns every triggered signal and its contribution so a person can challenge the result.

## Current signal weights

| Signal | Points | Example evidence |
| --- | ---: | --- |
| Urgency or threat language | 12 | “today”, “detained”, “immediately” |
| Credential or account access request | 30 | OTP, password, PIN, Singpass |
| Payment or financial request | 22 | Pay, fee, transfer, card details |
| Delivery-service impersonation | 18 | Parcel/delivery wording plus delivery brand cues |
| Possible organisation impersonation | 10 | Named bank, service, or public agency |
| Suspicious or reserved domain ending | 22 | `.test`, `.zip`, `.click`, and selected high-risk endings |
| Shortened destination URL | 18 | Known URL shorteners |
| Non-HTTPS link | 8 | Link is not encrypted; this alone is not proof of fraud |
| Similar community campaign | 8 or 12 | At least 5 reports with 35%+ word/character trigram similarity; higher bump for 15+ matches |

Points add, then cap at 100. A High level starts at 65; Critical starts at 95; Medium starts at 35. The demo example reaches 92 when its similar-campaign signal is present. Without community matches, its technical text/link signals still produce High risk.

## Interpretation

- The score is a **warning priority**, not a probability or legal finding.
- Community confidence is calculated separately as the share of votes marked “Scam.” It is not added into that vote percentage.
- A match count can influence the technical score only through a small, visible repeated-campaign signal. This can amplify a false report, so reports are flagged and moderation exists.
- A message with no matched rule can still be a scam. “Low” means no strong configured signal was found, not safe.
- Similarity uses word + character trigram cosine similarity, not semantic embeddings. A future evaluated embedding model could improve recall but must not erase explanations.

## Calibration work still needed

Rules and thresholds are prototype heuristics. Before public launch, collect consented and reviewed examples, measure false positives/negatives by category and language, get security/community review, and decide governance for score changes. Never tune only to maximize a hackathon demo score.
