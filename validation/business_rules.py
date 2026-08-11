import sys
from pathlib import Path

from sqlalchemy import text

from validation.guards import validate_identifier

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import engine


def business_rule_check(table_name: str, column_name: str, rule: str):
    """
    Check for business rule violations in a specified column of a table.
    """
    validate_identifier(table_name, column_name)

    result = {}
    status = "PASSED"

    result["check_name"] = f"business_rule_check for {column_name} with rule '{rule}'"
    result["dataset"] = table_name

    with engine.connect() as conn:
        violation_rows = conn.execute(
            text(f"SELECT COUNT(*) FROM {table_name} WHERE NOT ({rule})")
        )
        violation_count = violation_rows.scalar()

    if violation_count > 0:
        status = "FAILED"

    result["failed_rows"] = violation_count
    result["status"] = status

    print(f"Number of business rule violations in {column_name}: {violation_count}")

    return result
