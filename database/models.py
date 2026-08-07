"""
Design principle: raw_* tables are intentionally PERMISSIVE (no NOT NULL,
no uniqueness constraints on business keys like order_id/customer_id).

Each raw table uses a surrogate primary key (`id`, autoincrement) instead
of the source system's ID, specifically because the source ID (order_id,
customer_id, etc.) is not guaranteed unique in the raw data.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)


class RawCustomer(Base):
    __tablename__ = "raw_customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, nullable=True)       # nullable: CSV can have bad rows
    name = Column(String(200), nullable=True)
    country = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)         # source data has ~3% missing
    created_date = Column(Date, nullable=True)
    loaded_at = Column(DateTime, default=utcnow)        # when this row entered the DB


class RawProduct(Base):
    __tablename__ = "raw_products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, nullable=True)
    category = Column(String(100), nullable=True)
    size = Column(String(10), nullable=True)
    price = Column(Numeric(10, 2), nullable=True)       # source data has ~2% negative/zero
    supplier = Column(String(100), nullable=True)        # source data has ~2% missing
    loaded_at = Column(DateTime, default=utcnow)


class RawOrder(Base):
    __tablename__ = "raw_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, nullable=True)            # NOT unique, duplicates expected
    customer_id = Column(Integer, nullable=True)          # source data has ~2% missing
    product_id = Column(Integer, nullable=True)
    quantity = Column(Integer, nullable=True)              # source data has invalid <=0
    amount = Column(Numeric(10, 2), nullable=True)
    order_date = Column(Date, nullable=True)                # source data has ~1% future dates
    discount = Column(Numeric(5, 2), nullable=True)          # schema drift: only in later rows
    loaded_at = Column(DateTime, default=utcnow)


class RawInventory(Base):
    __tablename__ = "raw_inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, nullable=True)
    warehouse = Column(String(100), nullable=True)         # source data has ~1% missing
    stock_quantity = Column(Integer, nullable=True)          # source data has ~2% negative
    loaded_at = Column(DateTime, default=utcnow)


class QualityResult(Base):
    """
    One row per validation check run against one dataset.
    Designed for "failed checks in the last 7 days" / "pass rate by dataset over time" style queries.
    """
    __tablename__ = "quality_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset = Column(String(100), nullable=False)          # e.g. "orders"
    check_name = Column(String(100), nullable=False)         # e.g. "null_check"
    status = Column(String(20), nullable=False)                # "PASSED" / "FAILED"
    failed_rows = Column(Integer, nullable=False, default=0)
    run_timestamp = Column(DateTime, default=utcnow)


class PipelineRun(Base):
    """
    One row per end-to-end pipeline execution (what /pipeline-status
    reads from). A single pipeline run produces many quality_results rows (one per check).
    """
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(20), nullable=False)               # "SUCCESS" / "FAILED"
    records_processed = Column(Integer, nullable=True)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Numeric(10, 2), nullable=True)