# Project 9.2 — AWS Glue ETL
## PySpark Job: CSV Raw Zone → Parquet Processed Zone with Job Bookmarks

---

## Prerequisites Check

- [ ] AWS CLI configured: `aws sts get-caller-identity`
- [ ] IAM permissions: `glue:*`, `s3:*`, `iam:CreateRole`, `logs:*`
- [ ] S3 buckets: raw zone and processed zone
- [ ] Python 3.8+ (for local testing with PySpark)
- [ ] Region: `us-east-1`
- [ ] Glue has no free tier — charges start immediately

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"
DATA_BUCKET="glue-etl-data-${ACCOUNT_ID}"
SCRIPTS_BUCKET="glue-etl-scripts-${ACCOUNT_ID}"
```

---

## Decision Point 1

**AWS Glue ETL vs Lambda ETL — which to use?**

| Factor | Glue ETL ✅ | Lambda ETL ✅ |
|--------|-----------|------------|
| **Data size** | GB to PB | MB to GB (max 10GB tmp) |
| **Processing** | Distributed PySpark | Single-node Python |
| **Runtime** | Up to hours | Max 15 minutes |
| **Startup time** | 2-5 minutes (cold start) | < 1 second |
| **Cost** | $0.44/DPU-hour (min 2 DPU) | $0.20/million requests |
| **Skills needed** | PySpark/Spark | Python |
| **Use for** | Large CSV/JSON/Parquet transforms | Small event-driven transforms |

**Choose Glue when:**
- Processing files > 100 MB
- Joining multiple large datasets
- Complex transformations (dedup, reshape, aggregation)
- Need Glue Catalog integration

**Choose Lambda when:**
- File arrives and is < 50 MB
- Simple field-level transforms
- Need sub-second latency
- Cost matters for tiny files

**Verdict for this project:** Glue ETL ✅ — demonstrates PySpark at scale.

---

## 1. Architecture Overview

```
S3 raw/ zone                    S3 processed/ zone
├── data/2024/01/01/             ├── data/
│   ├── customers_001.csv        │   └── year=2024/month=01/day=01/
│   └── customers_002.csv        │       └── customers.parquet
└── data/2024/01/02/
    └── customers_003.csv

Glue Job (PySpark)
├── DynamicFrame (reads CSV with schema inference)
├── ApplyMapping (rename/type columns)
├── Filter (remove nulls, bad records)
├── DropDuplicates (deduplicate)
├── Write Parquet (partitioned by date)
└── Glue Catalog (auto-update table schema)

Job Bookmark → tracks processed files → prevents reprocessing
```

---

## 2. Create S3 Buckets and Upload Sample Data

```bash
# Create buckets
aws s3 mb s3://${DATA_BUCKET} --region $REGION
aws s3 mb s3://${SCRIPTS_BUCKET} --region $REGION

# Create sample CSV data
cat > /tmp/customers_001.csv << 'EOF'
customer_id,first_name,last_name,email,signup_date,age,revenue
1001,John,Doe,john.doe@example.com,2024-01-15,34,1200.50
1002,Jane,Smith,jane.smith@example.com,2024-01-15,28,850.00
1003,Bob,Johnson,,2024-01-15,45,2100.75
1004,Alice,Brown,alice@example.com,2024-01-16,31,450.25
1001,John,Doe,john.doe@example.com,2024-01-16,34,1200.50
EOF

cat > /tmp/customers_002.csv << 'EOF'
customer_id,first_name,last_name,email,signup_date,age,revenue
1005,Charlie,Wilson,charlie@example.com,2024-01-17,22,300.00
1006,Diana,Prince,diana@example.com,2024-01-17,38,1750.00
1007,Eve,Johnson,eve@example.com,2024-01-17,55,3200.00
EOF

# Upload to S3 raw zone
aws s3 cp /tmp/customers_001.csv \
  s3://${DATA_BUCKET}/raw/customers/2024/01/15/customers_001.csv
aws s3 cp /tmp/customers_002.csv \
  s3://${DATA_BUCKET}/raw/customers/2024/01/17/customers_002.csv

