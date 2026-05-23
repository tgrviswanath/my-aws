# Verification & Validation — Project 9.4 Spark Processing on EMR

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| EMR Cluster | EMR → Clusters | `handson-spark-cluster` listed, Status = **Waiting** or **Running** |
| Master Node | Cluster → Hardware tab | Master instance running |
| Core Nodes | Cluster → Hardware tab | Core instances running |
| Spark Step | Cluster → Steps tab | Step Status = **Completed** after job run |
| S3 Output | S3 → data lake bucket → processed/ | Parquet output files from Spark job |
| CloudWatch Logs | CloudWatch → Log Groups | EMR logs visible |
| EMR Studio | EMR → Studios (if configured) | Studio accessible |

📸 Screenshot: EMR cluster in Waiting state (ready for jobs)  
📸 Screenshot: Spark step showing Completed status  
📸 Screenshot: S3 processed/ output with Parquet files

---

## 2. AWS CLI Verification

```bash
# 2.1 Confirm cluster exists and is ready
CLUSTER_ID=$(aws emr list-clusters \
  --active \
  --query "Clusters[?Name=='handson-spark-cluster'].Id" --output text)
echo "Cluster ID: $CLUSTER_ID"

aws emr describe-cluster \
  --cluster-id $CLUSTER_ID \
  --query "Cluster.{Status:Status.State,Name:Name,MasterDNS:MasterPublicDnsName}"
# Expected: Status=WAITING (ready for steps)

# 2.2 Upload Spark script to S3
BUCKET=$(aws s3 ls | grep handson-data-lake | awk '{print $3}')
aws s3 cp src/spark_job.py s3://$BUCKET/scripts/spark_job.py
echo "Script uploaded"

# 2.3 Submit Spark step
STEP_ID=$(aws emr add-steps \
  --cluster-id $CLUSTER_ID \
  --steps "[{
    \"Type\": \"Spark\",
    \"Name\": \"Handson Spark Job\",
    \"ActionOnFailure\": \"CONTINUE\",
    \"Args\": [
      \"--deploy-mode\", \"cluster\",
      \"--master\", \"yarn\",
      \"s3://$BUCKET/scripts/spark_job.py\",
      \"--input\", \"s3://$BUCKET/raw/\",
      \"--output\", \"s3://$BUCKET/processed/spark-output/\"
    ]
  }]" \
  --query "StepIds[0]" --output text)
echo "Step ID: $STEP_ID"

# 2.4 Monitor step status
for i in {1..30}; do
  STATUS=$(aws emr describe-step \
    --cluster-id $CLUSTER_ID \
    --step-id $STEP_ID \
    --query "Step.Status.State" --output text)
  echo "Step status: $STATUS"
  [ "$STATUS" = "COMPLETED" ] && break
  [ "$STATUS" = "FAILED" ] && echo "❌ Step failed!" && break
  sleep 30
done
# Expected: COMPLETED

# 2.5 Confirm output in S3
aws s3 ls s3://$BUCKET/processed/spark-output/ --recursive | head -10
# Expected: Parquet files listed

# 2.6 Check cluster metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ElasticMapReduce \
  --metric-name CoreNodesRunning \
  --dimensions Name=JobFlowId,Value=$CLUSTER_ID \
  --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-30M +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average \
  --query "Datapoints[*].Average"
# Expected: core node count > 0
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_emr_cluster.main
# aws_security_group.emr_master
# aws_security_group.emr_core
# aws_iam_role.emr_service
# aws_iam_role.emr_ec2
# aws_iam_instance_profile.emr_ec2

terraform state show aws_emr_cluster.main
# Shows: name, release_label (emr-6.x.x), master_instance_group, core_instance_group

terraform output cluster_id
# Expected: j-XXXXXXXXXXXXX

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Spark Job Output Validation

```bash
BUCKET=$(aws s3 ls | grep handson-data-lake | awk '{print $3}')

# Count output files
FILE_COUNT=$(aws s3 ls s3://$BUCKET/processed/spark-output/ --recursive | grep ".parquet" | wc -l)
echo "Parquet output files: $FILE_COUNT"
# Expected: > 0

# Query output via Athena (after running Glue crawler on output)
QUERY_ID=$(aws athena start-query-execution \
  --query-string "SELECT COUNT(*) as total FROM processed_db.spark_output LIMIT 1;" \
  --query-execution-context Database=processed_db \
  --result-configuration OutputLocation=s3://$BUCKET/athena-results/ \
  --query "QueryExecutionId" --output text)
aws athena wait query-execution-complete --query-execution-id $QUERY_ID
aws athena get-query-results --query-execution-id $QUERY_ID \
  --query "ResultSet.Rows[1].Data[0].VarCharValue"
# Expected: row count > 0
```

---

## 5. Expected Successful Outputs

**CLI — describe-cluster:**
```json
{ "Status": "WAITING", "Name": "handson-spark-cluster", "MasterDNS": "ec2-xxx.compute-1.amazonaws.com" }
```

**CLI — describe-step:**
```json
{ "State": "COMPLETED" }
```

**S3 output:**
```
processed/spark-output/part-00000-abc123.snappy.parquet
processed/spark-output/part-00001-abc123.snappy.parquet
```

---

## 6. Verification Checklist

- [ ] EMR cluster `handson-spark-cluster` Status = WAITING (ready)
- [ ] Master and core nodes running
- [ ] Spark script uploaded to S3 scripts/ prefix
- [ ] Spark step submitted and Status = COMPLETED
- [ ] Parquet output files exist in S3 processed/spark-output/
- [ ] Output queryable via Athena
- [ ] CloudWatch shows CoreNodesRunning > 0
- [ ] `terraform plan` shows no changes
