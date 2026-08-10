import sys
import yaml
from fastapi import FastAPI
from pathlib import Path
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import engine

app = FastAPI()

PROJECT_ROOT = Path(__file__).parent.parent

with open(PROJECT_ROOT / "config" / "checks.yaml") as f:
    data = yaml.safe_load(f)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Data Quality API"}


@app.get("/quality-report")
def read_quality_report():
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT * FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY check_name ORDER BY run_timestamp DESC) AS rn FROM quality_results) ranked WHERE rn = 1"
            )
        )
        rows = result.fetchall()
    total_checks = len(rows)
    failed_checks = sum(1 for row in rows if row.status == "FAILED")
    passed_checks = total_checks - failed_checks
    quality_score = (
        round((passed_checks / total_checks) * 100) if total_checks > 0 else 0
    )
    return {
        "total_checks": total_checks,
        "failed_checks": failed_checks,
        "passed_checks": passed_checks,
        "quality_score": quality_score,
    }
    
@app.get("/pipeline-status")
def read_pipeline_status():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT TOP 1 * FROM pipeline_runs ORDER BY started_at DESC"))
        row = result.fetchone()
    return {
        "status": row.status if row else "UNKNOWN",
        "records_processed": row.records_processed if row else 0,
        "started_at": row.started_at if row else None,
        "finished_at": row.finished_at if row else None,
        "duration_seconds": row.duration_seconds if row else 0,
    }