echo "Sample data uploaded"
```

---

## 3. Create Glue IAM Role

```bash
# Create Glue service role
cat > /tmp/glue-trust.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "glue.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role \
  --role-name AWSGlueServiceRoleDefault \
  --assume-role-policy-document file:///tmp/glue-trust.json \
  --description "Glue service role for ETL jobs"

# Attach Glue service policy
aws iam attach-role-policy \
  --role-name AWSGlueServiceRoleDefault \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole

# S3 access policy
cat > /tmp/glue-s3-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket"],
    "Resource": [
      "arn:aws:s3:::${DATA_BUCKET}",
      "arn:aws:s3:::${DATA_BUCKET}/*",
      "arn:aws:s3:::${SCRIPTS_BUCKET}",
      "arn:aws:s3:::${SCRIPTS_BUCKET}/*"
    ]
  }]
}
EOF

aws iam put-role-policy \
  --role-name AWSGlueServiceRoleDefault \
  --policy-name GlueS3Access \
  --policy-document file:///tmp/glue-s3-policy.json
```

---

## 4. Write PySpark ETL Script

```python
# glue_etl_customers.py — Upload to S3 scripts bucket

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql.functions import col, to_date, year, month, dayofmonth

# Get job parameters
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'source_bucket',
    'source_prefix',
    'target_bucket',
    'target_prefix',
    'database_name',
    'table_name'
])

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# ─── EXTRACT ──────────────────────────────────────────────────────────────────
# Read CSV files — Job Bookmark ensures only new files are processed
raw_dyf = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={
        "paths": [f"s3://{args['source_bucket']}/{args['source_prefix']}"],
        "recurse": True,
        "jobBookmarkKeys": ["customer_id"],  # For incremental processing
        "jobBookmarkKeysSortOrder": "asc"
    },
    format="csv",
    format_options={
        "withHeader": True,
        "separator": ",",
        "quoteChar": '"',
        "optimizePerformance": True
    },
    transformation_ctx="raw_dyf"
)

print(f"Records read: {raw_dyf.count()}")
raw_dyf.printSchema()

# ─── TRANSFORM ────────────────────────────────────────────────────────────────
# Step 1: Apply schema mapping (rename + cast types)
mapped_dyf = ApplyMapping.apply(
    frame=raw_dyf,
    mappings=[
        ("customer_id", "string", "customer_id", "int"),
        ("first_name", "string", "first_name", "string"),
        ("last_name", "string", "last_name", "string"),
        ("email", "string", "email", "string"),
        ("signup_date", "string", "signup_date", "string"),
        ("age", "string", "age", "int"),
        ("revenue", "string", "revenue", "double")
    ],
    transformation_ctx="mapped_dyf"
)

# Step 2: Convert to Spark DataFrame for complex transformations
df = mapped_dyf.toDF()

# Step 3: Clean data — filter out records with null email
df_clean = df.filter(col("email").isNotNull() & (col("email") != ""))

# Step 4: Deduplicate on customer_id (keep latest by signup_date)
from pyspark.sql.window import Window
from pyspark.sql.functions import row_number, desc

window = Window.partitionBy("customer_id").orderBy(desc("signup_date"))
df_deduped = df_clean.withColumn("rn", row_number().over(window)) \
                     .filter(col("rn") == 1) \
                     .drop("rn")

# Step 5: Add partition columns
df_partitioned = df_deduped \
    .withColumn("signup_date_parsed", to_date(col("signup_date"), "yyyy-MM-dd")) \
    .withColumn("year", year(col("signup_date_parsed"))) \
    .withColumn("month", month(col("signup_date_parsed"))) \
    .withColumn("day", dayofmonth(col("signup_date_parsed")))

print(f"Records after dedup/clean: {df_partitioned.count()}")
df_partitioned.show(5)

# Step 6: Convert back to DynamicFrame
cleaned_dyf = DynamicFrame.fromDF(df_partitioned, glueContext, "cleaned_dyf")

