# ScamDar ML experiments

The current application intentionally does not claim an AI classifier. Its report retrieval method is implemented in `backend/app/scoring.py` as cosine similarity over word and character trigram counts.

Future experiments should:

1. Use a consented, anonymized, human-reviewed dataset with source and date metadata.
2. Keep a clean train/validation/test split by campaign so near-duplicate messages do not leak across splits.
3. Compare the current lexical baseline with multilingual sentence embeddings and a small classifier.
4. Report precision, recall, calibration, false-positive rates by scam type and language, and limitations.
5. Never use a language model as the sole source of a risk score. Explanations must cite concrete message signals and be checked against the message.

No trained weights, private examples, or fabricated model evaluation are included.
