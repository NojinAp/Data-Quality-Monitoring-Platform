"""
Database connection for Azure SQL 
Requires only: pip install sqlalchemy pymssql python-dotenv
"""

import os
import urllib.parse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SERVER = os.environ.get("AZURE_SQL_SERVER")
DATABASE = os.environ.get("AZURE_SQL_DB")
USERNAME = os.environ.get("AZURE_SQL_USER")
PASSWORD = os.environ.get("AZURE_SQL_PASSWORD")


def build_connection_string() -> str:
    if not all([SERVER, DATABASE, USERNAME, PASSWORD]):
        raise RuntimeError(
            "Missing one or more required env vars: "
            "AZURE_SQL_SERVER, AZURE_SQL_DB, AZURE_SQL_USER, AZURE_SQL_PASSWORD. "
            "Check your .env file."
        )

    quoted_password = urllib.parse.quote_plus(PASSWORD)

    return (
        f"mssql+pymssql://{USERNAME}:{quoted_password}@{SERVER}:1433/{DATABASE}"
    )


# echo=True prints every SQL statement SQLAlchemy runs
engine = create_engine(build_connection_string(), echo=True) if all(
    [SERVER, DATABASE, USERNAME, PASSWORD]
) else None

SessionLocal = sessionmaker(bind=engine) if engine else None


def get_session():
    if SessionLocal is None:
        raise RuntimeError("Engine not initialized. Check your .env values.")
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


if __name__ == "__main__":
    from models import Base
    from sqlalchemy import text

    print(f"Connecting to {SERVER}/{DATABASE} as {USERNAME}...")
    Base.metadata.create_all(engine)
    print("Tables created (or already existed).")

    with engine.connect() as conn:
        result = conn.execute(text("SELECT @@VERSION"))
        print("Connection test OK:", result.fetchone()[0][:60], "...")