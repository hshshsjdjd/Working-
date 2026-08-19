"""Create or promote an admin user.

Usage:
    python -m scripts.create_admin <email> <password>

If the user exists, they are promoted to admin and their password is reset.
The first user to register through the API also becomes an admin automatically.
"""
from __future__ import annotations

import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models import User, UserSettings
from app.security import hash_password


def main(email: str, password: str) -> None:
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters")
    email = email.lower().strip()
    db = SessionLocal()
    try:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is None:
            user = User(email=email, password_hash=hash_password(password), role="admin")
            db.add(user)
            db.flush()
            db.add(UserSettings(user_id=user.id, theme="amoled"))
            print(f"Created admin user {email}")
        else:
            user.role = "admin"
            user.password_hash = hash_password(password)
            user.is_active = True
            print(f"Promoted {email} to admin and reset password")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python -m scripts.create_admin <email> <password>")
    main(sys.argv[1], sys.argv[2])
