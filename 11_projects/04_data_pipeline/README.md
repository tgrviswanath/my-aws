# Project 04: Data Pipeline (S3 + Glue + Athena + QuickSight)

## Architecture

```
Data Sources
├── Application logs → S3 (raw)
├── Database exports → S3 (raw)
└── API events → Kinesis → S3 (raw)
        ↓
AWS Glue (ETL)
        ↓
S3 (processed/Parquet)
        ↓
AWS Glue Data Catalog
        ↓
Amazon Athena (SQL queries)
        ↓
Amazon QuickSight (dashboards)
```

## Use Case: E-commerce Analytics Pipeline

Process order events, transform to Parquet, query with Athena, visualize in QuickSight.

## Step 1: S3 Data Lake Structure

```bash
# Create S3 buckets
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
RAW_BUCKET="${ACCOUNT_ID}-datalake-raw"
PROCESSED_BUCKET="${ACCOUNT_ID}-datalake-processed"
ATHENA_BUCKET="${ACCOUNT_ID}-datalake-athena-results"

for BUCKET in $RAW_BUCKET $PROCESSED_BUCKET $ATHENA_BUCKET; do
  aws s3api create-bucket --bucket $BUCKET --region us-east-1
  aws s3api put-bucket-versioning \
    --bucket $BUCKET \
    --versioning-configuration Status=Enabled
  aws s3api put-public-access-block \
    --bucket $BUCKET \
    --public-access-block-configuration \
      BlockPublicAcls=true,IgnorePublicAcls=true,\
      BlockPublicPolicy=true,RestrictPublicBuckets=true
done

# S3 structure:
# raw/orders/year=2024/month=01/day=15/orders_20240115.json
# processed/orders/year=2024/month=01/day=15/part-00000.parquet
```

## Step 2: Kinesis Firehose (Real-time ingestion)

```bash
# Create Firehose delivery stream
aws firehose create-delivery-stream \
  --delivery-stream-name order-events-stream \
  --delivery-stream-type DirectPut \
  --extended-s3-destination-configuration "{
    \"RoleARN\": \"arn:aws:iam::${ACCOUNT_ID}:role/firehose-role\",
    \"BucketARN\": \"arn:aws:s3:::${RAW_BUCKET}\",
    \"Prefix\": \"orders/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/\",
    \"ErrorOutputPrefix\": \"errors/orders/\",
    \"BufferingHints\": {
      \"SizeInMBs\": 128,
      \"IntervalInSeconds\": 300
    },
    \"CompressionFormat\": \"GZIP\",
    \"DataFormatConversionConfiguration\": {
      \"Enabled\": false
    }
  }"

# Send test event
aws firehose put-record \
  --delivery-stream-name order-events-stream \
  --record Data=$(echo '{"orderId":"order-123","customerId":"cust-456","amount":99.99,"status":"CONFIRMED","timestamp":"2024-01-15T10:30:00Z"}' | base64)
```

## Step 3: AWS Glue ETL Job

```python
# glue_etl_job.py
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql import functions as F
from pyspark.sql.types import *

args = getResolvedOptions(sys.argv, ['JOB_NAME', 'RAW_BUCKET', 'PROCESSED_BUCKET', 'DATE'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Read raw JSON data
raw_df = spark.read.json(
    f"s3://{args['RAW_BUCKET']}/orders/year={args['DATE'][:4]}/month={args['DATE'][5:7]}/day={args['DATE'][8:10]}/"
)

# Transform
processed_df = raw_df \
    .withColumn('order_date', F.to_date('timestamp')) \
    .withColumn('order_hour', F.hour('timestamp')) \
    .withColumn('amount', F.col('amount').cast(DecimalType(10, 2))) \
    .withColumn('year', F.year('timestamp')) \
    .withColumn('month', F.month('timestamp')) \
    .withColumn('day', F.dayofmonth('timestamp')) \
    .filter(F.col('status').isin(['CONFIRMED', 'SHIPPED', 'DELIVERED'])) \
    .dropDuplicates(['orderId'])

# Add derived metrics
processed_df = processed_df \
    .withColumn('is_high_value', F.when(F.col('amount') >= 100, True).otherwise(False))

# Write as Parquet with partitioning
processed_df.write \
    .mode('overwrite') \
    .partitionBy('year', 'month', 'day') \
    .parquet(f"s3://{args['PROCESSED_BUCKET']}/orders/")

print(f"Processed {processed_df.count()} records")
job.commit()
```

```bash
# Create Glue job
aws glue create-job \
  --name order-etl-job \
  --role arn:aws:iam::${ACCOUNT_ID}:role/glue-role \
  --command '{
    "Name": "glueetl",
    "ScriptLocation": "s3://my-scripts/glue_etl_job.py",
    "PythonVersion": "3"
  }' \
  --default-arguments '{
    "--job-language": "python",
    "--enable-metrics": "",
    "--enable-continuous-cloudwatch-log": "true",
    "--enable-spark-ui": "true",
    "--spark-event-logs-path": "s3://my-scripts/spark-logs/"
  }' \
  --glue-version "4.0" \
  --number-of-workers 5 \
  --worker-type G.1X

# Schedule with Glue Trigger (daily at 2 AM)
aws glue create-trigger \
  --name daily-etl-trigger \
  --type SCHEDULED \
  --schedule "cron(0 2 * * ? *)" \
  --actions '[{"JobName": "order-etl-job"}]' \
  --start-on-creation
```

