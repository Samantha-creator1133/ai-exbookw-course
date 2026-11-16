"""Check that the Neon PostgreSQL database is reachable."""

import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def get_database_url() -> str | None:
    """Read DATABASE_URL from the environment or the project-root .env file."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url.strip().strip("\"'")

    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        return None

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip().strip("\"'")

    return None


def main() -> int:
    database_url = get_database_url()
    if not database_url:
        print("Not OK")
        return 1

    engine = None
    try:
        url = make_url(database_url)
        if url.drivername in {"postgres", "postgresql"}:
            url = url.set(drivername="postgresql+psycopg")

        engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10},
        )
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        print("OK")
        return 0
    except Exception:
        print("Not OK")
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
