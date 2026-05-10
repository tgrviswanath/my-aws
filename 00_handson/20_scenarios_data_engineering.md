# Level 4 — Data Engineering Hands-On Scenarios

> **Goal**: Build real data pipelines on AWS.  
> **Prerequisites**: Completed Levels 1–3, Python + SQL knowledge.

---

## Scenario 17 — Data Lake Project (CSV → S3 → Glue → Athena)

**Skills**: S3, Glue, Athena, Data Catalog  
**Time**: 60 minutes

### Architecture
```
CSV Files (local)
      ↓ upload
S3 (raw/bronze layer)
      ↓ Glue Crawler
Glue Data Catalog (schema discovery)
      ↓ Athena
SQL Queries on S3 data (no database needed!)
```

### Step-by-Step

```bash
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET="my-data-lake-${ACCOUNT_ID}"
ATHENA_RESULTS="s3://${BUCKET}/athena-results/"

# Step 1: Create data lake bucket
aws s3api create-bucket --bucket $BUCKET --region $REGION

# Create folder structure (Hive-style partitioning)
echo "Creating data lake structure..."

# Step 2: Generate and upload sample data
python3 << 'EOF'
import csv
import random
import boto3
from datetime import datetime, timedelta

s3 = boto3.client('s3')
BUCKET = 'my-data-lake-ACCOUNT_ID'  # Replace

# Generate transactions data
def generate_transactions(year, month, n=1000):
    rows = []
    start = datetime(year, month, 1)
    for i in range(n):
        date = start + timedelta(days=random.randint(0, 27))
        rows.append({
            'transaction_id': f'txn-{year}{month:02d}-{i:04d}',
            'user_id': f'user-{random.randint(1, 100):03d}',
            'amount': round(random.uniform(5, 500), 2),
            'category': random.choice(['food', 'travel', 'tech', 'health']),
            'status': random.choice(['completed', 'pending', 'failed']),
            'date': date.strftime('%Y-%m-%d'),
        })
    return rows

# Upload partitioned data
for year in [2024]:
    for month in [1, 2, 3]:
        rows = generate_transactions(year, month)
        # Write to CSV
        import io
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

        # Upload with Hive partitioning
        key = f"raw/transactions/year={year}/month={month:02d}/data.csv"
        s3.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=output.getvalue().encode()
        )
        print(f"Uploaded: s3://{BUCKET}/{key} ({len(rows)} rows)")

print("✅ Sample data uploaded!")
EOF

# Step 3: Create Glue Database
aws glue create-database \
  --database-input '{
    "Name": "data_lake",
    "Description": "My data lake database"
  }'

# Step 4: Create Glue Crawler (auto-discovers schema)
aws iam create-role \
  --role-name "GlueCrawlerRole" \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow", "Principal": {"Service": "glue.amazonaws.com"}, "Action": "sts:AssumeRole"}]
  }' 2>/dev/null || true

aws iam attach-role-policy \
  --role-name "GlueCrawlerRole" \
  --policy-arn "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"

aws iam attach-role-policy \
  --role-name "GlueCrawlerRole" \
  --policy-arn "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"

aws glue create-crawler \
  --name "transactions-crawler" \
  --role "GlueCrawlerRole" \
  --database-name "data_lake" \
  --targets "{\"S3Targets\": [{\"Path\": \"s3://${BUCKET}/raw/transactions/\"}]}" \
  --configuration '{"Version": 1.0, "CrawlerOutput": {"Partitions": {"AddOrUpdateBehavior": "InheritFromTable"}}}'

# Run crawler
aws glue start-crawler --name "transactions-crawler"
echo "Crawler running... (takes ~2 minutes)"

# Wait for crawler to finish
while true; do
  STATE=$(aws glue get-crawler --name transactions-crawler --query 'Crawler.State' --output text)
  echo "Crawler state: $STATE"
  if [ "$STATE" = "READY" ]; then break; fi
  sleep 15
done

echo "✅ Schema discovered!"

# Step 5: Configure Athena output location
aws athena update-work-group \
  --work-group primary \
  --configuration-updates "ResultConfigurationUpdates={OutputLocation=${ATHENA_RESULTS}}"

# Step 6: Query with Athena!
echo "Running Athena queries..."

# Query 1: Total revenue by category
QUERY_ID=$(aws athena start-query-execution \
  --query-string "
    SELECT
      category,
      COUNT(*) as transaction_count,
      ROUND(SUM(amount), 2) as total_revenue,
      ROUND(AVG(amount), 2) as avg_amount
    FROM data_lake.transactions
    WHERE status = 'completed'
    GROUP BY category
    ORDER BY total_revenue DESC
  " \
  --result-configuration "OutputLocation=${ATHENA_RESULTS}" \
  --query 'QueryExecutionId' --output text)

# Wait for query
aws athena wait query-execution-complete --query-execution-id $QUERY_ID 2>/dev/null || sleep 10

# Get results
aws athena get-query-results \
  --query-execution-id $QUERY_ID \
  --query 'ResultSet.Rows[*].Data[*].VarCharValue' \
  --output table

echo "✅ Data lake query complete!"
```

