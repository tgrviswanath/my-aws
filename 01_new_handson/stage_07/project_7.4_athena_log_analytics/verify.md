# Verification & Validation — Project 7.4 Athena Log Analytics

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Athena Workgroup | Athena → Workgroups | `handson-workgroup` listed, State = **Enabled** |
| Athena Database | Athena → Query Editor → Database dropdown | `handson_logs` database visible |
| CloudTrail Table | Athena → Query Editor → Tables | `cloudtrail_logs` table listed |
| ALB Logs Table | Athena → Query Editor → Tables | `alb_access_logs` table listed |
| S3 Results Bucket | S3 → Buckets | `handson-athena-results-*` exists |
| CloudTrail | CloudTrail → Trails | `handson-trail` logging = **ON** |
| ALB Access Logs | EC2 → Load Balancers → Attributes | Access logs = **Enabled** |

📸 Screenshot: Athena query editor with CloudTrail table  
📸 Screenshot: Query results showing top API callers  
📸 Screenshot: ALB query showing slowest endpoints  
📸 Screenshot: Data scanned amount (cost awareness)

---

## 2. AWS CLI Verification

```bash
# 2.1 Confirm workgroup exists and is enabled
aws athena get-work-group \
  --work-group handson-workgroup \
  --query "WorkGroup.{Name:Name,State:State,BytesScannedLimit:Configuration.BytesScannedCutoffPerQuery}"
# Expected: State=ENABLED

# 2.2 List databases in Athena
aws athena list-databases \
  --catalog-name AwsDataCatalog \
  --query "DatabaseList[*].Name"
# Expected: handson_logs listed

# 2.3 List tables in the database
aws athena list-table-metadata \
  --catalog-name AwsDataCatalog \
  --database-name handson_logs \
  --query "TableMetadataList[*].{Name:Name,Type:TableType}"
# Expected: cloudtrail_logs and alb_access_logs listed

# 2.4 Run a test CloudTrail query
QUERY_ID=$(aws athena start-query-execution \
  --query-string "SELECT useridentity.arn, COUNT(*) as call_count FROM cloudtrail_logs WHERE year='$(date +%Y)' GROUP BY useridentity.arn ORDER BY call_count DESC LIMIT 5;" \
  --work-group handson-workgroup \
  --query-execution-context Database=handson_logs \
  --result-configuration OutputLocation=s3://$(aws s3 ls | grep handson-athena-results | awk '{print $3}')/ \
  --query "QueryExecutionId" --output text)

echo "Query ID: $QUERY_ID"

# Wait for completion
aws athena wait query-execution-complete --query-execution-id $QUERY_ID

# Check status
aws athena get-query-execution \
  --query-execution-id $QUERY_ID \
  --query "QueryExecution.{State:Status.State,DataScanned:Statistics.DataScannedInBytes,Duration:Statistics.TotalExecutionTimeInMillis}"
# Expected: State=SUCCEEDED

# 2.5 Get query results
aws athena get-query-results \
  --query-execution-id $QUERY_ID \
  --query "ResultSet.Rows[*].Data[*].VarCharValue" \
  --output table
# Expected: table with ARN and call_count columns

# 2.6 Check cost of query
aws athena get-query-execution \
  --query-execution-id $QUERY_ID \
  --query "QueryExecution.Statistics.DataScannedInBytes" --output text | \
  python3 -c "import sys; b=int(sys.stdin.read()); print(f'Data scanned: {b/1e6:.2f} MB | Cost: \${b/1e12*5:.6f}')"
# Expected: cost printed (should be very small for test data)

# 2.7 Confirm CloudTrail is logging
aws cloudtrail get-trail-status \
  --name handson-trail \
  --query "{IsLogging:IsLogging,LatestDelivery:LatestDeliveryTime}"
# Expected: IsLogging=true
```

---

## 3. Terraform State Verification

```bash
cd terraform

# 3.1 List all resources
terraform state list
# Expected:
# aws_athena_workgroup.main
# aws_athena_database.logs
# aws_glue_catalog_table.cloudtrail
# aws_glue_catalog_table.alb_logs
# aws_s3_bucket.athena_results
# aws_cloudtrail.main

# 3.2 Inspect workgroup config
terraform state show aws_athena_workgroup.main
# Shows: name=handson-workgroup, bytes_scanned_cutoff_per_query (cost guard)

# 3.3 Confirm outputs
terraform output athena_query_url
# Expected: https://console.aws.amazon.com/athena/home#/query-editor

terraform output workgroup_name
# Expected: handson-workgroup

# 3.4 No drift
terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Query Execution

```bash
WORKGROUP=$(terraform output -raw workgroup_name 2>/dev/null || echo "handson-workgroup")
RESULTS_BUCKET=$(aws s3 ls | grep handson-athena-results | awk '{print $3}')

# Run ALB slow requests query
QUERY_ID=$(aws athena start-query-execution \
  --query-string "SELECT request_url, request_processing_time FROM alb_access_logs WHERE request_processing_time > 1.0 ORDER BY request_processing_time DESC LIMIT 10;" \
  --work-group $WORKGROUP \
  --query-execution-context Database=handson_logs \
  --result-configuration OutputLocation=s3://$RESULTS_BUCKET/ \
  --query "QueryExecutionId" --output text)

aws athena wait query-execution-complete --query-execution-id $QUERY_ID

STATE=$(aws athena get-query-execution \
  --query-execution-id $QUERY_ID \
  --query "QueryExecution.Status.State" --output text)
echo "Query state: $STATE"
# Expected: SUCCEEDED
```

---

## 5. Expected Successful Outputs

**CLI — get-query-execution:**
```json
{
  "State": "SUCCEEDED",
  "DataScanned": 1048576,
  "Duration": 2340
}
```

**Query results (top API callers):**
```
| arn:aws:iam::123456789012:user/admin | 142 |
| arn:aws:sts::123456789012:assumed-role/ECSRole/task | 89 |
| arn:aws:iam::123456789012:user/developer | 34 |
```

**Cost calculation:**
```
Data scanned: 1.05 MB | Cost: $0.000005
```

**terraform output:**
```
athena_query_url = "https://console.aws.amazon.com/athena/home#/query-editor"
workgroup_name   = "handson-workgroup"
database_name    = "handson_logs"
```

---

## 6. Verification Checklist

- [ ] Athena workgroup `handson-workgroup` state = ENABLED
- [ ] Database `handson_logs` visible in Athena query editor
- [ ] Tables `cloudtrail_logs` and `alb_access_logs` listed
- [ ] S3 results bucket exists
- [ ] CloudTrail `handson-trail` IsLogging = true
- [ ] ALB access logs enabled on load balancer
- [ ] Test CloudTrail query completes with State = SUCCEEDED
- [ ] Query results return rows (top API callers)
- [ ] ALB slow requests query returns results
- [ ] Data scanned amount printed (cost awareness confirmed)
- [ ] Partition pruning works (query with year/month filter is faster)
- [ ] `terraform plan` shows no changes
- [ ] `terraform state list` shows all resources
