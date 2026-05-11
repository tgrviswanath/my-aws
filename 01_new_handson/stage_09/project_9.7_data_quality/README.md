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
