import asyncio
import secrets
from io import BytesIO

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.datastructures import Headers, UploadFile
from starlette.requests import Request

from app.database import Base
from app.main import (
    add_comment, analyze, analyze_screenshot, ask_trusted_contact, create_report,
    flag_content, get_comments, get_report, helpful, login, notifications,
    merge_reports, moderation_queue, respond_trusted_contact, resolve_flag, signup, vote, warn_user,
    current_user, require_moderator,
)
from app.models import AuditLog, ScamReport, User
from app.schemas import AnalyzeIn, CommentIn, FlagIn, LoginIn, ModerationWarningIn, ReportIn, SignupIn, TrustedContactIn, TrustedResponseIn, VoteIn
from app.seed import CAMPAIGNS


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    with session_factory() as session:
        yield session
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def new_user(db, email="demo@example.com"):
    password = secrets.token_urlsafe(24)
    auth = signup(SignupIn(email=email, display_name="Demo User", password=password), db)
    return db.scalar(select(User).where(User.email == email)), auth["token"], password


def test_public_checker_returns_explainable_demo_score(db):
    message = "Your SingPost parcel has been detained. Pay $2.03 today to arrange delivery at http://example-suspicious-link.test"
    for category, brand, campaign, messages in CAMPAIGNS:
        for content in messages:
            db.add(ScamReport(title=campaign, content=content, category=category, campaign_key=f"{category}:{brand}", region="Central", score=84, risk_level="High", is_seed=True))
    db.commit()
    result = analyze(AnalyzeIn(text=message), db)
    assert result["level"] == "High"
    assert result["score"] == 92
    codes = {signal["code"] for signal in result["signals"]}
    assert {"urgency", "payment", "delivery_impersonation", "brand_impersonation", "suspicious_domain", "campaign_activity"}.issubset(codes)
    assert result["community"]["confidence_is_separate"] is True
    assert "independently verified" in result["recommended_action"]


def test_auth_report_duplicate_vote_and_comments(db):
    user, token, password = new_user(db)
    assert login(LoginIn(email=user.email, password=password), db)["user"]["id"] == user.id
    payload = ReportIn(content="Fake SingPost parcel held. Pay $2.03 today at http://parcel-check.test", category="delivery", region="Central")
    report = create_report(payload, False, db, user)
    duplicate = create_report(payload, False, db, user)
    assert duplicate.status_code == 409
    report_id = report["id"]
    assert vote(report_id, VoteIn(choice="Scam"), db, user)["counts"]["Scam"] == 1
    summary = vote(report_id, VoteIn(choice="Not sure"), db, user)
    assert summary["total"] == 1
    assert summary["counts"]["Not sure"] == 1
    comment = add_comment(report_id, CommentIn(body="Check the official delivery app before paying."), db, user)
    assert len(get_comments(report_id, db)["items"]) == 1
    assert helpful(comment["id"], db, user)["helpful_count"] == 1
    assert helpful(comment["id"], db, user)["already_marked"] is True
    assert get_report(report_id, db)["report_count"] == 1


def test_auth_is_required_and_regions_are_broad_only(db):
    request = Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1), "server": ("test", 80), "method": "GET", "scheme": "http", "path": "/api/reports", "query_string": b""})
    with pytest.raises(HTTPException) as error:
        current_user(request, db)
    assert error.value.status_code == 401
    with pytest.raises(ValidationError):
        ReportIn(content="A suspicious message with enough useful context", region="Block 123, Example Street")
    assert ReportIn(content="A suspicious message with enough useful context", region="Central").region == "Central"


def test_moderator_handles_flag_and_audit(db):
    user, _, _ = new_user(db)
    report = create_report(ReportIn(content="Fake refund request asks me to pay today at http://refund-check.test", category="refund"), False, db, user)
    flag = flag_content(FlagIn(target_type="report", target_id=report["id"], reason="Possible misinformation"), db, user)
    with pytest.raises(HTTPException) as denied:
        require_moderator(user)
    assert denied.value.status_code == 403
    user.role = "moderator"
    db.commit()
    assert len(moderation_queue(db, user)["items"]) == 1
    assert resolve_flag(flag["id"], "verify", db, user)["status"] == "resolved"
    assert get_report(report["id"], db)["status"] == "verified"
    assert db.scalar(select(AuditLog.id).where(AuditLog.action == "moderation.verify")) is not None
    assert any("moderator reviewed your flag" in item["message"] for item in notifications(db, user)["items"])


def test_trusted_contact_response_notifies_requester(db):
    user, _, _ = new_user(db)
    request = ask_trusted_contact(TrustedContactIn(contact_email="friend@example.net", message="Can you help me check this message?"), db, user)
    assert respond_trusted_contact(request["response_token"], TrustedResponseIn(response="Do not proceed"), db)["ok"] is True
    items = notifications(db, user)["items"]
    assert any("Do not proceed" in item["message"] for item in items)


def test_moderator_warning_and_duplicate_merge(db):
    user, _, _ = new_user(db)
    user.role = "moderator"; db.commit()
    first = create_report(ReportIn(content="SingPost parcel has been held. Pay a small delivery fee today at http://parcel-check.test", category="delivery"), True, db, user)
    second = create_report(ReportIn(content="SingPost parcel held: pay the delivery fee today at http://parcel-check.test", category="delivery"), True, db, user)
    vote(first["id"], VoteIn(choice="Scam"), db, user)
    vote(second["id"], VoteIn(choice="Not sure"), db, user)
    comment = add_comment(first["id"], CommentIn(body="Check the official delivery app first."), db, user)
    assert warn_user(user.id, ModerationWarningIn(message="Please keep reports factual and avoid personal data."), db, user)["ok"] is True
    result = merge_reports(first["id"], second["id"], db, user)
    assert result["into_report_id"] == second["id"]
    assert get_report(first["id"], db).status_code == 307
    assert len(get_comments(second["id"], db)["items"]) == 1
    assert any("Please keep reports factual" in item["message"] for item in notifications(db, user)["items"])


def test_unsupported_screenshot_type_is_rejected(db):
    upload = UploadFile(filename="image.svg", file=BytesIO(b"<svg></svg>"), headers=Headers({"content-type": "image/svg+xml"}))
    with pytest.raises(HTTPException) as error:
        asyncio.run(analyze_screenshot(upload, db))
    assert error.value.status_code == 415