# ─── LOAD ──────────────────────────────────────────────────────────────────────
# Write as Parquet, partitioned by year/month/day
glueContext.write_dynamic_frame.from_options(
    frame=cleaned_dyf,
    connection_type="s3",
    connection_options={
        "path": f"s3://{args['target_bucket']}/{args['target_prefix']}",
        "partitionKeys": ["year", "month", "day"]
    },
    format="parquet",
    format_options={"compression": "snappy"},
    transformation_ctx="output_dyf"
)

# ─── CATALOG UPDATE ───────────────────────────────────────────────────────────
# Update Glue Catalog table with new partitions
glueContext.write_dynamic_frame.from_catalog(
    frame=cleaned_dyf,
    database=args['database_name'],
    table_name=args['table_name'],
    additional_options={"enableUpdateCatalog": True, "updateBehavior": "UPDATE_IN_DATABASE"}
)

# Commit Job Bookmark — marks processed files as done
job.commit()
print("ETL job completed successfully")
```

```bash
# Upload script to S3
aws s3 cp /tmp/glue_etl_customers.py \
  s3://${SCRIPTS_BUCKET}/scripts/glue_etl_customers.py
```

---

## 5A. Console: Create Glue ETL Job

1. Navigate to **AWS Glue** → **ETL jobs** → **Create job**
2. **Job type**: `Spark script editor` (or Visual editor for drag-drop)
3. **Script editor**: Paste the PySpark script from Section 4
4. **Job details**:
   - **Name**: `customers-csv-to-parquet`
   - **IAM Role**: `AWSGlueServiceRoleDefault`
   - **Glue version**: Glue 4.0 (Spark 3.3)
   - **Language**: Python 3
   - **Worker type**: `G.1X` (4 vCPU, 16 GB) or `Standard` (2 DPU)
   - **Number of workers**: 2 (minimum)
5. **Job parameters** (key/value):
   - `--source_bucket`: `glue-etl-data-ACCOUNT_ID`
   - `--source_prefix`: `raw/customers/`
   - `--target_bucket`: `glue-etl-data-ACCOUNT_ID`
   - `--target_prefix`: `processed/customers/`
   - `--database_name`: `myapp_db`
   - `--table_name`: `customers_processed`
6. **Advanced properties** → **Job bookmark**: Enable
7. Click **Save** → **Run**

---

## 5B. CLI: Create and Run Glue Job

```bash
# Create Glue job
aws glue create-job \
  --name "customers-csv-to-parquet" \
  --role "AWSGlueServiceRoleDefault" \
  --command '{
    "Name": "glueetl",
    "ScriptLocation": "s3://'"$SCRIPTS_BUCKET"'/scripts/glue_etl_customers.py",
    "PythonVersion": "3"
  }' \
  --default-arguments '{
    "--enable-job-insights": "true",
    "--enable-glue-datacatalog": "true",
    "--job-bookmark-option": "job-bookmark-enable",
    "--enable-continuous-cloudwatch-log": "true",
    "--enable-spark-ui": "true",
    "--spark-event-logs-path": "s3://'"$SCRIPTS_BUCKET"'/spark-logs/",
    "--source_bucket": "'"$DATA_BUCKET"'",
    "--source_prefix": "raw/customers/",
    "--target_bucket": "'"$DATA_BUCKET"'",
    "--target_prefix": "processed/customers/",
    "--database_name": "myapp_db",
    "--table_name": "customers_processed"
  }' \
  --glue-version "4.0" \
  --worker-type "G.1X" \
  --number-of-workers 2 \
  --description "CSV to Parquet ETL for customer data"

# Run the job
JOB_RUN_ID=$(aws glue start-job-run \
  --job-name "customers-csv-to-parquet" \
  --query 'JobRunId' \
  --output text)

echo "Job Run ID: $JOB_RUN_ID"

# Monitor job status
watch -n 10 "aws glue get-job-run \
  --job-name customers-csv-to-parquet \
  --run-id $JOB_RUN_ID \
  --query 'JobRun.{State:JobRunState,StartedOn:StartedOn,Duration:ExecutionTime}'"
