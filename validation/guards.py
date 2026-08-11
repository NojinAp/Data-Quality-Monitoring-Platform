"""
Guards against SQL injection in the check functions by validating that
table_name/column_name refer to real tables/columns before they're ever
interpolated into a SQL string.

Uses Base.metadata as the source of truth, so it can never drift out of
sync with the actual schema defined in models.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.models import Base


def validate_identifier(table_name: str, column_name: str | None = None):
    """
    Raises ValueError if table_name isn't a real table, or if column_name
    isn't a real column on that table.
    """
    if table_name not in Base.metadata.tables:
        raise ValueError(f"Unknown table: {table_name!r}")

    if column_name is not None:
        valid_columns = Base.metadata.tables[table_name].columns.keys()
        if column_name not in valid_columns:
            raise ValueError(f"Unknown column: {column_name!r} on table {table_name!r}")