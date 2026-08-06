# Verification & Validation — Project 9.1 Data Lake Architecture

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| S3 Data Lake Bucket | S3 → Buckets | `handson-data-lake-*` with raw/, processed/, curated/, archive/ prefixes |
| Glue Databases | Glue → Databases | `raw_db`, `processed_db`, `curated_db` listed |
| Glue Tables | Glue → Tables | Tables visible under each database |
| Glue Crawler | Glue → Crawlers | `handson-crawler` listed, last run status = **Succeeded** |
| Lake Formation | Lake Formation → Data lake locations | S3 bucket registered |
| S3 Lifecycle | S3 → Bucket → Management → Lifecycle rules | Lifecycle rule moving archive/ to Glacier |
| Athena | Athena → Query Editor | Can query tables in `raw_db` |

📸 Screenshot: S3 bucket showing raw/, processed/, curated/, archive/ prefixes  
📸 Screenshot: Glue Data Catalog showing databases and tables  
📸 Screenshot: Athena query returning rows from data lake table

---

## 2. AWS CLI Verification

```bash
# 2.1 Confirm S3 zones exist
BUCKET=$(aws s3 ls | grep handson-data-lake | awk '{print $3}')
for zone in raw processed curated archive; do
  COUNT=$(aws s3 ls s3://$BUCKET/$zone/ 2>/dev/null | wc -l)
  echo "$zone/ prefix: $COUNT objects"
done
# Expected: all 4 zones exist

# 2.2 Confirm Glue databases
aws glue get-databases \
  --query "DatabaseList[*].{Name:Name,Location:LocationUri}" \
  --output table
# Expected: raw_db, processed_db, curated_db listed

# 2.3 List tables in raw_db
aws glue get-tables \
  --database-name raw_db \
  --query "TableList[*].{Name:Name,Location:StorageDescriptor.Location,Format:StorageDescriptor.InputFormat}"
# Expected: orders or sample table listed

# 2.4 Run Glue crawler and verify
aws glue start-crawler --name handson-crawler
echo "Waiting for crawler to complete..."
sleep 60
aws glue get-crawler \
  --name handson-crawler \
  --query "Crawler.{State:State,LastCrawl:LastCrawl.Status,TablesCreated:LastCrawl.TablesCreated}"
# Expected: State=READY, LastCrawl.Status=SUCCEEDED

# 2.5 Confirm Lake Formation registration
aws lakeformation list-resources \
  --query "ResourceInfoList[*].{Resource:ResourceArn,RoleArn:RoleArn}"
# Expected: S3 bucket ARN listed

# 2.6 Query data lake via Athena
QUERY_ID=$(aws athena start-query-execution \
  --query-string "SELECT COUNT(*) as total FROM raw_db.orders LIMIT 1;" \
  --query-execution-context Database=raw_db \
  --result-configuration OutputLocation=s3://$BUCKET/athena-results/ \
  --query "QueryExecutionId" --output text)
aws athena wait query-execution-complete --query-execution-id $QUERY_ID
aws athena get-query-results --query-execution-id $QUERY_ID \
  --query "ResultSet.Rows[1].Data[0].VarCharValue"
# Expected: row count > 0

# 2.7 Run data lake setup script
python code/data_lake_setup.py --bucket $BUCKET
# Expected: prints data lake structure summary
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_s3_bucket.data_lake
# aws_s3_bucket_lifecycle_configuration.data_lake
# aws_glue_catalog_database.raw
# aws_glue_catalog_database.processed
# aws_glue_catalog_database.curated
# aws_glue_crawler.main
# aws_iam_role.glue_crawler
# aws_lakeformation_resource.data_lake

terraform output data_lake_bucket
# Expected: handson-data-lake-xxx

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Data Flow Test

```bash
BUCKET=$(terraform output -raw data_lake_bucket 2>/dev/null || aws s3 ls | grep handson-data-lake | awk '{print $3}')

# Upload sample data to raw zone
echo 'order_id,customer_id,amount,order_date
ORD-001,CUST-1,29.99,2024-01-15
ORD-002,CUST-2,49.99,2024-01-15' > /tmp/sample_orders.csv

aws s3 cp /tmp/sample_orders.csv s3://$BUCKET/raw/orders/year=2024/month=01/day=15/orders.csv
echo "✅ Sample data uploaded to raw zone"

# Run crawler to discover schema
aws glue start-crawler --name handson-crawler
sleep 60

# Query via Athena
QUERY_ID=$(aws athena start-query-execution \
  --query-string "SELECT * FROM raw_db.orders LIMIT 5;" \
  --query-execution-context Database=raw_db \
  --result-configuration OutputLocation=s3://$BUCKET/athena-results/ \
  --query "QueryExecutionId" --output text)
aws athena wait query-execution-complete --query-execution-id $QUERY_ID
aws athena get-query-results --query-execution-id $QUERY_ID \
  --query "ResultSet.Rows[*].Data[*].VarCharValue" --output table
# Expected: order rows returned
```

---

## 5. Expected Successful Outputs

**CLI — get-databases:**
```
| raw_db       | s3://handson-data-lake-xxx/raw/       |
| processed_db | s3://handson-data-lake-xxx/processed/ |
| curated_db   | s3://handson-data-lake-xxx/curated/   |
```

**Athena query result:**
```
| total |
|-------|
| 2     |
```

**terraform output:**
```
data_lake_bucket = "handson-data-lake-abc123"
glue_database    = "raw_db"
```

---

## 6. Verification Checklist

- [ ] S3 bucket exists with raw/, processed/, curated/, archive/ prefixes
- [ ] S3 lifecycle rule moves archive/ objects to Glacier after 90 days
- [ ] Glue databases: raw_db, processed_db, curated_db all exist
- [ ] Glue crawler `handson-crawler` last run = SUCCEEDED
- [ ] Lake Formation S3 location registered
- [ ] Sample data uploaded to raw/ zone
- [ ] Athena query on raw_db returns rows
- [ ] `data_lake_setup.py` runs and prints structure summary
- [ ] `terraform plan` shows no changes

---

## Section 1: Prerequisites Verified

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 1 | AWS CLI installed | ws --version returns 2.x | Download from aws.amazon.com/cli |
| 2 | Logged in | ws sts get-caller-identity returns JSON | Run ws configure |
| 3 | Correct region | ws configure get region returns us-east-1 | Run ws configure again |

`ash
aws sts get-caller-identity
aws configure list
`

## Section 2: Resources Created

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 4 | Primary resource | Status: Active/Running/Available | Re-run creation command |
| 5 | Configuration applied | Settings match intended values | Check resource details |
| 6 | Service responding | Expected response code/output | Check security groups and logs |

`ash
# Verify resources exist
aws ec2 describe-instances --query 'Reservations[*].Instances[*].{ID:InstanceId,State:State.Name}' --output table
`

## Section 3: Validation Complete

| # | Check | Expected | Fix |
|---|-------|----------|-----|
| 7 | End-to-end test | Correct output from service | Check CloudWatch Logs |
| 8 | No errors in logs | Zero error entries | Review CloudWatch Log groups |

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| AccessDenied error | Missing IAM permissions | Add required policy to IAM user/role |
| Resource not found | Wrong region or name | Check ws configure get region |
| Timeout connecting | Security group blocking | Add inbound rule for required port |
| Quota exceeded | Service limit reached | Request limit increase or use different region |
| Authentication failure | Expired credentials | Run ws configure with fresh access keys |