```

---

## 6. Create Glue Catalog Database and Crawler

```bash
# Create Glue database
aws glue create-database \
  --database-input '{
    "Name": "myapp_db",
    "Description": "MyApp processed data catalog"
  }'

# Create Glue Crawler for processed zone
aws glue create-crawler \
  --name "customers-processed-crawler" \
  --role "AWSGlueServiceRoleDefault" \
  --database-name "myapp_db" \
  --targets '{
    "S3Targets": [{
      "Path": "s3://'"$DATA_BUCKET"'/processed/customers/"
    }]
  }' \
  --schema-change-policy '{
    "UpdateBehavior": "UPDATE_IN_DATABASE",
    "DeleteBehavior": "LOG"
  }' \
  --description "Discover partitions for processed customer data"

# Run crawler
aws glue start-crawler --name "customers-processed-crawler"

# Check crawler status
aws glue get-crawler \
  --name "customers-processed-crawler" \
  --query 'Crawler.{State:State,LastCrawl:LastCrawl}'
```

---

## 7. Query Processed Data with Athena

```bash
# Set Athena workgroup
aws athena create-work-group \
  --name "glue-etl-queries" \
  --configuration '{
    "ResultConfiguration": {
      "OutputLocation": "s3://'"$SCRIPTS_BUCKET"'/athena-results/"
    }
  }'

# Query processed Parquet data
aws athena start-query-execution \
  --query-string "
    SELECT year, month, 
           COUNT(*) as customer_count,
           SUM(revenue) as total_revenue,
           AVG(age) as avg_age
    FROM myapp_db.customers_processed
    GROUP BY year, month
    ORDER BY year, month" \
  --work-group "glue-etl-queries" \
  --query-execution-context 'Database=myapp_db'
```

---

## 8. Verify Job Bookmark (Incremental Processing)

```bash
# Add new data file to raw zone
cat > /tmp/customers_003.csv << 'EOF'
customer_id,first_name,last_name,email,signup_date,age,revenue
1008,Frank,Castle,frank@example.com,2024-01-20,40,5000.00
1009,Grace,Hopper,grace@example.com,2024-01-20,78,12000.00
EOF

aws s3 cp /tmp/customers_003.csv \
  s3://${DATA_BUCKET}/raw/customers/2024/01/20/customers_003.csv

# Run job again — bookmark ensures only customers_003.csv is processed
JOB_RUN_ID2=$(aws glue start-job-run \
  --job-name "customers-csv-to-parquet" \
  --query 'JobRunId' \
  --output text)

echo "Second run: $JOB_RUN_ID2"
# Only the new file should be processed — verify with CloudWatch logs
```

---

## 9. Monitor with CloudWatch and Glue Job Insights

```bash
# Get CloudWatch log group for Glue job
aws logs describe-log-groups \
  --log-group-name-prefix "/aws-glue/jobs"

# View job output logs
aws logs filter-log-events \
  --log-group-name "/aws-glue/jobs/output" \
  --filter-pattern "Records read"

# Get job metrics
aws glue get-job-runs \
  --job-name "customers-csv-to-parquet" \
  --query 'JobRuns[0].{State:JobRunState,Duration:ExecutionTime,DPUSeconds:DPUSeconds}'

# List all runs
aws glue get-job-runs \
  --job-name "customers-csv-to-parquet" \
  --query 'JobRuns[*].{Id:Id,State:JobRunState,Start:StartedOn,Duration:ExecutionTime}'
```

---

## 10. Verify Complete Setup

```bash
echo "=== Glue ETL Verification ==="

# 1. Job exists
aws glue get-job --job-name "customers-csv-to-parquet" \
  --query 'Job.{Name:Name,Role:Role,Version:GlueVersion}'

# 2. Last run succeeded
aws glue get-job-runs \
  --job-name "customers-csv-to-parquet" \
  --max-results 1 \
  --query 'JobRuns[0].{State:JobRunState,Duration:ExecutionTime}'