### What You Learned
- ✅ Data lake architecture (raw/bronze layer)
- ✅ Hive-style partitioning (year=/month=)
- ✅ Glue Crawler for schema discovery
- ✅ Athena for SQL queries on S3 (no database!)
- ✅ Partition pruning for cost optimization

---

## Scenario 18 — ETL Pipeline with Glue

**Skills**: Glue ETL, PySpark, Data transformation  
**Time**: 45 minutes

### Architecture
```
S3 (raw CSV)
      ↓ Glue ETL Job (PySpark)
      ├── Clean nulls
      ├── Standardize formats
      ├── Add derived columns
      └── Convert to Parquet
S3 (processed/silver layer)
      ↓ Athena
Analytics queries
```

```python
# glue_etl_job.py — runs in AWS Glue
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F

args = getResolvedOptions(sys.argv, ['JOB_NAME', 'source_bucket', 'target_bucket'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

SOURCE = f"s3://{args['source_bucket']}/raw/transactions/"
TARGET = f"s3://{args['target_bucket']}/processed/transactions/"

# Read raw data
df = spark.read.option("header", "true").csv(SOURCE)
print(f"Raw rows: {df.count()}")

# Transform
df_clean = df \
    .dropDuplicates(['transaction_id']) \
    .dropna(subset=['transaction_id', 'user_id', 'amount']) \
    .withColumn('amount', F.col('amount').cast('double')) \
    .filter(F.col('amount') > 0) \
    .withColumn('amount_usd',
        F.col('amount') * F.when(F.col('currency') == 'EUR', 1.08)
                           .when(F.col('currency') == 'GBP', 1.27)
                           .otherwise(1.0)) \
    .withColumn('date', F.to_date('date', 'yyyy-MM-dd')) \
    .withColumn('year', F.year('date')) \
    .withColumn('month', F.month('date')) \
    .withColumn('is_high_value', F.col('amount_usd') > 500) \
    .withColumn('_processed_at', F.current_timestamp())

print(f"Clean rows: {df_clean.count()}")

# Write as Parquet (partitioned, compressed)
df_clean.write \
    .mode('overwrite') \
    .partitionBy('year', 'month') \
    .option('compression', 'snappy') \
    .parquet(TARGET)

print(f"✅ Written to {TARGET}")
job.commit()
```

```bash
# Upload Glue script to S3
aws s3 cp glue_etl_job.py s3://$BUCKET/scripts/glue_etl_job.py

# Create Glue job
aws glue create-job \
  --name "transactions-etl" \
  --role "GlueCrawlerRole" \
  --command '{
    "Name": "glueetl",
    "ScriptLocation": "s3://'"$BUCKET"'/scripts/glue_etl_job.py",
    "PythonVersion": "3"
  }' \
  --default-arguments '{
    "--source_bucket": "'"$BUCKET"'",
    "--target_bucket": "'"$BUCKET"'",
    "--job-language": "python",
    "--enable-metrics": "",
    "--enable-continuous-cloudwatch-log": "true"
  }' \
  --glue-version "4.0" \
  --number-of-workers 2 \
  --worker-type G.1X

# Run the job
RUN_ID=$(aws glue start-job-run \
  --job-name "transactions-etl" \
  --query 'JobRunId' --output text)

echo "Job running: $RUN_ID"

# Monitor
while true; do
  STATE=$(aws glue get-job-run \
    --job-name transactions-etl \
    --run-id $RUN_ID \
    --query 'JobRun.JobRunState' --output text)
  echo "State: $STATE"
  if [[ "$STATE" == "SUCCEEDED" || "$STATE" == "FAILED" ]]; then break; fi
  sleep 20
done

echo "✅ ETL job complete!"
```

### What You Learned
- ✅ Glue ETL jobs with PySpark
- ✅ Data cleaning and transformation
- ✅ Parquet output with partitioning
- ✅ Glue job monitoring

---

## Scenario 19 — Real-Time Streaming Pipeline