## Step 4: Glue Data Catalog

```bash
# Create database
aws glue create-database \
  --database-input '{
    "Name": "ecommerce_analytics",
    "Description": "E-commerce analytics data lake"
  }'

# Create table (or use Glue Crawler)
aws glue create-table \
  --database-name ecommerce_analytics \
  --table-input '{
    "Name": "orders",
    "Description": "Processed order data",
    "StorageDescriptor": {
      "Columns": [
        {"Name": "orderid", "Type": "string"},
        {"Name": "customerid", "Type": "string"},
        {"Name": "amount", "Type": "decimal(10,2)"},
        {"Name": "status", "Type": "string"},
        {"Name": "timestamp", "Type": "timestamp"},
        {"Name": "is_high_value", "Type": "boolean"}
      ],
      "Location": "s3://ACCOUNT_ID-datalake-processed/orders/",
      "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
      "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
      "SerdeInfo": {
        "SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      }
    },
    "PartitionKeys": [
      {"Name": "year", "Type": "int"},
      {"Name": "month", "Type": "int"},
      {"Name": "day", "Type": "int"}
    ],
    "TableType": "EXTERNAL_TABLE",
    "Parameters": {
      "classification": "parquet",
      "compressionType": "none"
    }
  }'

# Run Glue Crawler to auto-discover schema
aws glue create-crawler \
  --name orders-crawler \
  --role arn:aws:iam::${ACCOUNT_ID}:role/glue-role \
  --database-name ecommerce_analytics \
  --targets '{
    "S3Targets": [{
      "Path": "s3://ACCOUNT_ID-datalake-processed/orders/"
    }]
  }' \
  --schedule "cron(30 2 * * ? *)"
```

## Step 5: Athena Queries

```sql
-- Configure Athena output location
-- aws athena update-work-group --work-group primary \
--   --configuration ResultConfiguration={OutputLocation=s3://ACCOUNT_ID-datalake-athena-results/}

-- Daily revenue
SELECT
    year,
    month,
    day,
    COUNT(*) as order_count,
    SUM(amount) as total_revenue,
    AVG(amount) as avg_order_value,
    COUNT(CASE WHEN is_high_value THEN 1 END) as high_value_orders
FROM ecommerce_analytics.orders
WHERE year = 2024 AND month = 1
GROUP BY year, month, day
ORDER BY day;

-- Top customers by revenue
SELECT
    customerid,
    COUNT(*) as order_count,
    SUM(amount) as total_spent,
    MAX(amount) as largest_order
FROM ecommerce_analytics.orders
WHERE year = 2024
GROUP BY customerid
ORDER BY total_spent DESC
LIMIT 100;

-- Order status distribution
SELECT
    status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM ecommerce_analytics.orders
WHERE year = 2024 AND month = 1
GROUP BY status;

-- Hourly order patterns
SELECT
    order_hour,
    COUNT(*) as orders,
    AVG(amount) as avg_amount
FROM ecommerce_analytics.orders
WHERE year = 2024
GROUP BY order_hour
ORDER BY order_hour;
```

```bash
# Run Athena query via CLI
QUERY_ID=$(aws athena start-query-execution \
  --query-string "SELECT COUNT(*) as total_orders, SUM(amount) as revenue FROM ecommerce_analytics.orders WHERE year=2024" \
  --query-execution-context Database=ecommerce_analytics \
  --result-configuration OutputLocation=s3://${ATHENA_BUCKET}/results/ \
  --query 'QueryExecutionId' --output text)

# Wait for completion
aws athena wait query-execution-complete --query-execution-id $QUERY_ID

# Get results
aws athena get-query-results --query-execution-id $QUERY_ID
```

## Step 6: Cost Optimization for Data Lake

```bash
# Convert to Parquet (already done) — 75% storage reduction vs JSON
# Use columnar format — Athena scans only needed columns

# Partition pruning — always filter on partition columns
# BAD:  SELECT * FROM orders WHERE customerid = 'cust-123'
# GOOD: SELECT * FROM orders WHERE year=2024 AND month=1 AND customerid='cust-123'

# Compress with Snappy (good balance of speed/compression)
# Already configured in Glue job

# S3 Lifecycle for raw data
aws s3api put-bucket-lifecycle-configuration \
  --bucket $RAW_BUCKET \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "archive-raw-data",
      "Status": "Enabled",
      "Filter": {"Prefix": "orders/"},
      "Transitions": [
        {"Days": 30, "StorageClass": "STANDARD_IA"},
        {"Days": 90, "StorageClass": "GLACIER"}
      ]
    }]
  }'
```

## Estimated Monthly Cost (10GB/day ingestion)

| Service | Cost |
|---------|------|
| S3 (300GB raw + 75GB processed) | ~$9 |
| Kinesis Firehose (300GB) | ~$9 |
| Glue ETL (30 DPU-hours/month) | ~$4.40 |
| Athena (100GB scanned) | ~$5 |
| **Total** | **~$27/month** |
