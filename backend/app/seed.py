"""Create 60 fictional reports for the demo; never use real victim data."""

from sqlalchemy import select

from .database import Base, SessionLocal, engine
from .models import ScamReport
from .scoring import analyze_text

CAMPAIGNS = [
    ("delivery", "Fake SingPost", "SingPost parcel delivery", [
        "Your SingPost parcel has been detained. Pay $2.03 today to arrange delivery at http://example-suspicious-link.test",
        "SingPost: parcel held at sorting centre. Pay S$2.03 today to reschedule delivery at http://singpost-redelivery.test",
        "Your parcel is waiting. Final notice: pay a delivery fee today at http://parcel-fee.test",
        "SingPost delivery failed. A small redelivery payment is required now at http://sp-delivery.test",
        "Parcel detained by customs. Pay the outstanding delivery fee today at http://parcel-release.test",
        "We could not deliver your SingPost item. Confirm payment and address at http://singpost-track.test",
    ]),
    ("banking", "Fake DBS", "DBS account alert", [
        "DBS security alert: your account will be blocked today. Verify your login and OTP at http://dbs-secure.test",
        "DBS: unusual transfer detected. Confirm your password immediately at http://dbs-check.test",
        "Your DBS card is suspended. Update card details now to restore access at http://dbs-card.test",
        "DBS refund pending. Enter your account and one-time password at http://dbs-refund.test",
        "DBS: your PayNow profile expires today. Verify your PIN at http://dbs-paynow.test",
        "A transfer needs your approval. Sign in to DBS and enter the verification code at http://dbs-confirm.test",
    ]),
    ("banking", "Fake OCBC", "OCBC account alert", [
        "OCBC: your account access is limited. Verify your password and OTP today at http://ocbc-verify.test",
        "OCBC security notice: suspicious activity. Confirm card details immediately at http://ocbc-alert.test",
        "Your OCBC reward is ready. Pay a small processing fee today at http://ocbc-reward.test",
        "OCBC: update Singpass credentials now to avoid account suspension at http://ocbc-login.test",
        "A new device accessed your OCBC account. Confirm the verification code at http://ocbc-device.test",
    ]),
    ("banking", "Fake UOB", "UOB payment alert", [
        "UOB: pending payment needs confirmation today. Enter your OTP at http://uob-payment.test",
        "Your UOB account will be suspended. Verify card details now at http://uob-secure.test",
        "UOB cashback refund: pay S$1.50 processing fee today at http://uob-cashback.test",
        "Security check required. Sign in with your UOB password at http://uob-check.test",
        "Your UOB PayNow access expires today. Confirm your PIN at http://uob-paynow.test",
    ]),
    ("government", "Fake IRAS", "Government tax notice", [
        "IRAS tax refund: confirm your bank details today or the claim expires at http://iras-refund.test",
        "Final notice from IRAS. Pay outstanding tax immediately at http://iras-payment.test",
        "IRAS: your tax account is locked. Enter Singpass and OTP to restore access at http://iras-access.test",
        "A tax rebate is ready. Pay the verification fee today at http://iras-rebate.test",
        "IRAS payment overdue. Transfer the amount today to avoid legal action at http://iras-final.test",
    ]),
    ("government", "Fake CPF", "CPF account notice", [
        "CPF: confirm Singpass password and OTP today to protect your account at http://cpf-verify.test",
        "Your CPF withdrawal is pending. Pay a release fee now at http://cpf-release.test",
        "CPF account suspended. Verify your identity immediately at http://cpf-identity.test",
        "CPF investment bonus: transfer a deposit today to unlock returns at http://cpf-bonus.test",
        "New CPF statement available. Sign in and enter your PIN at http://cpf-statement.test",
    ]),
    ("job-task", "Job/task offer", "Remote task job offer", [
        "Earn S$500 a day by liking posts. Transfer a deposit now to unlock tasks on Telegram.",
        "Part-time job offer: pay a registration fee today and get guaranteed daily income.",
        "A recruiter asks for your bank login and OTP to release your first salary.",
        "Complete easy online tasks and deposit more money today to unlock your commission.",
        "Remote job: buy gift cards immediately for equipment and claim reimbursement later.",
    ]),
    ("investment", "Telegram investment", "Telegram investment group", [
        "Join our Telegram investment group. Transfer crypto today for guaranteed 20% weekly returns.",
        "A trading mentor says to send a deposit now to unlock a risk-free profit.",
        "Crypto withdrawal is frozen. Pay a tax fee today to release your balance.",
        "Telegram group offers guaranteed returns if you deposit before midnight.",
        "Investment platform requests your wallet seed phrase to verify your account.",
    ]),
    ("marketplace", "Marketplace buyer", "Fake marketplace transaction", [
        "A buyer sent a payment link. Enter your card details and OTP now to receive funds.",
        "Marketplace courier needs a small insurance fee today before pickup.",
        "Buyer overpaid. Transfer the difference back immediately to confirm the sale.",
        "To receive payment, sign in to your bank through this link and approve the OTP.",
        "A buyer asks you to move the conversation to Telegram and pay a verification deposit.",
    ]),
    ("refund", "Fake e-commerce refund", "E-commerce refund request", [
        "Your online order refund is ready. Pay S$2 verification fee today at http://refund-check.test",
        "Store support: confirm card number and OTP now to process your refund.",
        "Delivery failed. A refund is pending; enter your password at http://order-refund.test",
        "You won a shopping voucher. Pay a small handling fee today to claim it.",
        "An online store asks for your Singpass login to release a refund immediately.",
    ]),
]

