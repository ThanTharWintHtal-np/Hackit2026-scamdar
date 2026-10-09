"""Transparent scam indicators and lightweight word/character similarity."""

from __future__ import annotations

import math
import re
from collections import Counter
from urllib.parse import urlparse

URGENCY = ("today", "now", "immediately", "urgent", "within 24 hours", "final notice", "act fast", "last chance", "detained", "suspended", "blocked", "expire")
PAYMENT = ("pay", "payment", "fee", "transfer", "deposit", "refund", "bank account", "credit card", "paynow", "wallet", "$", "s$", "crypto")
CREDENTIALS = ("password", "otp", "one-time password", "pin", "login", "verification code", "card details", "singpass")
DELIVERY = ("parcel", "delivery", "singpost", "ninjavan", "speedpost", "customs", "detained", "redelivery")
BRANDS = ("singpost", "dbs", "ocbc", "uob", "paynow", "iras", "cpf", "singpass", "police", "gov.sg", "telegram")
RISKY_TLDS = {"test", "zip", "mov", "click", "top", "xyz", "icu", "work"}
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "cutt.ly", "rb.gy"}
OFFICIAL_DOMAINS = {
    "singpost.com", "singpost.com.sg", "dbs.com", "dbs.com.sg", "ocbc.com", "ocbc.com.sg",
    "uob.com.sg", "iras.gov.sg", "cpf.gov.sg", "singpass.gov.sg", "gov.sg", "paynow.gov.sg",
}


def _signal(code: str, label: str, points: int, detail: str) -> dict:
    return {"code": code, "label": label, "points": points, "detail": detail}


def _domain_signals(text: str) -> list[dict]:
    urls = re.findall(r"(?:https?://|www\.)[^\s<>\]\[()]+", text, flags=re.I)
    found = []
    for raw in urls:
        cleaned = raw.rstrip(".,!?;:)")
        parsed = urlparse(cleaned if "://" in cleaned else "https://" + cleaned)
        host = (parsed.hostname or "").lower().strip(".")
        if not host:
            continue
        parts = host.split(".")
        tld = parts[-1] if parts else ""
        if tld in RISKY_TLDS or host.endswith(".test"):
            found.append(_signal("suspicious_domain", "Suspicious domain", 22, f"{host} uses a high-risk or reserved domain ending."))
            break
        if host in SHORTENERS:
            found.append(_signal("shortened_url", "Shortened link", 18, f"{host} hides the final destination."))
            break
        if any(host == domain or host.endswith("." + domain) for domain in OFFICIAL_DOMAINS):
            continue
        if parsed.scheme != "https":
            found.append(_signal("no_https", "Link does not use HTTPS", 8, "The link is not encrypted; verify the destination independently."))
            break
        brand_match = next((b for b in BRANDS if b.replace(".", "") in host.replace(".", "") and not (host == b or host.endswith("." + b))), None)
        if brand_match:
            found.append(_signal("brand_like_domain", "Brand-like domain", 18, f"The address contains {brand_match} but is not its exact official domain."))
            break
    return found


def analyze_text(text: str, community_matches: int = 0) -> dict:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    signals: list[dict] = []
    if any(phrase in normalized for phrase in URGENCY):
        signals.append(_signal("urgency", "Urgency or threat language", 12, "It pressures the reader to act quickly or suggests a loss of service."))
    if any(phrase in normalized for phrase in CREDENTIALS):
        signals.append(_signal("credentials", "Credential or account access request", 30, "Never share passwords, OTPs, PINs, or Singpass details through a message link."))
    if any(phrase in normalized for phrase in PAYMENT):
        signals.append(_signal("payment", "Payment or financial request", 22, "The message asks for money, payment details, or a transfer."))
    if any(phrase in normalized for phrase in DELIVERY) and any(brand in normalized for brand in ("singpost", "ninjavan", "speedpost", "parcel", "delivery")):
        signals.append(_signal("delivery_impersonation", "Delivery-service impersonation", 18, "It refers to a parcel or delivery issue commonly used in impersonation scams."))
    if any(brand in normalized for brand in BRANDS):
        signals.append(_signal("brand_impersonation", "Possible organisation impersonation", 10, "A bank, service, or government organisation is named. Check through its official app or website."))
    signals.extend(_domain_signals(text))
    if community_matches >= 5:
        points = 8 if community_matches < 15 else 12
        signals.append(_signal("campaign_activity", "Similar community reports", points, f"{community_matches} related community reports suggest a repeated campaign. Community reports are evidence, not proof."))
    score = min(100, sum(s["points"] for s in signals))
    level = "Critical" if score >= 95 else "High" if score >= 65 else "Medium" if score >= 35 else "Low"
    category = "delivery" if any(s["code"] == "delivery_impersonation" for s in signals) else "banking" if any(b in normalized for b in ("dbs", "ocbc", "uob", "bank")) else "government" if any(b in normalized for b in ("iras", "cpf", "singpass", "police")) else "phishing" if any(s["code"] in {"credentials", "suspicious_domain", "brand_like_domain"} for s in signals) else "other"
    action = "High scam likelihood. Do not send money or disclose credentials until independently verified." if score >= 65 else "Pause and verify the sender through an official channel before taking action." if score >= 35 else "No strong scam indicators were found. Still verify unexpected requests independently."
    return {"score": score, "level": level, "category": category, "signals": signals, "recommended_action": action, "disclaimer": "This is an evidence-based warning aid, not a guarantee that a message is safe or fraudulent."}


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    tokens = ["w:" + word for word in words]
    compact = " ".join(words)
    tokens.extend("c:" + compact[i:i + 3] for i in range(max(0, len(compact) - 2)))
    return tokens


def similarity(left: str, right: str) -> float:
    """Cosine similarity over word and character trigram counts; no external model."""
    a, b = Counter(_tokens(left)), Counter(_tokens(right))
    if not a or not b:
        return 0.0
    dot = sum(value * b.get(key, 0) for key, value in a.items())
    denominator = math.sqrt(sum(v * v for v in a.values()) * sum(v * v for v in b.values()))
    return round(dot / denominator, 4) if denominator else 0.0
