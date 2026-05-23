# Verification & Validation — Project 7.2 Centralized Logging Platform

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| OpenSearch Domain | OpenSearch → Domains | `handson-logs`, Status = **Active** |
| Kinesis Firehose | Kinesis → Delivery Streams | `handson-log-delivery`, Status = **Active** |
| CloudWatch Subscription Filter | CloudWatch → Log Groups → `/ecs/handson-flask-api` → Subscription filters | Filter to Firehose listed |
| S3 Backup Bucket | S3 → Buckets | `handson-log-backup-*` exists |
| Kibana | OpenSearch → Domains → Kibana URL | Kibana login page loads |

📸 Screenshot: OpenSearch domain in Active state  
📸 Screenshot: Firehose delivery stream active with delivery metrics  
📸 Screenshot: CloudWatch subscription filter configured on log group  
📸 Screenshot: Kibana Discover showing log entries

---

## 2. AWS CLI Verification

```bash
# 2.1 OpenSearch domain status
aws opensearch describe-domain \
  --domain-name handson-logs \
  --query "DomainStatus.{Status:Processing,Endpoint:Endpoint,EngineVersion:EngineVersion}"
# Expected: Processing=false (ready), Endpoint populated

# 2.2 Firehose delivery stream active
aws firehose describe-delivery-stream \
  --delivery-stream-name handson-log-delivery \
  --query "DeliveryStreamDescription.{Status:DeliveryStreamStatus,Destination:Destinations[0].ExtendedS3DestinationDescription.BucketARN}"
# Expected: Status=ACTIVE

# 2.3 Subscription filter on log group
aws logs describe-subscription-filters \
  --log-group-name /ecs/handson-flask-api \
  --query "subscriptionFilters[*].{Name:filterName,Destination:destinationArn}"
# Expected: destination ARN contains firehose

# 2.4 Check Firehose delivery metrics (logs delivered)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Firehose \
  --metric-name DeliveryToElasticsearch.Success \
  --dimensions Name=DeliveryStreamName,Value=handson-log-delivery \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Sum \
  --query "Datapoints[*].{Time:Timestamp,Count:Sum}"
# Expected: Sum > 0 after generating traffic

# 2.5 Query OpenSearch directly
ENDPOINT=$(aws opensearch describe-domain \
  --domain-name handson-logs \
  --query "DomainStatus.Endpoint" --output text)

curl -u admin:Admin@1234! \
  "https://$ENDPOINT/ecs-logs-*/_count" \
  -H "Content-Type: application/json"
# Expected: {"count": N, ...} where N > 0

# 2.6 Search for recent logs
curl -u admin:Admin@1234! \
  "https://$ENDPOINT/ecs-logs-*/_search?size=3&sort=@timestamp:desc" \
  -H "Content-Type: application/json" | python3 -m json.tool
# Expected: hits.total.value > 0, log entries in hits.hits
```

---

## 3. Terraform State Verification

```bash
cd terraform

# 3.1 List all resources
terraform state list
# Expected:
# aws_opensearch_domain.logs
# aws_kinesis_firehose_delivery_stream.logs
# aws_cloudwatch_log_subscription_filter.ecs
# aws_s3_bucket.log_backup
# aws_iam_role.firehose
# aws_iam_role_policy.firehose

# 3.2 Inspect OpenSearch domain
terraform state show aws_opensearch_domain.logs
# Shows: domain_name, engine_version, cluster_config, endpoint

# 3.3 Confirm outputs
terraform output kibana_url
# Expected: https://ENDPOINT/_dashboards
terraform output opensearch_endpoint
# Expected: ENDPOINT (no https://)

# 3.4 No drift
terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — End-to-End Log Flow

```bash
# Step 1: Generate logs
ALB_URL="http://your-alb-dns.us-east-1.elb.amazonaws.com"
for i in {1..20}; do
  curl -s $ALB_URL/health > /dev/null
  curl -s $ALB_URL/nonexistent > /dev/null
done

# Step 2: Wait for Firehose buffer (60s default)
echo "Waiting 90s for Firehose to flush..."
sleep 90

# Step 3: Verify logs reached OpenSearch
ENDPOINT=$(aws opensearch describe-domain \
  --domain-name handson-logs \
  --query "DomainStatus.Endpoint" --output text)

curl -u admin:Admin@1234! \
  "https://$ENDPOINT/ecs-logs-*/_search" \
  -H "Content-Type: application/json" \
  -d '{"query":{"match":{"@message":"404"}},"size":3}' | python3 -m json.tool
# Expected: hits containing 404 log entries
```

---

## 5. Expected Successful Outputs

**CLI — describe-domain:**
```json
{ "Status": false, "Endpoint": "search-handson-logs-xxx.us-east-1.es.amazonaws.com", "EngineVersion": "OpenSearch_2.11" }
```

**OpenSearch _count:**
```json
{ "count": 142, "_shards": { "total": 5, "successful": 5 } }
```

**terraform output:**
```
kibana_url         = "https://search-handson-logs-xxx.us-east-1.es.amazonaws.com/_dashboards"
opensearch_endpoint = "search-handson-logs-xxx.us-east-1.es.amazonaws.com"
```

---

## 6. Verification Checklist

- [ ] OpenSearch domain `handson-logs` status = Active
- [ ] Firehose delivery stream `handson-log-delivery` status = ACTIVE
- [ ] CloudWatch subscription filter on `/ecs/handson-flask-api` → Firehose
- [ ] S3 backup bucket exists
- [ ] Kibana login page loads at `/_dashboards`
- [ ] OpenSearch `_count` returns count > 0 after traffic generation
- [ ] Firehose delivery metrics show Sum > 0
- [ ] Kibana Discover shows log entries with `@timestamp`
- [ ] Search for "404" returns error log entries
- [ ] `terraform plan` shows no changes
- [ ] `terraform state list` shows all resources