**Skills**: Kinesis, Lambda, S3  
**Time**: 45 minutes

### Architecture
```
Producer (Python script)
      ↓ put_record()
Kinesis Data Stream (4 shards)
      ↓ trigger
Lambda (process + aggregate)
      ↓
S3 (raw events) + DynamoDB (aggregates)
```

```python
# producer.py — sends events to Kinesis
import boto3
import json
import time
import random
from datetime import datetime

kinesis = boto3.client('kinesis', region_name='us-east-1')
STREAM = 'transactions-stream'

def send_event(user_id: str, amount: float, category: str):
    event = {
        'transaction_id': f'txn-{int(time.time()*1000)}',
        'user_id': user_id,
        'amount': amount,
        'category': category,
        'timestamp': datetime.utcnow().isoformat(),
        'status': random.choice(['completed', 'pending'])
    }
    kinesis.put_record(
        StreamName=STREAM,
        Data=json.dumps(event),
        PartitionKey=user_id  # Same user → same shard (ordered)
    )
    return event

# Send 100 events
print("Sending events to Kinesis...")
for i in range(100):
    event = send_event(
        user_id=f"user-{random.randint(1, 20):03d}",
        amount=round(random.uniform(5, 500), 2),
        category=random.choice(['food', 'travel', 'tech', 'health'])
    )
    print(f"Sent: {event['transaction_id']} - ${event['amount']}")
    time.sleep(0.1)

print("✅ All events sent!")
```

```python
# stream_processor.py — Lambda function
import boto3
import json
import base64
import os
from collections import defaultdict
from datetime import datetime

s3       = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table    = dynamodb.Table(os.environ['AGGREGATES_TABLE'])
BUCKET   = os.environ['OUTPUT_BUCKET']

def handler(event, context):
    records = []
    aggregates = defaultdict(lambda: {'count': 0, 'total': 0.0})

    for record in event['Records']:
        # Decode Kinesis record
        data = json.loads(base64.b64decode(record['kinesis']['data']))
        records.append(data)

        # Aggregate by category
        cat = data['category']
        aggregates[cat]['count'] += 1
        aggregates[cat]['total'] += data['amount']

    # Save raw events to S3
    timestamp = datetime.utcnow().strftime('%Y/%m/%d/%H')
    key = f"streaming/year={datetime.utcnow().year}/month={datetime.utcnow().month:02d}/{timestamp}/{context.aws_request_id}.json"

    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=json.dumps(records, default=str),
        ContentType='application/json'
    )

    # Update aggregates in DynamoDB
    for category, stats in aggregates.items():
        table.update_item(
            Key={'category': category},
            UpdateExpression='ADD #count :c, #total :t',
            ExpressionAttributeNames={'#count': 'count', '#total': 'total'},
            ExpressionAttributeValues={':c': stats['count'], ':t': stats['total']}
        )

    print(f"✅ Processed {len(records)} events, saved to {key}")
    return {'statusCode': 200, 'processed': len(records)}
```

```bash
# Create Kinesis stream
aws kinesis create-stream \
  --stream-name "transactions-stream" \
  --shard-count 2

aws kinesis wait stream-exists --stream-name "transactions-stream"

# Create aggregates table
aws dynamodb create-table \
  --table-name "stream-aggregates" \
  --attribute-definitions AttributeName=category,AttributeType=S \
  --key-schema AttributeName=category,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# Deploy Lambda
zip stream_processor.zip stream_processor.py

aws lambda create-function \
  --function-name "stream-processor" \
  --runtime python3.12 \
  --role $ROLE_ARN \
  --handler stream_processor.handler \
  --zip-file fileb://stream_processor.zip \
  --environment Variables="{OUTPUT_BUCKET=${BUCKET},AGGREGATES_TABLE=stream-aggregates}"

# Connect Lambda to Kinesis
STREAM_ARN=$(aws kinesis describe-stream-summary \
  --stream-name transactions-stream \
  --query 'StreamDescriptionSummary.StreamARN' --output text)

aws lambda create-event-source-mapping \
  --function-name "stream-processor" \
  --event-source-arn $STREAM_ARN \
  --starting-position LATEST \
  --batch-size 100

# Run producer
python3 producer.py

# Check aggregates
aws dynamodb scan \
  --table-name "stream-aggregates" \
  --query 'Items[*].{Category:category.S,Count:count.N,Total:total.N}' \
  --output table

echo "✅ Streaming pipeline complete!"
```

### What You Learned
- ✅ Kinesis Data Streams for real-time ingestion
- ✅ Lambda as stream consumer
- ✅ Real-time aggregation with DynamoDB
- ✅ Raw event storage in S3

