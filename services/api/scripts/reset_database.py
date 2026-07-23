#!/usr/bin/env python3
"""Reset the PostgreSQL database selected by DATABASE_URL."""

import argparse

from app import models  # noqa: F401
from app.core.config import get_settings
from sqlalchemy import text

from app.core.database import Base, engine


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-reset", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    if not args.confirm_reset:
        raise SystemExit("Refusing to reset without --confirm-reset")
    if not settings.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
        raise SystemExit("Refusing to reset a non-PostgreSQL database")
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    if not table_names:
        raise SystemExit("No application tables were discovered")
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
    print(f"Reset completed for APP_ENV={settings.app_env}")


if __name__ == "__main__":
    main()
