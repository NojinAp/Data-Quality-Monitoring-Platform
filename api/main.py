import sys
from pathlib import Path

import yaml
from fastapi import FastAPI
from sqlalchemy import text

from run_checks import CHECK_FUNCTIONS

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
        result = conn.execute(
            text("SELECT TOP 1 * FROM pipeline_runs ORDER BY started_at DESC")
        )
        row = result.fetchone()
    return {
        "status": row.status if row else "UNKNOWN",
        "records_processed": row.records_processed if row else 0,
        "started_at": row.started_at if row else None,
        "finished_at": row.finished_at if row else None,
        "duration_seconds": row.duration_seconds if row else 0,
    }


DATASET_TO_TABLE = {
    "customers": "raw_customers",
    "products": "raw_products",
    "orders": "raw_orders",
    "inventory": "raw_inventory",
}


@app.post("/validate/{dataset}")
def validate_dataset(dataset: str):
    table_name = DATASET_TO_TABLE.get(dataset)
    if not table_name:
        return {"error": f"Unknown dataset: {dataset}"}

    matching_checks = [entry for entry in data if entry["table"] == table_name]

    results = []
    for entry in matching_checks:
        check_function = CHECK_FUNCTIONS[entry["check_type"]]

        if entry["check_type"] == "business_rule_check":
            result = check_function(entry["table"], entry["column"], entry["rule"])
        else:
            result = check_function(entry["table"], entry["column"])

        results.append(result)

    with engine.connect() as conn:
        for result in results:
            conn.execute(
                text(
                    "INSERT INTO quality_results (dataset, check_name, status, failed_rows, run_timestamp) VALUES (:dataset, :check_name, :status, :failed_rows, CURRENT_TIMESTAMP)"
                ),
                {
                    "dataset": result["dataset"],
                    "check_name": result["check_name"],
                    "status": result.get("status", "UNKNOWN"),
                    "failed_rows": result.get("failed_rows", 0),
                },
            )
        conn.commit()

    return {"dataset": dataset, "checks_run": len(results), "results": results}
