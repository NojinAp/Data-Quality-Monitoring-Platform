from pathlib import Path
import yaml
import sys

sys.path.insert(0, str(Path(__file__).parent))

from database.models import QualityResult
from validation.business_rules import business_rule_check
from validation.duplicate_check import duplicate_check
from validation.null_check import null_check
from database.connection import SessionLocal

PROJECT_ROOT = Path(__file__).parent

session = SessionLocal()

with open(PROJECT_ROOT / "config" / "checks.yaml") as f:
    data = yaml.safe_load(f)

CHECK_FUNCTIONS = {
    "null_check": null_check,
    "duplicate_check": duplicate_check,
    "business_rule_check": business_rule_check
}

for entry in data:
    check_function = CHECK_FUNCTIONS[entry["check_type"]]

    if entry["check_type"] == "business_rule_check":
        result = check_function(entry["table"], entry["column"], entry["rule"])
    else:
        result = check_function(entry["table"], entry["column"])
        
    new_row = QualityResult(dataset = result["dataset"], check_name = result["check_name"], status = result.get("status", "UNKNOWN"), failed_rows = result.get("failed_rows", 0))
    session.add(new_row)
    
session.commit()