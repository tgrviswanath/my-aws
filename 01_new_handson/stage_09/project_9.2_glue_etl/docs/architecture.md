# Architecture — Project 9.2 Glue ETL Pipeline

## Complete Pipeline Flow

```
S3 bucket: handson-data-lake-{ACCOUNT_ID}
│
├── raw/orders/                        ← INPUT (from Project 9.1 crawler)
│   └── year=2024/month=01/day=15/
│       └── orders.csv
│
├── scripts/etl_job.py                 ← uploaded by Terraform (aws_s3_object.etl_script)
│
└── processed/                         ← OUTPUT (written by etl_job.py)
    ├── orders/                        ← individual clean orders
    │   └── year=2024/month=01/
    │       └── part-00000.parquet
    └── orders_daily/                  ← daily aggregates by product
        └── year=2024/month=01/
            └── part-00000.parquet
```

## ETL Job Execution Flow

```
Glue Job: handson-etl-job
  │
  ├── Parameters (--key value format, passed from Terraform default_arguments)
  │   ├── --source_bucket   = handson-data-lake-{ACCOUNT_ID}
  │   ├── --target_bucket   = handson-data-lake-{ACCOUNT_ID}  (same bucket)
  │   ├── --database_name   = handson_data_lake
  │   ├── --TempDir         = s3://handson-data-lake-{ACCOUNT_ID}/temp/
  │   ├── --job-bookmark-option = job-bookmark-enable
  │   └── --enable-metrics  = true
  │
  ├── EXTRACT
  │   └── glueContext.create_dynamic_frame.from_options()
  │       → reads s3://{source_bucket}/raw/orders/ (recursive)
  │       → format: CSV with header
  │       → transformation_ctx: "raw_orders"  ← bookmark key
  │
  ├── TRANSFORM (Spark DataFrame operations)
  │   ├── dropna(subset=["order_id", "amount"])     ← remove incomplete rows
  │   ├── cast amount → DoubleType                  ← fix data types
  │   ├── cast order_date → DateType (yyyy-MM-dd)   ← fix dates
  │   ├── add year, month, day columns              ← partition keys
  │   ├── upper(trim(product))                      ← standardize text
  │   ├── add processed_at = current_timestamp()    ← audit column
  │   ├── add etl_job = JOB_NAME                   ← audit column
  │   └── dropDuplicates(["order_id"])              ← remove duplicates
  │
  ├── AGGREGATE (df_daily)
  │   └── groupBy(year, month, day, product)
  │       → order_count, total_revenue, avg_order_value, unique_customers
  │
  └── LOAD
      ├── df_clean → s3://{target_bucket}/processed/orders/
      │   partitionBy("year", "month")   ← NOT day — month-level partitions
      │   format: parquet, mode: overwrite
      │
      └── df_daily → s3://{target_bucket}/processed/orders_daily/
          partitionBy("year", "month")
          format: parquet, mode: overwrite
      │
      └── job.commit()  ← saves bookmark — REQUIRED, do not remove
```

## Job Bookmark Behavior

```
Without bookmark (job-bookmark-option = job-bookmark-disable):
  Run 1: reads raw/orders/year=2024/month=01/  → processes 100 rows
  Run 2: reads raw/orders/year=2024/month=01/  → reprocesses same 100 rows!

With bookmark enabled (default in this project):
  Run 1: reads raw/orders/year=2024/month=01/  → bookmark saved after job.commit()
  Run 2: reads only NEW files since last run   → processes 0 rows (no new data)
  Run 3: NEW file raw/orders/year=2024/month=02/ added → processes only new file
```

## Terraform Resources

```
aws_s3_object.etl_script
  → uploads src/etl_job.py → s3://{data_lake_bucket}/scripts/etl_job.py
  → etag = MD5 of file — auto re-uploads if script changes

aws_glue_job.etl
  → name:        handson-etl-job
  → type:        glueetl (Spark, NOT pythonshell)
  → version:     4.0 (Spark 3.3, Python 3.10)
  → workers:     2 × G.1X (4 vCPU, 16 GB each)
  → timeout:     60 minutes (cost protection)
  → max_retries: 1
  → depends_on:  aws_s3_object.etl_script

aws_glue_trigger.daily
  → name:     handson-etl-daily
  → type:     SCHEDULED
  → schedule: cron(0 2 * * ? *)  = 2:00 AM UTC daily
  → enabled:  false by default (CREATED state, not running)
              set enable_trigger = true in terraform.tfvars to activate
```

## Worker Types Reference

| Type | vCPU | Memory | Cost/DPU-hr | Use Case |
|------|------|--------|-------------|---------|
| G.1X | 4 | 16 GB | $0.44 | ✅ Standard ETL (this project) |
| G.2X | 8 | 32 GB | $0.88 | Memory-intensive joins/aggregations |
| G.4X | 16 | 64 GB | $1.76 | Large datasets > 10 GB |
| G.8X | 32 | 128 GB | $3.52 | Very large datasets > 100 GB |

## Output Schema

**processed/orders/ — cleaned individual orders:**
```
order_id      STRING     (deduplicated)
product       STRING     (uppercased, trimmed)
customer_id   STRING     (trimmed)
amount        DOUBLE     (cast from string)
order_date    DATE       (parsed from yyyy-MM-dd)
year          INT        (partition key)
month         INT        (partition key)
day           INT        (column — NOT a partition key at write time)
processed_at  TIMESTAMP  (audit)
etl_job       STRING     (audit — job name)
```

**processed/orders_daily/ — daily aggregates:**
```
year              INT    (partition key)
month             INT    (partition key)
day               INT
product           STRING
order_count       LONG
total_revenue     DOUBLE (rounded to 2 decimals)
avg_order_value   DOUBLE (rounded to 2 decimals)
unique_customers  LONG
```

## Cost Calculation

```
2 workers × G.1X = 2 DPUs
10 minutes run  = 10/60 = 0.167 hours
Cost            = 2 × 0.167 × $0.44 = $0.15 per run

STARTING state is also billed — Glue charges from worker allocation,
not from when your Python code starts executing (~1-2 min startup overhead)
```

## Data Quality Rules Applied

| Rule | Column | Action |
|------|--------|--------|
| Not null | order_id | Drop row |
| Not null | amount | Drop row |
| Type cast | amount | String → Double |
| Type cast | order_date | String → Date |
| Standardize | product | UPPER(TRIM()) |
| Deduplicate | order_id | Keep first occurrence |

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
