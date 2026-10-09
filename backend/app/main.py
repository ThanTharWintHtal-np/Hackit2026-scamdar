from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
import warnings
from contextlib import asynccontextmanager
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import APP_ENV, AUTH_SECRET, FRONTEND_ORIGINS, MAX_UPLOAD_BYTES, MAX_REQUEST_BYTES, RATE_LIMIT_PER_MINUTE, TOKEN_TTL_HOURS, OCR_ENABLED
from .database import Base, engine, get_db
from .models import AuditLog, Comment, Flag, HelpfulVote, Notification, ScamReport, TrustedContact, User, Vote, now_utc
from .schemas import AnalyzeIn, CommentIn, FlagIn, LoginIn, ModerationWarningIn, ReportIn, SignupIn, TrustedContactIn, TrustedResponseIn, VoteIn
from .scoring import analyze_text, similarity

@asynccontextmanager
async def lifespan(_: FastAPI):
    if APP_ENV == "production" and len(AUTH_SECRET) < 32:
        raise RuntimeError("Set AUTH_SECRET to a random value of at least 32 characters in production.")
    Base.metadata.create_all(bind=engine)
    from .seed import seed_reports
    seed_reports()
    yield


app = FastAPI(title="ScamDar API", version="0.1.0", description="Explainable community scam-awareness API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=FRONTEND_ORIGINS, allow_credentials=False,
                   allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
                   allow_headers=["Authorization", "Content-Type"], max_age=600)

_token_secret = AUTH_SECRET.encode() if AUTH_SECRET else secrets.token_bytes(32)
_rate_buckets: dict[str, deque[float]] = defaultdict(deque)
_upload_mime = {"image/png": b"\x89PNG\r\n\x1a\n", "image/jpeg": b"\xff\xd8\xff", "image/webp": b"RIFF"}


@app.middleware("http")
async def security_and_rate_limit(request: Request, call_next):
    path = request.url.path
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_REQUEST_BYTES:
        return JSONResponse({"detail": "Request body is too large."}, status_code=413)
    if path.startswith("/api/") and path not in {"/api/health", "/api/openapi.json", "/api/docs", "/api/redoc"}:
        key = f"{request.client.host if request.client else 'unknown'}:{path.split('/')[2]}"
        limit = min(RATE_LIMIT_PER_MINUTE, 10) if path.startswith("/api/auth/") else RATE_LIMIT_PER_MINUTE
        now = time.monotonic()
        bucket = _rate_buckets[key]
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= limit:
            return JSONResponse({"detail": "Too many requests. Please wait a minute and try again."}, status_code=429)
        bucket.append(now)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if APP_ENV == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _make_token(user: User) -> str:
    expires = int(time.time()) + TOKEN_TTL_HOURS * 3600
    payload = _b64(json.dumps({"sub": user.id, "role": user.role, "exp": expires}, separators=(",", ":")).encode())
    signature = _b64(hmac.new(_token_secret, payload.encode(), hashlib.sha256).digest())
    return payload + "." + signature


