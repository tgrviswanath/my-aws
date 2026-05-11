# Steps — Project 7.4 Athena Log Analytics

## Phase 1 — Enable Log Sources

```bash
# Enable CloudTrail (if not already enabled)
aws cloudtrail create-trail \
  --name handson-trail \
  --s3-bucket-name YOUR_CLOUDTRAIL_BUCKET \
  --is-multi-region-trail

aws cloudtrail start-logging --name handson-trail

# Enable ALB access logs
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn YOUR_ALB_ARN \
  --attributes Key=access_logs.s3.enabled,Value=true \
               Key=access_logs.s3.bucket,Value=YOUR_ALB_LOGS_BUCKET \
               Key=access_logs.s3.prefix,Value=alb-logs
```

---

## Phase 2 — Deploy Athena Infrastructure

```bash
cd terraform
terraform init
terraform apply \
  -var="cloudtrail_s3_bucket=your-cloudtrail-bucket" \
  -var="alb_logs_s3_bucket=your-alb-logs-bucket"

echo "Athena URL: $(terraform output -raw athena_query_url)"
```

---

## Phase 3 — Run CloudTrail Queries

```bash
# Run query via CLI
WORKGROUP=$(terraform output -raw workgroup_name)
DATABASE=$(terraform output -raw database_name)
RESULTS_BUCKET=$(terraform output -raw results_bucket)

# Top API callers
QUERY_ID=$(aws athena start-query-execution \
  --query-string "$(cat queries/cloudtrail_queries.sql | head -15)" \
  --work-group $WORKGROUP \
  --query-execution-context Database=$DATABASE \
  --query "QueryExecutionId" --output text)

# Wait for completion
aws athena wait query-execution-complete --query-execution-id $QUERY_ID

# Get results
aws athena get-query-results --query-execution-id $QUERY_ID \
  --query "ResultSet.Rows[*].Data[*].VarCharValue" --output table
```

---

## Phase 4 — Run ALB Queries

```
1. Open Athena console: https://console.aws.amazon.com/athena
2. Select workgroup: handson-workgroup
3. Select database: handson_logs
4. Paste query from queries/alb_queries.sql
5. Click Run
6. View results in the Results tab
```

---

## Phase 5 — Cost Check

```bash
# Check how much data each query scanned
aws athena get-query-execution \
  --query-execution-id $QUERY_ID \
  --query "QueryExecution.Statistics.DataScannedInBytes"

# Convert to GB and multiply by $0.005 to get cost
python3 -c "bytes=1234567; print(f'Cost: \${bytes/1e9*5:.4f}')"
```

---

## Screenshots to Take
- [ ] Athena query editor with CloudTrail table
- [ ] Query results showing top API callers
- [ ] ALB query showing slowest endpoints
- [ ] Data scanned amount (cost awareness)
- [ ] Partition projection working (fast query without MSCK REPAIR)
