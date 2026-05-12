# Architecture — Project 9.7 Data Quality Validation

## Quality Gate in Pipeline

```
Glue ETL Job completes (SUCCEEDED)
    │
    │ EventBridge rule triggers
    ▼
Lambda: handson-data-quality-check
    │
    ├── Load processed Parquet from S3
    ├── Run Great Expectations suite
    │   ├── Row count > 0
    │   ├── order_id: not null, unique
    │   ├── amount: > 0, < 10000
    │   ├── product: in known list (99%)
    │   └── order_date: valid format
    │
    ├── PASS → pipeline continues (dbt runs next)
    │
    └── FAIL → SNS alert → email
              → pipeline stops
              → bad data quarantined
```

## Fail Fast Principle

```
Without quality gates:
  Bad data → processed → loaded to warehouse → wrong dashboards
  Discovery: weeks later when business notices wrong numbers
  Fix: expensive data cleanup + reprocessing

With quality gates:
  Bad data → quality check FAILS → pipeline stops
  Discovery: immediately (same day)
  Fix: fix source data, re-run pipeline
```

## Great Expectations Concepts

```
Expectation Suite:
  Collection of expectations for a dataset
  Stored as JSON, version-controlled

Expectation:
  A testable assertion about data
  expect_column_values_to_not_be_null("order_id")

Validation Result:
  Pass/fail for each expectation
  Statistics: % passing, failing examples

Data Docs:
  Auto-generated HTML report
  Share with data consumers
```
