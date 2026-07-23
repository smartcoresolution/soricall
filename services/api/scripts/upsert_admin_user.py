#!/usr/bin/env python3
"""Create or update a SoriCall administrator without storing a plaintext password."""

from __future__ import annotations

import argparse
import getpass
import os

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import User


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admin-id", required=True)
    parser.add_argument("--password", default=os.getenv("SORICALL_ADMIN_BOOTSTRAP_PASSWORD", ""))
    parser.add_argument("--display-name", default="SoriCall 관리자")
    args = parser.parse_args()
    admin_id = args.admin_id.strip().lower()
    password = args.password or getpass.getpass("Admin password: ")
    if len(password) < 8:
        parser.error("--password must contain at least 8 characters")

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == admin_id))
        if user is None:
            user = User(email=admin_id, display_name=args.display_name, role="ADMIN")
            db.add(user)
        user.display_name = args.display_name
        user.role = "ADMIN"
        user.password_hash = hash_password(password)
        db.commit()
        print(f"administrator is ready: {admin_id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
