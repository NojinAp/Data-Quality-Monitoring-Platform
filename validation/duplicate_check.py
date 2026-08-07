import sys
from pathlib import Path
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import engine


def duplicate_check(table_name: str, column_name: str):
    """
    Check for duplicate values in a specified column of a table.
    """
    result = {}
    status = "PASSED"

    result["check_name"] = f"duplicate_check for {column_name}"
    result["dataset"] = table_name

    with engine.connect() as conn:
        duplicate_rows = conn.execute(
            text(
                f"SELECT {column_name}, COUNT(*) as count FROM {table_name}  WHERE {column_name} IS NOT NULL GROUP BY {column_name} HAVING COUNT(*) > 1"
            )
        )
        duplicates = duplicate_rows.fetchall()
        duplicate_values = len(duplicates)
        duplicate_count = sum(row[1] - 1 for row in duplicates)

    if duplicate_count > 0:
        status = "FAILED"
        result["duplicates"] = [
            {"value": row[0], "count": row[1]} for row in duplicates
        ]

    result["failed_rows"] = duplicate_count
    result["status"] = status

    print(f"Number of duplicate values in {column_name}: {duplicate_count}")

    return result
