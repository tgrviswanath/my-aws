# Verification & Validation — Project 11.9 VPC Flow Logs Analysis

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Flow Log (CloudWatch) | VPC → Your VPCs → Flow logs tab | Status = **Active**, Destination = CloudWatch |
| Flow Log (S3) | VPC → Your VPCs → Flow logs tab | Status = **Active**, Destination = S3 |
| Log Group | CloudWatch → Log Groups | `/vpc/flowlogs/11-9` exists |
| Log Streams | CloudWatch → Log Groups → Streams | Streams appear after generating traffic |
| S3 Bucket | S3 → Buckets | `flowlogs-11-9-<account-id>`, log files appear after ~10 min |
| IAM Role | IAM → Roles | `role-flowlogs-11-9` with CloudWatch Logs permissions |

📸 Screenshot: VPC Flow logs tab showing both flow logs as Active  
📸 Screenshot: CloudWatch Log Group `/vpc/flowlogs/11-9` with log streams  
📸 Screenshot: Sample log record showing srcaddr, dstaddr, action fields

---

## 2. AWS CLI Verification

```bash
# 2.1 Confirm flow logs are active
aws ec2 describe-flow-logs \
  --filter "Name=resource-id,Values=$VPC_ID" \
  --query "FlowLogs[*].{ID:FlowLogId,Status:FlowLogStatus,Dest:LogDestinationType,Group:LogGroupName}"
# Expected: FlowLogStatus=ACTIVE for both CW and S3

# 2.2 Generate traffic to produce log records
ssh -i key.pem ec2-user@<PUBLIC_IP>
curl https://example.com
nc -zv <SOME_IP> 9999   # blocked port → generates REJECT record

# 2.3 Wait 2-5 minutes, then check CloudWatch log streams
aws logs describe-log-streams \
  --log-group-name /vpc/flowlogs/11-9 \
  --query "logStreams[*].{Name:logStreamName,LastEvent:lastEventTimestamp}"
# Expected: at least 1 stream with recent timestamp

# 2.4 Read recent log events
aws logs get-log-events \
  --log-group-name /vpc/flowlogs/11-9 \
  --log-stream-name <stream-name> \
  --limit 10 \
  --query "events[*].message"
# Expected: flow log records with srcaddr, dstaddr, srcport, dstport, action

# 2.5 CloudWatch Insights — find REJECT records
aws logs start-query \
  --log-group-name /vpc/flowlogs/11-9 \
  --start-time $(date -d '1 hour ago' +%s 2>/dev/null || date -v-1H +%s) \
  --end-time $(date +%s) \
  --query-string 'fields srcAddr, dstAddr, dstPort, action | filter action = "REJECT" | limit 10'
# Capture queryId, then:
QUERY_ID=<query-id>
sleep 10
aws logs get-query-results --query-id $QUERY_ID \
  --query "results[*][*].{Field:field,Value:value}"
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_flow_log.cloudwatch
# aws_flow_log.s3
# aws_cloudwatch_log_group.flow_logs
# aws_iam_role.flow_logs
# aws_iam_role_policy.flow_logs
# aws_s3_bucket.flow_logs

terraform state show aws_flow_log.cloudwatch
# Shows: id, vpc_id, traffic_type=ALL, log_destination_type=cloud-watch-logs, flow_log_status=ACTIVE

terraform plan
# Expected: No changes.
```

---

## 4. Health Check — Log Record Format

A valid flow log record looks like:
```
2 123456789012 eni-0abc123 10.0.1.5 8.8.8.8 54321 443 6 10 840 1620000000 1620000060 ACCEPT OK
```

Fields: version, account-id, interface-id, srcaddr, dstaddr, srcport, dstport, protocol, packets, bytes, start, end, action, log-status

Confirm all fields are present:
```bash
aws logs get-log-events \
  --log-group-name /vpc/flowlogs/11-9 \
  --log-stream-name <stream> \
  --limit 1 \
  --query "events[0].message"
# Count the space-separated fields — should be 14 (default format)
```

---

## 5. Expected Successful Outputs

**CLI — describe-flow-logs:**
```json
[
  { "ID": "fl-0abc123", "Status": "ACTIVE", "Dest": "cloud-watch-logs", "Group": "/vpc/flowlogs/11-9" },
  { "ID": "fl-0def456", "Status": "ACTIVE", "Dest": "s3",               "Group": null }
]
```

**Sample log record (ACCEPT):**
```
2 123456789012 eni-0abc123 10.0.1.5 93.184.216.34 54321 443 6 5 420 1620000000 1620000060 ACCEPT OK
```

**Sample log record (REJECT):**
```
2 123456789012 eni-0abc123 203.0.113.5 10.0.1.5 12345 9999 6 1 40 1620000000 1620000060 REJECT OK
```

---

## 6. Verification Checklist

- [ ] Flow log to CloudWatch: status = ACTIVE
- [ ] Flow log to S3: status = ACTIVE
- [ ] IAM role `role-flowlogs-11-9` has CloudWatch Logs permissions
- [ ] Log group `/vpc/flowlogs/11-9` exists in CloudWatch
- [ ] Log streams appear after generating traffic (wait 2-5 min)
- [ ] Log records contain all 14 default fields
- [ ] ACCEPT records visible for allowed traffic
- [ ] REJECT records visible for blocked traffic
- [ ] CloudWatch Insights query returns REJECT records
- [ ] S3 bucket contains log files (after ~10 min)
- [ ] `terraform plan` shows no changes
