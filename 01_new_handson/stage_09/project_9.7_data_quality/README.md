# Project 9.7 — Data Quality Validation

## What This Does
Implements automated data quality checks using Great Expectations and AWS Deequ. Validates data at every stage of the pipeline — catching bad data before it reaches analytics.

## Tools Used
| Tool | Language | Best For |
|------|----------|---------|
| Great Expectations | Python | Flexible, rich reporting, data docs |
| AWS Deequ | Scala/PySpark | Large datasets on EMR/Glue |
| dbt tests | SQL | Simple checks in dbt models |

## Checks Implemented
| Check | Type | Threshold |
|-------|------|-----------|
| Row count > 0 | Completeness | Fail if 0 rows |
| order_id not null | Completeness | 100% |
| order_id unique | Uniqueness | 100% |
| amount > 0 | Validity | 100% |
| order_date in range | Validity | 100% |
| product in known list | Validity | 99% (allow 1% unknown) |
| No duplicate orders | Consistency | 100% |

## How to Run
```bash
pip install great-expectations
python src/validate_orders.py
```

## Lessons Learned
- Data quality is a pipeline concern, not just a reporting concern
- Fail fast: catch bad data at ingestion, not at the dashboard
- Expectations as code: version-controlled, reviewable, testable
- Data docs: auto-generated HTML report — share with data consumers
- Quarantine bad records: don't drop them — move to a quarantine zone for investigation

## Code

### `src/validate_orders.py` — Great Expectations data quality checks

```bash
pip install great-expectations pyarrow pandas s3fs

# Create sample data with quality issues (for testing)
python -c "
import pandas as pd
df = pd.DataFrame({
    'order_id': ['ORD-001', 'ORD-002', None, 'ORD-001'],
    'amount': [29.99, -5.00, 49.99, 19.99],
    'product': ['Widget A', 'Widget B', 'Unknown', 'Widget C']
})
df.to_parquet('/tmp/test_orders.parquet', index=False)
"

# Run validation (expects FAILED — shows which checks fail)
python src/validate_orders.py

# Fix data and re-run (expects PASSED)
```

Checks: row count > 0, order_id not null + unique, amount > 0, product in known list (99%), order_date valid format.