---

## Scenario 20 — Spark Processing on EMR

**Skills**: EMR, PySpark, S3  
**Time**: 30 minutes (+ cluster startup ~10 min)

```bash
# Step 1: Create EMR cluster
CLUSTER_ID=$(aws emr create-cluster \
  --name "data-processing-cluster" \
  --release-label emr-7.0.0 \
  --applications Name=Spark \
  --instance-type m5.xlarge \
  --instance-count 3 \
  --use-default-roles \
  --ec2-attributes KeyName=my-ec2-key \
  --log-uri s3://$BUCKET/emr-logs/ \
  --query 'ClusterId' --output text)

echo "Cluster: $CLUSTER_ID"
echo "Waiting for cluster to start (~10 minutes)..."
aws emr wait cluster-running --cluster-id $CLUSTER_ID
```

```python
# spark_job.py — PySpark job for EMR
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
import sys

spark = SparkSession.builder \
    .appName("TransactionAnalysis") \
    .getOrCreate()

INPUT  = sys.argv[1]  # s3://bucket/processed/transactions/
OUTPUT = sys.argv[2]  # s3://bucket/analytics/

# Read Parquet data
df = spark.read.parquet(INPUT)
print(f"Total rows: {df.count():,}")

# Analysis 1: Revenue by category and month
monthly_revenue = df \
    .filter(F.col('status') == 'completed') \
    .groupBy('year', 'month', 'category') \
    .agg(
        F.count('*').alias('transaction_count'),
        F.sum('amount_usd').alias('total_revenue'),
        F.avg('amount_usd').alias('avg_amount'),
        F.countDistinct('user_id').alias('unique_users')
    ) \
    .orderBy('year', 'month', F.desc('total_revenue'))

monthly_revenue.write.mode('overwrite').parquet(f"{OUTPUT}/monthly_revenue/")

# Analysis 2: Top users by spend
top_users = df \
    .filter(F.col('status') == 'completed') \
    .groupBy('user_id') \
    .agg(F.sum('amount_usd').alias('total_spend')) \
    .orderBy(F.desc('total_spend')) \
    .limit(100)

top_users.write.mode('overwrite').parquet(f"{OUTPUT}/top_users/")

print("✅ Spark job complete!")
spark.stop()
```

```bash
# Upload Spark script
aws s3 cp spark_job.py s3://$BUCKET/scripts/spark_job.py

# Submit Spark job to EMR
STEP_ID=$(aws emr add-steps \
  --cluster-id $CLUSTER_ID \
  --steps "[{
    \"Name\": \"Transaction Analysis\",
    \"ActionOnFailure\": \"CONTINUE\",
    \"HadoopJarStep\": {
      \"Jar\": \"command-runner.jar\",
      \"Args\": [
        \"spark-submit\",
        \"--deploy-mode\", \"cluster\",
        \"s3://${BUCKET}/scripts/spark_job.py\",
        \"s3://${BUCKET}/processed/transactions/\",
        \"s3://${BUCKET}/analytics/\"
      ]
    }
  }]" \
  --query 'StepIds[0]' --output text)

echo "Step submitted: $STEP_ID"

# Monitor step
aws emr wait step-complete --cluster-id $CLUSTER_ID --step-id $STEP_ID
echo "✅ Spark job complete!"

# Query results with Athena
aws athena start-query-execution \
  --query-string "SELECT * FROM data_lake.monthly_revenue ORDER BY total_revenue DESC LIMIT 10" \
  --result-configuration "OutputLocation=${ATHENA_RESULTS}"

# IMPORTANT: Terminate cluster when done (saves money!)
aws emr terminate-clusters --cluster-ids $CLUSTER_ID
echo "Cluster terminating..."
```

### What You Learned
- ✅ EMR cluster creation and management
- ✅ PySpark for large-scale data processing
- ✅ Submitting Spark jobs to EMR
- ✅ Cost management (terminate when done!)

---

## Summary — Data Engineering Level Complete ✅

| Scenario | Services | Key Concept |
|---------|---------|------------|
| 17 | S3, Glue, Athena | Data lake, schema discovery, SQL on S3 |
| 18 | Glue ETL | PySpark transformations, Parquet output |
| 19 | Kinesis, Lambda | Real-time streaming, aggregation |
| 20 | EMR, Spark | Distributed processing, large datasets |

**Next**: Move to `21_scenarios_production.md` → Netflix-style architecture, multi-env Terraform, EKS, complete data platform.