# 3. Output files in S3
aws s3 ls s3://${DATA_BUCKET}/processed/customers/ --recursive | head -10

# 4. Glue catalog has table
aws glue get-tables --database-name "myapp_db" \
  --query 'TableList[].{Name:Name,Type:TableType}'

# 5. Bookmark state
aws glue get-job-bookmark --job-name "customers-csv-to-parquet" \
  --query 'JobBookmarkEntry.{Active:Active,Attempt:Attempt}'

echo "=== Verification Complete ==="
```

---

## Troubleshooting

**Job fails with permission error:**
```bash
# Check Glue role has S3 access
aws iam simulate-principal-policy \
  --policy-source-arn "arn:aws:iam::${ACCOUNT_ID}:role/AWSGlueServiceRoleDefault" \
  --action-names s3:GetObject \
  --resource-arns "arn:aws:s3:::${DATA_BUCKET}/*"
```

**Job runs but produces no output:**
```bash
# Check job logs
aws logs filter-log-events \
  --log-group-name "/aws-glue/jobs/output" \
  --filter-pattern "error"
# Also: Job Bookmark may think files already processed
# Reset bookmark: aws glue reset-job-bookmark --job-name customers-csv-to-parquet
```

**Crawler not finding partitions:**
```bash
# Ensure Parquet output has correct partition path structure
aws s3 ls s3://${DATA_BUCKET}/processed/customers/ --recursive
# Should show: processed/customers/year=2024/month=1/day=15/xxx.parquet
```

---

## Expected Outcome

- ✅ PySpark Glue job reads raw CSV from `s3://*/raw/customers/`
- ✅ Transforms: type casting, null filter, deduplication, partition columns
- ✅ Writes compressed Parquet to `s3://*/processed/customers/`
- ✅ Job Bookmark enabled — second run processes only new files
- ✅ Glue Catalog updated with table schema and partitions
- ✅ Athena can query processed Parquet directly
- ✅ CloudWatch logs for job monitoring

---

## Cleanup

```bash
# Delete Glue job
aws glue delete-job --job-name "customers-csv-to-parquet"

# Delete Glue crawler
aws glue delete-crawler --name "customers-processed-crawler"

# Delete Glue database (and all tables)
aws glue delete-database --name "myapp_db"

# Delete S3 buckets
aws s3 rm s3://${DATA_BUCKET} --recursive
aws s3 rb s3://${DATA_BUCKET}
aws s3 rm s3://${SCRIPTS_BUCKET} --recursive
aws s3 rb s3://${SCRIPTS_BUCKET}

# Delete IAM role
aws iam detach-role-policy \
  --role-name AWSGlueServiceRoleDefault \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole
aws iam delete-role-policy \
  --role-name AWSGlueServiceRoleDefault \
  --policy-name GlueS3Access
aws iam delete-role --role-name AWSGlueServiceRoleDefault

echo "Glue ETL cleanup complete"
```

---

## 5. Hands-on Implementation

### 5A. AWS Console Method
Follow the steps_awsconsoleui.md guide for step-by-step console walkthrough.

**Summary:**
1. Navigate to the relevant AWS service console
2. Create required resources using the wizard
3. Configure settings per the architecture
4. Test the deployment

### 5B. AWS CLI Method
Follow the steps.md guide for complete CLI command reference.

`ash
# Set region
export AWS_DEFAULT_REGION=us-east-1

# Verify identity
aws sts get-caller-identity

# Create main resource (see steps.md for full commands)
aws ec2 describe-vpcs --output table
`

**Prerequisites Check:**
- âœ… AWS CLI configured with ws configure
- âœ… Correct region set to us-east-1
- âœ… IAM permissions verified

**Decision Point 1:** Console vs CLI implementation
| Option | Pros | For This Project |
|--------|------|-----------------|
| AWS Console | Visual, beginner-friendly | âœ… First time |
| AWS CLI | Repeatable, scriptable | âœ… Automation |

**Expected Outcome:** All resources deployed and healthy in AWS Console.

**Troubleshooting:** If deployment fails, check IAM permissions and CloudWatch Logs.
