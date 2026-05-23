# Verification & Validation — Project 7.3 AWS X-Ray Distributed Tracing

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| X-Ray Service Map | X-Ray → Service Map | Visual graph showing ALB → Flask API → DynamoDB |
| X-Ray Traces | X-Ray → Traces | Traces listed with duration and status |
| X-Ray Groups | X-Ray → Groups | Default group active |
| ECS Task Definition | ECS → Task Definitions | X-Ray daemon sidecar container present |
| IAM Role | IAM → Roles | ECS task role has `AWSXRayDaemonWriteAccess` |
| Sampling Rules | X-Ray → Sampling rules | Default rule active |

📸 Screenshot: X-Ray Service Map showing all services connected  
📸 Screenshot: Individual trace timeline (segments + subsegments)  
📸 Screenshot: DynamoDB subsegment showing query time  
📸 Screenshot: Error trace showing 404 response

---

## 2. AWS CLI Verification

```bash
# 2.1 Confirm X-Ray sampling rules exist
aws xray get-sampling-rules \
  --query "SamplingRuleRecords[*].SamplingRule.{Name:RuleName,Rate:FixedRate,Priority:Priority}"
# Expected: Default rule with FixedRate=0.05 (5%)

# 2.2 Get recent trace summaries
aws xray get-trace-summaries \
  --start-time $(date -d '1 hour ago' +%s 2>/dev/null || date -v-1H +%s) \
  --end-time $(date +%s) \
  --query "TraceSummaries[*].{Id:Id,Duration:Duration,Error:HasError,Fault:HasFault}" \
  --output table
# Expected: traces listed with durations

# 2.3 Get traces with errors
aws xray get-trace-summaries \
  --start-time $(date -d '1 hour ago' +%s 2>/dev/null || date -v-1H +%s) \
  --end-time $(date +%s) \
  --filter-expression 'error = true' \
  --query "TraceSummaries[*].{Id:Id,Duration:Duration,Error:HasError}"
# Expected: traces with HasError=true (from 404 requests)

# 2.4 Get high-latency traces
aws xray get-trace-summaries \
  --start-time $(date -d '1 hour ago' +%s 2>/dev/null || date -v-1H +%s) \
  --end-time $(date +%s) \
  --filter-expression 'responsetime > 0.5' \
  --query "TraceSummaries[*].{Id:Id,Duration:Duration}"
# Expected: slow traces listed

# 2.5 Fetch full trace detail
TRACE_ID=$(aws xray get-trace-summaries \
  --start-time $(date -d '1 hour ago' +%s 2>/dev/null || date -v-1H +%s) \
  --end-time $(date +%s) \
  --query "TraceSummaries[0].Id" --output text)

aws xray batch-get-traces \
  --trace-ids $TRACE_ID \
  --query "Traces[0].Segments[*].Document" --output text | python3 -m json.tool
# Expected: full segment JSON with subsegments

# 2.6 Confirm ECS task role has X-Ray permissions
TASK_ROLE=$(aws ecs describe-task-definition \
  --task-definition handson-flask-api \
  --query "taskDefinition.taskRoleArn" --output text)

aws iam list-attached-role-policies \
  --role-name $(echo $TASK_ROLE | cut -d'/' -f2) \
  --query "AttachedPolicies[*].PolicyName"
# Expected: AWSXRayDaemonWriteAccess listed
```

---

## 3. Terraform State Verification

```bash
cd terraform

# 3.1 List all resources
terraform state list
# Expected:
# aws_ecs_task_definition.app (updated with X-Ray sidecar)
# aws_iam_role_policy_attachment.xray
# aws_xray_sampling_rule.main (if custom rule created)

# 3.2 Inspect task definition for X-Ray sidecar
terraform state show aws_ecs_task_definition.app
# Shows: container_definitions containing xray-daemon container

# 3.3 No drift
terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Generate and Verify Traces

```bash
ALB_URL="http://your-alb-dns.us-east-1.elb.amazonaws.com"

# Generate mixed traffic
for i in {1..20}; do
  curl -s $ALB_URL/health > /dev/null
  curl -s $ALB_URL/items  > /dev/null
  curl -s -X POST $ALB_URL/items \
    -H "Content-Type: application/json" \
    -d '{"name": "Test Item '$i'"}' > /dev/null
done

# Generate errors
curl $ALB_URL/items/nonexistent-id

# Wait for traces to appear (15-30 seconds)
sleep 30

# Verify traces exist
TRACE_COUNT=$(aws xray get-trace-summaries \
  --start-time $(date -d '5 minutes ago' +%s 2>/dev/null || date -v-5M +%s) \
  --end-time $(date +%s) \
  --query "length(TraceSummaries)")
echo "Traces found: $TRACE_COUNT"
# Expected: > 0
```

---

## 5. Expected Successful Outputs

**CLI — get-trace-summaries:**
```json
[
  { "Id": "1-abc123-def456", "Duration": 0.045, "Error": false, "Fault": false },
  { "Id": "1-abc124-def457", "Duration": 0.123, "Error": true,  "Fault": false },
  { "Id": "1-abc125-def458", "Duration": 0.892, "Error": false, "Fault": false }
]
```

**Full trace document (key fields):**
```json
{
  "name": "handson-flask-api",
  "subsegments": [
    { "name": "DynamoDB", "namespace": "aws", "duration": 0.012 },
    { "name": "POST /items", "http": { "response": { "status": 201 } } }
  ]
}
```

---

## 6. Verification Checklist

- [ ] ECS task definition has X-Ray daemon sidecar container
- [ ] ECS task role has `AWSXRayDaemonWriteAccess` policy
- [ ] X-Ray sampling rules exist (default rule active)
- [ ] X-Ray Service Map shows: ALB → Flask API → DynamoDB
- [ ] Traces appear in X-Ray console after generating traffic
- [ ] Error traces visible (from 404 requests)
- [ ] Trace detail shows segments and subsegments with durations
- [ ] DynamoDB subsegment visible in trace timeline
- [ ] High-latency filter returns slow traces
- [ ] `terraform plan` shows no changes
