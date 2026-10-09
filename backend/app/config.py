from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def get_setting(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


DATABASE_URL = get_setting("DATABASE_URL", "sqlite:///./scamdar.db")
APP_ENV = get_setting("APP_ENV", "development")
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in get_setting("FRONTEND_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
TOKEN_TTL_HOURS = int(get_setting("TOKEN_TTL_HOURS", "24"))
MAX_UPLOAD_BYTES = int(get_setting("MAX_UPLOAD_BYTES", "5242880"))
MAX_REQUEST_BYTES = int(get_setting("MAX_REQUEST_BYTES", "6291456"))
RATE_LIMIT_PER_MINUTE = int(get_setting("RATE_LIMIT_PER_MINUTE", "30"))
OCR_ENABLED = get_setting("OCR_ENABLED", "false").lower() == "true"
AUTH_SECRET = get_setting("AUTH_SECRET", "")
