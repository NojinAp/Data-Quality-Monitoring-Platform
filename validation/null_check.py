import sys
from pathlib import Path

from sqlalchemy import text
from validation.guards import validate_identifier

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import engine


def null_check(table_name: str, column_name: str):
    """
    Check for null values in a specified column of a table.
    """
    validate_identifier(table_name, column_name)

    result = {}
    status = "PASSED"

    result["check_name"] = f"null_check for {column_name}"
    result["dataset"] = table_name

    with engine.connect() as conn:
        null_rows = conn.execute(
            text(f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} IS NULL")
        )
        row_count = null_rows.scalar()

    if row_count > 0:
        status = "FAILED"

    result["failed_rows"] = row_count
    result["status"] = status

    print(f"Number of rows with null {column_name}: {row_count}")

    return result
