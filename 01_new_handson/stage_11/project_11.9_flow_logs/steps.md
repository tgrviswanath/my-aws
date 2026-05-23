# Steps — Project 11.9 VPC Flow Logs Analysis

## Phase 1 — Console

### 1.1 Create VPC and EC2
- Use VPC from Project 11.1 or create a new one
- Launch an EC2 instance with a public IP for generating traffic

### 1.2 Create IAM Role for Flow Logs
1. **IAM** → **Roles** → **Create role**
2. Trusted entity: VPC Flow Logs service (`vpc-flow-logs.amazonaws.com`)
3. Attach policy: `CloudWatchLogsFullAccess` (or custom policy below)
4. Name: `role-flowlogs-11-9`

Custom policy (least privilege):
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams"
    ],
    "Resource": "*"
  }]
}
```

### 1.3 Enable Flow Logs → CloudWatch
1. **VPC** → select your VPC → **Flow logs** tab → **Create flow log**
2. Filter: All (accept + reject)
3. Max aggregation interval: 1 minute
4. Destination: CloudWatch Logs
5. Log group: `/vpc/flowlogs/11-9`
6. IAM role: `role-flowlogs-11-9`
7. Log format: Default (or custom)
8. Create

### 1.4 Enable Flow Logs → S3
1. Create S3 bucket: `flowlogs-11-9-<account-id>`
2. Create another flow log on the same VPC
3. Destination: S3 bucket
4. S3 bucket ARN: `arn:aws:s3:::flowlogs-11-9-<account-id>`
5. Log file format: Parquet (better for Athena)

---

## Phase 2 — AWS CLI

```bash
VPC_ID=<vpc-id>
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET="flowlogs-11-9-$ACCOUNT_ID"

# Create S3 bucket
aws s3 mb s3://$BUCKET

# Create IAM role for CloudWatch flow logs
aws iam create-role \
  --role-name role-flowlogs-11-9 \
  --assume-role-policy-document '{
    "Version":"2012-10-17",
    "Statement":[{
      "Effect":"Allow",
      "Principal":{"Service":"vpc-flow-logs.amazonaws.com"},
      "Action":"sts:AssumeRole"
    }]
  }'

aws iam put-role-policy \
  --role-name role-flowlogs-11-9 \
  --policy-name flowlogs-policy \
  --policy-document '{
    "Version":"2012-10-17",
    "Statement":[{
      "Effect":"Allow",
      "Action":["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],
      "Resource":"*"
    }]
  }'

ROLE_ARN=$(aws iam get-role --role-name role-flowlogs-11-9 \
  --query "Role.Arn" --output text)

# Create flow log to CloudWatch
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids $VPC_ID \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /vpc/flowlogs/11-9 \
  --deliver-logs-permission-arn $ROLE_ARN \
  --max-aggregation-interval 60

# Create flow log to S3
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids $VPC_ID \
  --traffic-type ALL \
  --log-destination-type s3 \
  --log-destination arn:aws:s3:::$BUCKET \
  --max-aggregation-interval 60
```

---

## Phase 3 — Terraform

```bash
cd terraform && terraform init && terraform apply
```

---

## Phase 4 — Verify

```bash
# 1. Confirm flow logs are active
aws ec2 describe-flow-logs \
  --filter "Name=resource-id,Values=$VPC_ID" \
  --query "FlowLogs[*].{ID:FlowLogId,Status:FlowLogStatus,Dest:LogDestinationType}"
# Expected: ACTIVE for both CW and S3

# 2. Generate traffic — SSH to EC2, make some requests
ssh -i key.pem ec2-user@<PUBLIC_IP>
curl https://example.com
curl https://google.com
# Also try a blocked port to generate REJECT records:
nc -zv <SOME_IP> 9999   # should be blocked → generates REJECT log

# 3. Wait 2-5 minutes for logs to appear, then check CloudWatch
aws logs describe-log-streams \
  --log-group-name /vpc/flowlogs/11-9 \
  --query "logStreams[*].logStreamName"

# 4. Get recent log events
aws logs get-log-events \
  --log-group-name /vpc/flowlogs/11-9 \
  --log-stream-name <stream-name> \
  --limit 20 \
  --query "events[*].message"
```

---

## Phase 5 — Test (CloudWatch Insights Queries)

```bash
# Open CloudWatch → Log Insights → select /vpc/flowlogs/11-9

# Query 1: Top 10 source IPs by traffic volume
# fields srcAddr, bytes
# stats sum(bytes) as totalBytes by srcAddr
# sort totalBytes desc
# limit 10

# Query 2: All REJECTED traffic (security analysis)
# fields srcAddr, dstAddr, srcPort, dstPort, protocol, action
# filter action = "REJECT"
# sort @timestamp desc
# limit 50

# Query 3: Traffic to a specific destination port
# fields srcAddr, dstAddr, dstPort, bytes, action
# filter dstPort = 22
# sort @timestamp desc

# Query 4: Count accepts vs rejects
# stats count(*) as total by action

# Run via CLI:
aws logs start-query \
  --log-group-name /vpc/flowlogs/11-9 \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields srcAddr, dstAddr, action | filter action = "REJECT" | limit 20'

QUERY_ID=$(aws logs start-query ... --query "queryId" --output text)
sleep 5
aws logs get-query-results --query-id $QUERY_ID

# Run automated checker
python code/flowlog_checker.py --vpc-id $VPC_ID --log-group /vpc/flowlogs/11-9
```

### Verification Checklist
- [ ] Flow log to CloudWatch: status = ACTIVE
- [ ] Flow log to S3: status = ACTIVE
- [ ] Log streams appear in CloudWatch after generating traffic
- [ ] Log records contain: srcaddr, dstaddr, srcport, dstport, action
- [ ] ACCEPT records visible for allowed traffic
- [ ] REJECT records visible for blocked traffic
- [ ] CloudWatch Insights query returns results
- [ ] S3 bucket contains log files (after ~10 min)

---

## Teardown
```bash
terraform destroy
aws s3 rm s3://$BUCKET --recursive
aws s3 rb s3://$BUCKET
```