def _decode_token(token: str) -> dict:
    try:
        payload, signature = token.split(".", 1)
        expected = _b64(hmac.new(_token_secret, payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("bad signature")
        raw = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        body = json.loads(raw)
        if int(body["exp"]) < int(time.time()):
            raise ValueError("expired")
        return body
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=401, detail="Your session is invalid or expired. Please sign in again.") from exc


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    claims = _decode_token(header[7:].strip())
    user = db.get(User, int(claims["sub"]))
    if not user or not user.active:
        raise HTTPException(status_code=401, detail="This account is unavailable.")
    return user


def require_moderator(user: User = Depends(current_user)) -> User:
    if user.role not in {"moderator", "admin"}:
        raise HTTPException(status_code=403, detail="Moderator access is required.")
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    return user


def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"pbkdf2_sha256${_b64(salt)}${_b64(digest)}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt, expected = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = _b64(hashlib.pbkdf2_hmac("sha256", password.encode(), base64.urlsafe_b64decode(salt + "=" * (-len(salt) % 4)), 310_000))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _plain(text: str) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text).strip()


def _votes(db: Session, report_id: int) -> dict:
    rows = db.execute(select(Vote.choice, func.count(Vote.id)).where(Vote.report_id == report_id).group_by(Vote.choice)).all()
    counts = {choice: int(count) for choice, count in rows}
    total = sum(counts.values())
    confidence = round(counts.get("Scam", 0) / total * 100) if total else None
    return {"counts": {key: counts.get(key, 0) for key in ("Scam", "Not sure", "Likely legitimate")}, "community_confidence": confidence, "total": total}


def _report_dict(report: ScamReport, db: Session) -> dict:
    vote_summary = _votes(db, report.id)
    report_count = db.scalar(select(func.count(ScamReport.id)).where(ScamReport.campaign_key == report.campaign_key, ScamReport.status.in_(["active", "verified"]))) or 1
    return {"id": report.id, "title": report.title, "content": report.content, "category": report.category,
            "report_count": report_count,
            "region": report.region, "impersonated_brand": report.impersonated_brand, "url": report.url,
            "phone": report.phone, "score": report.score, "risk_level": report.risk_level,
            "status": report.status, "merged_into_id": report.merged_into_id, "created_at": report.first_seen.isoformat(), "last_seen": report.last_seen.isoformat(),
            "comment_count": db.scalar(select(func.count(Comment.id)).where(Comment.report_id == report.id, Comment.hidden.is_(False))) or 0,
            "vote_summary": vote_summary}


def _matches(db: Session, text: str, limit: int = 5) -> list[dict]:
    candidates = db.scalars(select(ScamReport).where(ScamReport.status.in_(["active", "verified"])).order_by(ScamReport.last_seen.desc()).limit(250)).all()
    ranked = [(similarity(text, row.content), row) for row in candidates]
    ranked = [(score, row) for score, row in ranked if score >= 0.16]
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    result = []
    for score, report in ranked[:limit]:
        item = _report_dict(report, db)
        item["similarity"] = round(score * 100)
        result.append(item)
    return result


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "ScamDar API", "environment": APP_ENV}


