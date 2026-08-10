"""
Tests for null_check, duplicate_check, business_rule_check.
These are integration tests against Azure SQL data.
"""

from validation.null_check import null_check
from validation.duplicate_check import duplicate_check
from validation.business_rules import business_rule_check


# null_check
def test_null_check_returns_expected_shape():
    result = null_check("raw_customers", "email")
    assert set(result.keys()) == {"check_name", "dataset", "failed_rows", "status"}


def test_null_check_detects_known_failures():
    result = null_check("raw_customers", "email")
    assert result["failed_rows"] == 60
    assert result["status"] == "FAILED"


def test_null_check_customer_id_on_orders():
    result = null_check("raw_orders", "customer_id")
    assert result["failed_rows"] == 404
    assert result["status"] == "FAILED"


def test_null_check_supplier_on_products():
    result = null_check("raw_products", "supplier")
    assert result["failed_rows"] == 6


def test_null_check_warehouse_on_inventory():
    result = null_check("raw_inventory", "warehouse")
    assert result["failed_rows"] == 12


# duplicate_check
def test_duplicate_check_finds_duplicates():
    result = duplicate_check("raw_orders", "order_id")
    assert result["failed_rows"] == 200
    assert result["status"] == "FAILED"
    assert "duplicates" in result


def test_duplicate_check_passes_when_unique():
    result = duplicate_check("raw_products", "product_id")
    assert result["failed_rows"] == 0
    assert result["status"] == "PASSED"


def test_duplicate_check_excludes_nulls():
    """Regression test: nulls should never be reported as duplicates,
    since a null customer_id is null_check's job, not duplicate_check's."""
    result = duplicate_check("raw_orders", "customer_id")
    dup_values = [d["value"] for d in result.get("duplicates", [])]
    assert None not in dup_values


# business_rule_check
def test_business_rule_price_non_negative():
    result = business_rule_check("raw_products", "price", "price >= 0")
    assert result["failed_rows"] == 6
    assert result["status"] == "FAILED"


def test_business_rule_quantity_positive():
    result = business_rule_check("raw_orders", "quantity", "quantity > 0")
    assert result["failed_rows"] == 303
    assert result["status"] == "FAILED"


def test_business_rule_stock_quantity_non_negative():
    result = business_rule_check(
        "raw_inventory", "stock_quantity", "stock_quantity >= 0"
    )
    assert result["failed_rows"] == 24
    assert result["status"] == "FAILED"


def test_business_rule_order_date_not_future():
    """order_date failures drift downward over time as 'today' moves
    forward past previously-future dates."""
    result = business_rule_check(
        "raw_orders", "order_date", "order_date <= CAST(GETDATE() AS DATE)"
    )
    assert 0 <= result["failed_rows"] <= 200
    assert result["status"] in ("PASSED", "FAILED")
