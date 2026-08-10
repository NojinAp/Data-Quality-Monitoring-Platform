"""
Tests for the FastAPI app. Uses TestClient, which calls the app directly
in-process (no need for uvicorn to be running separately) but still hits
the real Azure SQL database through the app's own engine/session.
"""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_quality_report_shape():
    response = client.get("/quality-report")
    assert response.status_code == 200
    body = response.json()
    for key in ("total_checks", "failed_checks", "passed_checks", "quality_score"):
        assert key in body
    assert body["total_checks"] == 11  # one row per unique check_name
    assert 0 <= body["quality_score"] <= 100


def test_pipeline_status_shape():
    response = client.get("/pipeline-status")
    assert response.status_code == 200
    body = response.json()
    for key in ("status", "records_processed", "started_at", "finished_at", "duration_seconds"):
        assert key in body
    assert body["status"] in ("SUCCESS", "FAILED", "UNKNOWN")


def test_validate_unknown_dataset_returns_error():
    response = client.post("/validate/not_a_real_dataset")
    assert response.status_code == 200  # endpoint returns 200 with an "error" key
    assert "error" in response.json()


def test_validate_known_dataset_runs_checks():
    """This writes new rows to quality_results.
    Uses 'inventory' since it's the smallest dataset (fewest checks) to keep test runs light."""
    response = client.post("/validate/inventory")
    assert response.status_code == 200
    body = response.json()
    assert body["dataset"] == "inventory"
    assert body["checks_run"] > 0
    assert len(body["results"]) == body["checks_run"]