@app.post("/api/auth/signup")
def signup(payload: SignupIn, db: Session = Depends(get_db)):
    email = str(payload.email).lower().strip()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(email=email, display_name=_plain(payload.display_name), password_hash=_password_hash(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"token": _make_token(user), "user": {"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role}}


@app.post("/api/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(payload.email).lower().strip()))
    if not user or not _verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    return {"token": _make_token(user), "user": {"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role}}


@app.post("/api/auth/logout")
def logout(_: User = Depends(current_user)):
    # The short-lived bearer token is held by the client and deleted on logout.
    return {"ok": True, "message": "Remove the session token from this device."}


@app.post("/api/analyze")
def analyze(payload: AnalyzeIn, db: Session = Depends(get_db)):
    text = _plain(payload.text)
    matches = _matches(db, text, limit=250)
    related_count = sum(1 for item in matches if item["similarity"] >= 35)
    result = analyze_text(text, community_matches=related_count)
    return {**result, "similar_reports": matches[:5], "community": {"related_reports": related_count, "confidence_is_separate": True}}


@app.post("/api/analyze/screenshot")
async def analyze_screenshot(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type not in _upload_mime:
        raise HTTPException(status_code=415, detail="Upload a PNG, JPEG, or WebP screenshot.")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Screenshot must be 5 MB or smaller.")
    signature = _upload_mime[file.content_type]
    if not data.startswith(signature) or (file.content_type == "image/webp" and data[8:12] != b"WEBP"):
        raise HTTPException(status_code=415, detail="File contents do not match the selected image type.")
    if not OCR_ENABLED:
        raise HTTPException(status_code=503, detail="Screenshot upload is validated, but OCR is disabled. Enable OCR_ENABLED and install the Tesseract engine to extract text.")
    try:
        from PIL import Image
        import pytesseract
        from io import BytesIO
        Image.MAX_IMAGE_PIXELS = 64_000_000
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", Image.DecompressionBombWarning)
            source = Image.open(BytesIO(data))
            if source.width * source.height > 16_000_000:
                raise HTTPException(status_code=413, detail="Screenshot dimensions are too large to process safely.")
            image = source.convert("RGB")
        image.thumbnail((3000, 3000))
        extracted = _plain(pytesseract.image_to_string(image)[:8000])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="OCR could not read this image. You can paste the message text instead.") from exc
    if len(extracted) < 3:
        raise HTTPException(status_code=422, detail="No readable message text was found in the screenshot.")
    matches = _matches(db, extracted)
    return {"extracted_text": extracted, **analyze_text(extracted, sum(m["similarity"] >= 35 for m in matches)), "similar_reports": matches}


@app.get("/api/reports")
def list_reports(sort: str = "newest", category: str | None = None, region: str | None = None, limit: int = 30, offset: int = 0, db: Session = Depends(get_db)):
    limit = min(max(limit, 1), 100)
    query = select(ScamReport).where(ScamReport.status.in_(["active", "verified"]))
    if category and category != "all": query = query.where(ScamReport.category == category)
    if region and region != "all": query = query.where(ScamReport.region == region)
    if sort == "trending": query = query.order_by(ScamReport.last_seen.desc(), ScamReport.score.desc())
    elif sort == "most-reported":
        campaign_counts = select(ScamReport.campaign_key, func.count(ScamReport.id).label("campaign_count")).where(ScamReport.status.in_(["active", "verified"])).group_by(ScamReport.campaign_key).subquery()
        query = query.outerjoin(campaign_counts, ScamReport.campaign_key == campaign_counts.c.campaign_key).order_by(campaign_counts.c.campaign_count.desc(), ScamReport.last_seen.desc())
    else: query = query.order_by(ScamReport.first_seen.desc())
    return {"items": [_report_dict(row, db) for row in db.scalars(query.offset(max(0, offset)).limit(limit)).all()], "limit": limit, "offset": max(0, offset)}


@app.get("/api/reports/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.get(ScamReport, report_id)
    if report and report.status == "merged" and report.merged_into_id:
        return RedirectResponse(url=f"/api/reports/{report.merged_into_id}", status_code=307)
    if not report or report.status == "hidden": raise HTTPException(status_code=404, detail="Report not found.")
    signals = analyze_text(report.content)["signals"]
    similar = [item for item in _matches(db, report.content, 6) if item["id"] != report.id]
    return {**_report_dict(report, db), "signals": signals, "recommended_action": analyze_text(report.content)["recommended_action"],
            "similar_reports": similar, "discussion_locked": report.status == "locked"}


@app.post("/api/reports")
def create_report(payload: ReportIn, allow_duplicate: bool = False, db: Session = Depends(get_db), user: User = Depends(current_user)):
    content = _plain(payload.content)
    if len(content) < 12: raise HTTPException(status_code=422, detail="Please include enough message context to assess the report.")
    near = _matches(db, content, 5)
    duplicates = [item for item in near if item["similarity"] >= 68]
    if duplicates and not allow_duplicate:
        return JSONResponse({"duplicate": True, "message": "This may already be reported. Review similar campaigns before adding another report.", "similar_reports": duplicates}, status_code=409)
    result = analyze_text(content, sum(item["similarity"] >= 35 for item in near))
    combined = " ".join(part for part in (content, payload.url or "", payload.description or "") if part)
    related_campaign = next((db.get(ScamReport, item["id"]) for item in near if item["similarity"] >= 35), None)
    campaign_key = related_campaign.campaign_key if related_campaign else f"{payload.category}:{hashlib.sha256(content.lower().encode()).hexdigest()[:20]}"
    report = ScamReport(title=(content[:110].rsplit(" ", 1)[0] or content[:110]), content=combined[:9000], category=payload.category or result["category"], campaign_key=campaign_key,
                        region=payload.region, impersonated_brand=_plain(payload.impersonated_brand or "") or None,
                        url=_plain(payload.url or "") or None, phone=_plain(payload.phone or "") or None,
                        score=result["score"], risk_level=result["level"], created_by=user.id)
    db.add(report); db.commit(); db.refresh(report)
    db.add(AuditLog(actor_id=user.id, action="report.created", target_type="report", target_id=report.id, detail="User created community report")); db.commit()
    return _report_dict(report, db)


@app.post("/api/reports/{report_id}/votes")
def vote(report_id: int, payload: VoteIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    report = db.get(ScamReport, report_id)
    if not report or report.status == "hidden": raise HTTPException(status_code=404, detail="Report not found.")
    existing = db.scalar(select(Vote).where(Vote.user_id == user.id, Vote.report_id == report_id))
    if existing: existing.choice = payload.choice
    else: db.add(Vote(user_id=user.id, report_id=report_id, choice=payload.choice))
    db.commit()
    return _votes(db, report_id)


@app.get("/api/reports/{report_id}/comments")
def get_comments(report_id: int, db: Session = Depends(get_db)):
    if not db.get(ScamReport, report_id): raise HTTPException(status_code=404, detail="Report not found.")
    rows = db.scalars(select(Comment).where(Comment.report_id == report_id, Comment.hidden.is_(False)).order_by(Comment.created_at.asc())).all()
    names = {u.id: u.display_name for u in db.scalars(select(User).where(User.id.in_({r.user_id for r in rows}))).all()} if rows else {}
    return {"items": [{"id": c.id, "parent_id": c.parent_id, "body": c.body, "author": names.get(c.user_id, "Community member"), "helpful_count": c.helpful_count, "created_at": c.created_at.isoformat()} for c in rows]}


@app.post("/api/reports/{report_id}/comments")
def add_comment(report_id: int, payload: CommentIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    report = db.get(ScamReport, report_id)
    if not report or report.status in {"hidden", "locked"}: raise HTTPException(status_code=404 if not report else 423, detail="Discussion is unavailable or locked.")
    body = _plain(payload.body)
    if not body: raise HTTPException(status_code=422, detail="Comment cannot be empty.")
    if payload.parent_id and not db.scalar(select(Comment.id).where(Comment.id == payload.parent_id, Comment.report_id == report_id, Comment.hidden.is_(False))):
        raise HTTPException(status_code=404, detail="Reply target not found in this discussion.")
    comment = Comment(report_id=report_id, user_id=user.id, parent_id=payload.parent_id, body=body)
    db.add(comment); db.flush()
    if report.created_by and report.created_by != user.id:
        db.add(Notification(user_id=report.created_by, kind="reply", message=f"{user.display_name} commented on your scam report."))
    db.commit(); db.refresh(comment)
    return {"id": comment.id, "parent_id": comment.parent_id, "body": comment.body, "author": user.display_name, "helpful_count": 0}


@app.post("/api/comments/{comment_id}/helpful")
def helpful(comment_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    comment = db.get(Comment, comment_id)
    if not comment or comment.hidden: raise HTTPException(status_code=404, detail="Comment not found.")
    existing = db.scalar(select(HelpfulVote.id).where(HelpfulVote.user_id == user.id, HelpfulVote.comment_id == comment_id))
    if existing:
        return {"id": comment.id, "helpful_count": comment.helpful_count, "already_marked": True}
    db.add(HelpfulVote(user_id=user.id, comment_id=comment_id))
    comment.helpful_count += 1
    db.commit()
    return {"id": comment.id, "helpful_count": comment.helpful_count}


@app.post("/api/flags")
def flag_content(payload: FlagIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if payload.target_type == "report": target = db.get(ScamReport, payload.target_id)
    elif payload.target_type == "comment": target = db.get(Comment, payload.target_id)
    else: raise HTTPException(status_code=422, detail="Flags can target a report or comment.")
    if not target: raise HTTPException(status_code=404, detail="Content not found.")
    flag = Flag(reporter_id=user.id, target_type=payload.target_type, target_id=payload.target_id, reason=_plain(payload.reason), details=_plain(payload.details))
    db.add(flag); db.commit(); db.refresh(flag)
    return {"id": flag.id, "status": flag.status}


@app.get("/api/moderation/flags")
def moderation_queue(db: Session = Depends(get_db), _: User = Depends(require_moderator)):
    flags = db.scalars(select(Flag).where(Flag.status == "open").order_by(Flag.created_at.asc()).limit(100)).all()
    items = []
    for flag in flags:
        target = db.get(ScamReport, flag.target_id) if flag.target_type == "report" else db.get(Comment, flag.target_id)
        owner_id = target.created_by if flag.target_type == "report" and target else target.user_id if target else None
        items.append({"id": flag.id, "target_type": flag.target_type, "target_id": flag.target_id, "target_user_id": owner_id,
                      "reason": flag.reason, "details": flag.details, "created_at": flag.created_at.isoformat()})
    return {"items": items}


@app.patch("/api/moderation/flags/{flag_id}")
def resolve_flag(flag_id: int, action: str, db: Session = Depends(get_db), user: User = Depends(require_moderator)):
    if action not in {"dismiss", "hide", "verify", "lock"}: raise HTTPException(status_code=422, detail="Choose dismiss, hide, verify, or lock.")
    flag = db.get(Flag, flag_id)
    if not flag or flag.status != "open": raise HTTPException(status_code=404, detail="Open flag not found.")
    if action != "dismiss":
        if flag.target_type == "report":
            target = db.get(ScamReport, flag.target_id)
            if target: target.status = {"hide": "hidden", "verify": "verified", "lock": "locked"}[action]
        elif flag.target_type == "comment" and action == "hide":
            target = db.get(Comment, flag.target_id)
            if target: target.hidden = True
    flag.status = "resolved"; flag.resolution = action
    db.add(Notification(user_id=flag.reporter_id, kind="moderation-update", message=f"A moderator reviewed your flag and chose: {action}."))
    db.add(AuditLog(actor_id=user.id, action=f"moderation.{action}", target_type=flag.target_type, target_id=flag.target_id, detail=f"Flag {flag_id}"))
    db.commit()
    return {"id": flag.id, "status": flag.status, "action": action}


@app.post("/api/moderation/users/{user_id}/warn")
def warn_user(user_id: int, payload: ModerationWarningIn, db: Session = Depends(get_db), actor: User = Depends(require_moderator)):
    target = db.get(User, user_id)
    if not target: raise HTTPException(status_code=404, detail="User not found.")
    db.add(Notification(user_id=target.id, kind="moderation-warning", message=_plain(payload.message)))
    db.add(AuditLog(actor_id=actor.id, action="moderation.user_warned", target_type="user", target_id=target.id, detail="Moderation warning sent"))
    db.commit()
    return {"ok": True, "user_id": target.id}


@app.post("/api/moderation/reports/{source_id}/merge")
def merge_reports(source_id: int, into_id: int, db: Session = Depends(get_db), actor: User = Depends(require_moderator)):
    source, destination = db.get(ScamReport, source_id), db.get(ScamReport, into_id)
    if not source or not destination or source.id == destination.id:
        raise HTTPException(status_code=404, detail="Choose two different existing reports.")
    if source.status == "merged" or destination.status not in {"active", "verified"}:
        raise HTTPException(status_code=409, detail="The selected reports cannot be merged in their current state.")
    for source_vote in db.scalars(select(Vote).where(Vote.report_id == source.id)).all():
        existing = db.scalar(select(Vote.id).where(Vote.report_id == destination.id, Vote.user_id == source_vote.user_id))
        if existing: db.delete(source_vote)
        else: source_vote.report_id = destination.id
    for comment in db.scalars(select(Comment).where(Comment.report_id == source.id)).all(): comment.report_id = destination.id
    for flag in db.scalars(select(Flag).where(Flag.target_type == "report", Flag.target_id == source.id)).all(): flag.target_id = destination.id
    destination.first_seen = min(destination.first_seen, source.first_seen)
    destination.last_seen = now_utc()
    source.status = "merged"; source.merged_into_id = destination.id
    db.add(AuditLog(actor_id=actor.id, action="moderation.reports_merged", target_type="report", target_id=source.id, detail=f"Merged into report {destination.id}"))
    db.commit()
    return {"merged_report_id": source.id, "into_report_id": destination.id}


@app.post("/api/trusted-contacts")
def ask_trusted_contact(payload: TrustedContactIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    token = secrets.token_urlsafe(32)
    contact = TrustedContact(owner_id=user.id, contact_email=str(payload.contact_email).lower(), token=token,
                             message=_plain(payload.message), expires_at=now_utc() + timedelta(days=7))
    db.add(contact); db.commit(); db.refresh(contact)
    db.add(Notification(user_id=user.id, kind="trusted-contact", message="Trusted contact request created. Share its response link privately.")); db.commit()
    # Email delivery is not configured; return a one-time share token for this hackathon demo.
    return {"id": contact.id, "response_token": token, "expires_at": contact.expires_at.isoformat(), "delivery": "manual-share"}


@app.post("/api/trusted-contacts/{token}/respond")
def respond_trusted_contact(token: str, payload: TrustedResponseIn, db: Session = Depends(get_db)):
    contact = db.scalar(select(TrustedContact).where(TrustedContact.token == token))
    expiry = contact.expires_at.replace(tzinfo=timezone.utc) if contact and contact.expires_at.tzinfo is None else (contact.expires_at.astimezone(timezone.utc) if contact else None)
    if not contact or expiry < now_utc(): raise HTTPException(status_code=404, detail="This trusted contact link has expired or is invalid.")
    contact.response = payload.response
    db.add(Notification(user_id=contact.owner_id, kind="trusted-response", message=f"Your trusted contact responded: {payload.response}."))
    db.commit()
    return {"ok": True, "response": payload.response}


@app.get("/api/notifications")
def notifications(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(100)).all()
    return {"items": [{"id": n.id, "kind": n.kind, "message": n.message, "read": n.read, "created_at": n.created_at.isoformat()} for n in rows]}


@app.get("/api/trends")
def trends(db: Session = Depends(get_db)):
    reports = db.scalars(select(ScamReport).where(ScamReport.status.in_(["active", "verified"]))).all()
    today = now_utc() - timedelta(days=1); week = now_utc() - timedelta(days=7)
    def utc(value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    by_category, by_region, brands = defaultdict(int), defaultdict(int), defaultdict(int)
    daily = defaultdict(int)
    for row in reports:
        by_category[row.category] += 1; by_region[row.region] += 1
        if row.impersonated_brand: brands[row.impersonated_brand] += 1
        stamp = row.first_seen.date().isoformat(); daily[stamp] += 1
    return {"reports_today": sum(1 for r in reports if utc(r.first_seen) >= today), "reports_this_week": sum(1 for r in reports if utc(r.first_seen) >= week),
            "active_campaigns": len({(r.category, r.impersonated_brand or r.title[:20]) for r in reports}),
            "by_category": dict(sorted(by_category.items(), key=lambda item: -item[1])), "by_region": dict(by_region),
            "top_brands": dict(sorted(brands.items(), key=lambda item: -item[1])[:8]), "activity": dict(sorted(daily.items())),
            "note": "Counts use broad regions only. Synthetic seed records may use the seed run date."}


@app.get("/api/admin/summary")
def admin_summary(db: Session = Depends(get_db), _: User = Depends(require_moderator)):
    recent_reports = db.scalars(select(ScamReport).where(ScamReport.status.in_(["active", "verified", "locked"])).order_by(ScamReport.last_seen.desc()).limit(10)).all()
    return {"users": db.scalar(select(func.count(User.id))) or 0, "reports": db.scalar(select(func.count(ScamReport.id))) or 0,
            "active_campaigns": db.scalar(select(func.count(func.distinct(ScamReport.campaign_key))).where(ScamReport.status.in_(["active", "verified", "locked"]))) or 0,
            "open_flags": db.scalar(select(func.count(Flag.id)).where(Flag.status == "open")) or 0,
            "recent_reports": [_report_dict(report, db) for report in recent_reports],
            "recent_audit": [{"action": a.action, "target_type": a.target_type, "target_id": a.target_id, "created_at": a.created_at.isoformat()} for a in db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(20)).all()]}


@app.get("/api/admin/users")
def admin_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return {"items": [{"id": u.id, "email": u.email, "display_name": u.display_name, "role": u.role, "active": u.active} for u in db.scalars(select(User).order_by(User.id)).all()]}


@app.patch("/api/admin/users/{user_id}/role")
def set_user_role(user_id: int, role: str, db: Session = Depends(get_db), actor: User = Depends(require_admin)):
    if role not in {"user", "trusted_contributor", "moderator", "admin"}: raise HTTPException(status_code=422, detail="Unknown role.")
    target = db.get(User, user_id)
    if not target: raise HTTPException(status_code=404, detail="User not found.")
    target.role = role
    db.add(AuditLog(actor_id=actor.id, action="user.role_changed", target_type="user", target_id=user_id, detail=f"Role changed to {role}")); db.commit()
    return {"id": target.id, "role": target.role}
