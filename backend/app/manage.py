"""Small local admin helper: python -m app.manage promote <email> <role>."""

import sys
from sqlalchemy import select

from .database import SessionLocal
from .models import AuditLog, User


def main() -> None:
    if len(sys.argv) != 4 or sys.argv[1] != "promote":
        raise SystemExit("Usage: python -m app.manage promote <email> <moderator|admin>")
    email, role = sys.argv[2].lower(), sys.argv[3]
    if role not in {"moderator", "admin"}: raise SystemExit("Role must be moderator or admin")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if not user: raise SystemExit("Create the account in the app first, then run this command.")
        user.role = role
        db.add(AuditLog(actor_id=user.id, action="user.role_bootstrap", target_type="user", target_id=user.id, detail=f"Locally promoted to {role}"))
        db.commit()
        print(f"{email} is now {role}. Sign in again to refresh the role claim.")


if __name__ == "__main__": main()
