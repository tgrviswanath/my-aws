# Architecture — Project 9.7 Data Quality Validation

## Resources

| Resource | Name | Notes |
|----------|------|-------|
| Lambda | `handson-data-quality-check` | Python 3.11, 300s, 512 MB |
| IAM Role | `handson-quality-lambda-role` | S3 read/write + SNS publish |
| SNS Topic | `handson-data-quality-alerts` | Standard, email subscription |
| EventBridge Rule | `handson-glue-job-success` | Triggers on Glue SUCCEEDED |
| S3 prefix | `data-quality/reports/` | Validation JSON reports |
| S3 prefix | `quarantine/orders/` | Bad records on failure |

---

## Quality Gate in Pipeline

```
Glue ETL Job: handson-etl-job → state: SUCCEEDED
    │
    │  EventBridge rule matches:
    │  source=aws.glue, detail.state=SUCCEEDED, detail.jobName=handson-etl-job
    │
    ▼
Lambda: handson-data-quality-check
    │  Environment: DATA_LAKE_BUCKET, SNS_TOPIC_ARN
    │
    ├── 1. load_data_from_s3(bucket, "processed/orders/")
    │      → reads all Parquet files → DataFrame
    │
    ├── 2. validate_orders(df) — Great Expectations suite
    │      ├── Completeness: row_count, nulls on 4 columns
    │      ├── Uniqueness:   order_id
    │      ├── Validity:     amount range, product list, date format
    │      └── Statistical:  mean(amount) in range
    │
    ├── PASS (all expectations succeed):
    │      ├── Print: "✅ PASSED | 10/10 | N rows"
    │      ├── Save report to data-quality/reports/TIMESTAMP.json
    │      └── sys.exit(0) → EventBridge records SUCCESS
    │
    └── FAIL (any expectation fails):
           ├── Print: "❌ FAILED | 7/10 | which checks failed"
           ├── sns.publish() → email alert
           ├── Move bad records to quarantine/orders/DATE/
           └── sys.exit(1) → EventBridge records ERROR
```

---

## Validation Suite (10 checks from src/validate_orders.py)

```python
# COMPLETENESS (5)
expect_table_row_count_to_be_between(min_value=1)
expect_column_values_to_not_be_null("order_id")
expect_column_values_to_not_be_null("customer_id")
expect_column_values_to_not_be_null("amount")
expect_column_values_to_not_be_null("order_date")

# UNIQUENESS (1)
expect_column_values_to_be_unique("order_id")

# VALIDITY (3)
expect_column_values_to_be_between("amount", min_value=0.01, max_value=10000.0)
expect_column_values_to_be_in_set("product", value_set=[...], mostly=0.99)
expect_column_values_to_match_strftime_format("order_date", strftime_format="%Y-%m-%d")

# STATISTICAL (1)
expect_column_mean_to_be_between("amount", min_value=10.0, max_value=200.0)
```

---

## Fail-Fast Principle

```
Without quality gates:
  Source → Glue ETL → S3 processed/ → dbt → Redshift → Dashboard
  Bad data discovered: weeks later at dashboard
  Fix cost: data cleanup + reprocessing + stakeholder trust damage

With quality gate (after Glue ETL):
  Source → Glue ETL → ❌ Quality FAILS → STOP → SNS alert
  Bad data discovered: immediately, same pipeline run
  Fix cost: fix source data + re-run ETL (minutes)

Rule: move quality checks as LEFT as possible in the pipeline
```

---

## Great Expectations Concepts

```
Expectation Suite:
  A named collection of expectations
  suite_name = "orders_suite"

Expectation:
  A single testable assertion
  expect_column_values_to_not_be_null("order_id")
  → generates SQL/Python check against the data

mostly= parameter:
  0.99 = 99% of rows must satisfy the expectation
  1.0  = 100% (default, strict)
  Use mostly= for dimensions that may have new valid values

Validation Result:
  Pass if ALL expectations satisfied (or within mostly= threshold)
  For each expectation: success bool + unexpected count + examples

Exit code convention:
  sys.exit(0) = PASS  → Airflow task SUCCESS, CI step passes
  sys.exit(1) = FAIL  → Airflow task FAIL, CI step fails, pipeline stops
```

---

## Quarantine Pattern

```
On FAIL:
  1. Identify rows that violated any expectation
  2. Write those rows to:
     s3://BUCKET/quarantine/orders/YYYY-MM-DD/bad_records.parquet
  3. Write validation report to:
     s3://BUCKET/data-quality/reports/TIMESTAMP.json

On investigation:
  Engineer downloads quarantine Parquet → pandas.read_parquet()
  Sees: order_id=None, amount=-5.00
  Fixes upstream source system
  Deletes quarantine file
  Re-runs Glue ETL → new quality check → PASS → pipeline resumes

Never delete bad records silently — always preserve for audit
```

---

## Airflow Integration

```python
# In Airflow DAG (Project 9.5):
run_glue_etl = GlueJobOperator(task_id="run_glue_etl", ...)

validate_task = BashOperator(
    task_id="validate_data_quality",
    bash_command="python /opt/airflow/src/validate_orders.py",
    # Exit code 1 → BashOperator raises AirflowException → task FAILS
    # → run_dbt_task never starts → bad data blocked from analytics
)

run_dbt_task = PythonOperator(task_id="run_dbt_models", ...)

# Dependency chain:
run_glue_etl >> validate_task >> run_dbt_task
```

---

## Data Quality Tools Comparison

| Tool | Language | Checks | Reports | Scale | Free? |
|------|---------|--------|---------|-------|-------|
| **Great Expectations** | Python | Rich | HTML+JSON | Medium | ✅ |
| dbt tests | SQL | Basic | dbt docs | Small | ✅ |
| AWS Deequ | PySpark | Statistical | Metrics | Large | ✅ |
| Pandas assertions | Python | Ad hoc | None | Small | ✅ |
| Monte Carlo | SaaS | ML-based | Dashboard | Any | ❌ $$$$ |

## Input / Output

### Input
| Type | Description | Example |
|------|-------------|---------|
| AWS Account | Active subscription | IAM user with required permissions |
| Configuration | Service settings | CIDR blocks, instance types, regions |
| Source Data | Application or data files | Docker images, SQL scripts, CSV files |

### Output
| Type | Description | Access |
|------|-------------|--------|
| AWS Resources | Deployed infrastructure | AWS Console or CLI |
| Service Endpoints | HTTP/HTTPS URLs, connection strings | Resource overview |
| CloudWatch Logs | Execution and audit trail | CloudWatch Log groups |
| Metrics | Performance data | CloudWatch Metrics |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| IAM Role | AWS identity for services â€” no static credentials |
| Security Group | Virtual firewall for EC2/RDS â€” stateful |
| VPC | Isolated network â€” your private AWS cloud |
| Region | Geographic AWS datacenter location |
| Availability Zone | Isolated datacenters within a region |
| CloudWatch | AWS monitoring and logging service |
| Free Tier | AWS free usage limits per service per month |
