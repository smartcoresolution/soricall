import os


# Application tests intentionally use an isolated SQLite file. Development and
# production runtimes require their own PostgreSQL databases.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/soricall-api-tests.db")


def pytest_sessionstart() -> None:
    from app.core.database import Base, engine
    from app import models  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
