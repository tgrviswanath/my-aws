# Verification & Validation — Project 8.4 GuardDuty + Security Hub

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| GuardDuty | GuardDuty → Summary | Status = **Enabled**, monitoring active |
| GuardDuty Findings | GuardDuty → Findings | Findings listed (or empty if clean account) |
| Security Hub | Security Hub → Summary | Status = **Enabled** |
| Security Hub Standards | Security Hub → Security standards | CIS AWS Foundations = **Enabled** |
| Security Hub Findings | Security Hub → Findings | Aggregated findings from all sources |
| SNS Alert | SNS → Topics | `handson-security-alerts` topic exists |
| EventBridge Rule | EventBridge → Rules | Rule routing GuardDuty findings to SNS |

📸 Screenshot: GuardDuty enabled with monitoring active  
📸 Screenshot: Security Hub summary showing enabled standards  
📸 Screenshot: Sample GuardDuty finding (after generating test finding)  
📸 Screenshot: security_monitor.py output

---

## 2. AWS CLI Verification

```bash
# 2.1 Confirm GuardDuty is enabled
DETECTOR_ID=$(aws guardduty list-detectors --query "DetectorIds[0]" --output text)
aws guardduty get-detector \
  --detector-id $DETECTOR_ID \
  --query "{Status:Status,FindingFrequency:FindingPublishingFrequency,UpdatedAt:UpdatedAt}"
# Expected: Status=ENABLED

# 2.2 Generate sample GuardDuty findings (test — no real threat)
aws guardduty create-sample-findings \
  --detector-id $DETECTOR_ID \
  --finding-types "UnauthorizedAccess:EC2/SSHBruteForce" "Recon:IAMUser/MaliciousIPCaller"
echo "Sample findings created — check GuardDuty console"

# 2.3 List GuardDuty findings
aws guardduty list-findings \
  --detector-id $DETECTOR_ID \
  --finding-criteria '{"Criterion":{"service.archived":{"Eq":["false"]}}}' \
  --query "FindingIds" | head -5
# Expected: finding IDs listed

# 2.4 Get finding details
FINDING_ID=$(aws guardduty list-findings \
  --detector-id $DETECTOR_ID \
  --query "FindingIds[0]" --output text)
aws guardduty get-findings \
  --detector-id $DETECTOR_ID \
  --finding-ids $FINDING_ID \
  --query "Findings[0].{Type:Type,Severity:Severity,Title:Title}"
# Expected: finding type, severity, title

# 2.5 Confirm Security Hub is enabled
aws securityhub describe-hub \
  --query "{HubArn:HubArn,SubscribedAt:SubscribedAt,AutoEnableControls:AutoEnableControls}"
# Expected: HubArn populated

# 2.6 List enabled Security Hub standards
aws securityhub describe-standards-subscriptions \
  --query "StandardsSubscriptions[*].{StandardsArn:StandardsArn,Status:StandardsStatus}"
# Expected: CIS and/or AWS Foundational Security = READY

# 2.7 Get Security Hub findings count
aws securityhub get-findings \
  --filters '{"RecordState":[{"Value":"ACTIVE","Comparison":"EQUALS"}]}' \
  --query "length(Findings)"
# Expected: number (may be 0 in clean account)

# 2.8 Run security monitor
python code/security_monitor.py
# Expected: findings report with severity breakdown
```

---

## 3. Terraform State Verification

```bash
cd terraform

# 3.1 List all resources
terraform state list
# Expected:
# aws_guardduty_detector.main
# aws_securityhub_account.main
# aws_securityhub_standards_subscription.cis
# aws_securityhub_standards_subscription.aws_foundational
# aws_sns_topic.security_alerts
# aws_sns_topic_subscription.email
# aws_cloudwatch_event_rule.guardduty_findings
# aws_cloudwatch_event_target.sns

# 3.2 Inspect GuardDuty detector
terraform state show aws_guardduty_detector.main
# Shows: enable=true, finding_publishing_frequency

# 3.3 No drift
terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — End-to-End Alert Flow

```bash
DETECTOR_ID=$(aws guardduty list-detectors --query "DetectorIds[0]" --output text)

# Step 1: Generate sample finding
aws guardduty create-sample-findings \
  --detector-id $DETECTOR_ID \
  --finding-types "UnauthorizedAccess:EC2/SSHBruteForce"

# Step 2: Wait for EventBridge to route to SNS (~30 seconds)
sleep 30

# Step 3: Verify finding appears in Security Hub
aws securityhub get-findings \
  --filters '{"Type":[{"Value":"TTPs/Initial Access/UnauthorizedAccess:EC2-SSHBruteForce","Comparison":"PREFIX"}]}' \
  --query "Findings[0].{Title:Title,Severity:Severity.Label,Source:ProductName}"
# Expected: finding from GuardDuty visible in Security Hub

# Step 4: Check email for SNS notification
echo "Check your email for the GuardDuty alert notification"

# Step 5: Archive sample findings (cleanup)
FINDING_IDS=$(aws guardduty list-findings \
  --detector-id $DETECTOR_ID \
  --finding-criteria '{"Criterion":{"type":{"Eq":["UnauthorizedAccess:EC2/SSHBruteForce"]}}}' \
  --query "FindingIds" --output json)
aws guardduty archive-findings \
  --detector-id $DETECTOR_ID \
  --finding-ids $(echo $FINDING_IDS | python3 -c "import sys,json; print(*json.load(sys.stdin))")
```

---

## 5. Expected Successful Outputs

**CLI — get-detector:**
```json
{ "Status": "ENABLED", "FindingFrequency": "SIX_HOURS", "UpdatedAt": "2024-01-01T00:00:00Z" }
```

**CLI — get-findings (sample):**
```json
{ "Type": "UnauthorizedAccess:EC2/SSHBruteForce", "Severity": 2.0, "Title": "EC2 instance is involved in SSH brute force attacks." }
```

**security_monitor.py output:**
```
=== Security Findings Report ===
GuardDuty Findings:
  LOW:    2 findings
  MEDIUM: 1 finding

Security Hub Findings:
  HIGH:   0 findings
  MEDIUM: 3 findings (Config compliance)

Overall Security Score: 7/10
```

---

## 6. Verification Checklist

- [ ] GuardDuty detector Status = ENABLED
- [ ] Security Hub enabled with CIS AWS Foundations standard = READY
- [ ] SNS topic `handson-security-alerts` exists
- [ ] Email subscription confirmed on SNS topic
- [ ] EventBridge rule routes GuardDuty findings to SNS
- [ ] Sample findings generated successfully
- [ ] Sample findings appear in GuardDuty console
- [ ] Sample findings propagate to Security Hub
- [ ] Email notification received for sample finding
- [ ] `security_monitor.py` runs and prints severity breakdown
- [ ] Sample findings archived after test
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