REGIONS = ["Singapore-wide", "Central", "East", "North", "Northeast", "West"]


def seed_reports() -> int:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        existing = db.scalar(select(ScamReport.id).where(ScamReport.is_seed.is_(True)).limit(1))
        if existing:
            return 0
        inserted = 0
        for category, brand, title_prefix, messages in CAMPAIGNS:
            for index, content in enumerate(messages):
                result = analyze_text(content)
                db.add(ScamReport(
                    title=f"{title_prefix}: {content[:72].rstrip()}…",
                    content=content,
                    category=category,
                    campaign_key=f"{category}:{brand.lower().replace(' ', '-')}",
                    region=REGIONS[(inserted + index) % len(REGIONS)],
                    impersonated_brand=brand,
                    url=next((part for part in content.split() if part.startswith("http")), None),
                    score=result["score"],
                    risk_level=result["level"],
                    is_seed=True,
                ))
                inserted += 1
        # Add five fictional tech-support and five phishing variants to make 60.
        extra = [
            ("tech-support", "Fake support", "Computer infected: call our support number now and pay for a repair subscription."),
            ("tech-support", "Fake support", "A pop-up says my device is blocked. It asks me to install remote support software."),
            ("tech-support", "Fake support", "Support agent requests remote access and a bank transfer to fix my laptop immediately."),
            ("tech-support", "Fake support", "Your phone has a virus. Call this number now and provide your account password."),
            ("tech-support", "Fake support", "Caller claims to be technical support and asks for an OTP to cancel a payment."),
            ("phishing", "Account phishing", "Your account is blocked today. Confirm your password and verification code at http://account-check.test"),
            ("phishing", "Account phishing", "Security notice: sign in now to prevent closure at http://verify-account.test"),
            ("phishing", "Account phishing", "Update your Singpass details today using this link to avoid suspension."),
            ("phishing", "Account phishing", "A parcel message asks for my password and card number before delivery."),
            ("phishing", "Account phishing", "Urgent: verify your email and OTP at http://mail-login.test"),
        ]
        for category, brand, content in extra:
            result = analyze_text(content)
            db.add(ScamReport(title=f"{brand}: {content[:72]}…", content=content, category=category,
                              campaign_key=f"{category}:{brand.lower().replace(' ', '-')}",
                              region=REGIONS[inserted % len(REGIONS)], impersonated_brand=brand,
                              url=next((part for part in content.split() if part.startswith("http")), None),
                              score=result["score"], risk_level=result["level"], is_seed=True))
            inserted += 1
        db.commit()
        return inserted


if __name__ == "__main__":
    print(f"Seeded {seed_reports()} synthetic reports (existing seed data is preserved).")
