from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

REGIONS = {"Singapore-wide", "Central", "East", "North", "Northeast", "West"}
CATEGORIES = {
    "delivery", "banking", "government", "job-task", "investment", "phishing",
    "marketplace", "refund", "tech-support", "other",
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SignupIn(StrictModel):
    email: EmailStr
    display_name: str = Field(min_length=2, max_length=60)
    password: str = Field(min_length=10, max_length=128)


class LoginIn(StrictModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AnalyzeIn(StrictModel):
    text: str = Field(min_length=3, max_length=8000)


class ReportIn(StrictModel):
    content: str = Field(min_length=12, max_length=8000)
    category: str = Field(default="other", max_length=48)
    region: str = "Singapore-wide"
    url: str | None = Field(default=None, max_length=2048)
    phone: str | None = Field(default=None, max_length=40)
    impersonated_brand: str | None = Field(default=None, max_length=80)
    description: str = Field(default="", max_length=1200)

    @field_validator("region")
    @classmethod
    def broad_region_only(cls, value: str) -> str:
        if value not in REGIONS:
            raise ValueError("Choose a broad Singapore region; precise locations are not collected.")
        return value

    @field_validator("category")
    @classmethod
    def valid_category(cls, value: str) -> str:
        if value not in CATEGORIES:
            raise ValueError("Unknown scam category.")
        return value


class VoteIn(StrictModel):
    choice: str

    @field_validator("choice")
    @classmethod
    def valid_choice(cls, value: str) -> str:
        if value not in {"Scam", "Not sure", "Likely legitimate"}:
            raise ValueError("Choose Scam, Not sure, or Likely legitimate.")
        return value


class CommentIn(StrictModel):
    body: str = Field(min_length=1, max_length=1200)
    parent_id: int | None = None


class FlagIn(StrictModel):
    target_type: str
    target_id: int = Field(gt=0)
    reason: str = Field(min_length=3, max_length=80)
    details: str = Field(default="", max_length=500)


class TrustedContactIn(StrictModel):
    contact_email: EmailStr
    message: str = Field(min_length=3, max_length=1000)


class TrustedResponseIn(StrictModel):
    response: str

    @field_validator("response")
    @classmethod
    def valid_response(cls, value: str) -> str:
        if value not in {"Do not proceed", "Looks safe", "I am unsure"}:
            raise ValueError("Unknown response.")
        return value


class ModerationWarningIn(StrictModel):
    message: str = Field(min_length=5, max_length=240)
