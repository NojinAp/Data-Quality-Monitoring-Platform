from pathlib import Path
import yaml
import sys
from database.models import QualityResult, PipelineRun, utcnow
from validation.business_rules import business_rule_check
from validation.duplicate_check import duplicate_check
from validation.null_check import null_check
from database.connection import engine, SessionLocal

sys.path.insert(0, str(Path(__file__).parent))

PROJECT_ROOT = Path(__file__).parent

session = SessionLocal()

with open(PROJECT_ROOT / "config" / "checks.yaml") as f:
    data = yaml.safe_load(f)

CHECK_FUNCTIONS = {
    "null_check": null_check,
    "duplicate_check": duplicate_check,
    "business_rule_check": business_rule_check,
}

started_at = utcnow()

for entry in data:
    check_function = CHECK_FUNCTIONS[entry["check_type"]]

    if entry["check_type"] == "business_rule_check":
        result = check_function(entry["table"], entry["column"], entry["rule"])
    else:
        result = check_function(entry["table"], entry["column"])

    new_row = QualityResult(
        dataset=result["dataset"],
        check_name=result["check_name"],
        status=result.get("status", "UNKNOWN"),
        failed_rows=result.get("failed_rows", 0),
    )
    session.add(new_row)

finished_at = utcnow()

duration_seconds = (finished_at - started_at).total_seconds()

status = "SUCCESS"

try:
    session.commit()
except Exception as e:
    session.rollback()
    session.flush()
    status = "FAILED"


with engine.connect() as conn:
    from sqlalchemy import text

    tables = {entry["table"] for entry in data}
    total_rows = 0
    for table_name in tables:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
        total_rows += count
    print(tables)
    print(total_rows)

new_row = PipelineRun(
    status=status,
    records_processed=total_rows,
    started_at=started_at,
    finished_at=finished_at,
    duration_seconds=duration_seconds,
)

session.add(new_row)

try:
    session.commit()
except Exception as e:
    session.rollback()
    session.flush()
