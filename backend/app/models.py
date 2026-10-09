from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(60))
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(24), default="user")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class ScamReport(Base):
    __tablename__ = "scam_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(48), index=True)
    campaign_key: Mapped[str] = mapped_column(String(100), index=True, default="uncategorized")
    merged_into_id: Mapped[int | None] = mapped_column(ForeignKey("scam_reports.id"), nullable=True)
    region: Mapped[str] = mapped_column(String(24), default="Singapore-wide", index=True)
    impersonated_brand: Mapped[str | None] = mapped_column(String(80), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    risk_level: Mapped[str] = mapped_column(String(16), default="Low")
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    is_seed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    comments: Mapped[list["Comment"]] = relationship(back_populates="report", cascade="all, delete-orphan")


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("user_id", "report_id", name="uq_vote_user_report"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("scam_reports.id"), index=True)
    choice: Mapped[str] = mapped_column(String(24))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("scam_reports.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("comments.id"), nullable=True)
    body: Mapped[str] = mapped_column(String(1200))
    helpful_count: Mapped[int] = mapped_column(Integer, default=0)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    report: Mapped[ScamReport] = relationship(back_populates="comments")


class HelpfulVote(Base):
    __tablename__ = "helpful_votes"
    __table_args__ = (UniqueConstraint("user_id", "comment_id", name="uq_helpful_user_comment"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    comment_id: Mapped[int] = mapped_column(ForeignKey("comments.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Flag(Base):
    __tablename__ = "flags"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    target_type: Mapped[str] = mapped_column(String(16))
    target_id: Mapped[int] = mapped_column(Integer, index=True)
    reason: Mapped[str] = mapped_column(String(80))
    details: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    resolution: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class TrustedContact(Base):
    __tablename__ = "trusted_contacts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    contact_email: Mapped[str] = mapped_column(String(254))
    token: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    message: Mapped[str] = mapped_column(String(1000))
    response: Mapped[str | None] = mapped_column(String(24), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(String(240))
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    target_type: Mapped[str] = mapped_column(String(32))
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
