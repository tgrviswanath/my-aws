# Steps — Project 8.4 GuardDuty + Security Hub

## Phase 1 — Deploy

```bash
cd terraform
terraform init
terraform apply -var="alert_email=your@email.com" -auto-approve
terraform output guardduty_detector_id
```

---

## Phase 2 — Generate Sample GuardDuty Findings

```bash
DETECTOR_ID=$(terraform output -raw guardduty_detector_id)

# Generate sample findings (safe — no real threat)
aws guardduty create-sample-findings \
  --detector-id $DETECTOR_ID \
  --finding-types \
    "UnauthorizedAccess:EC2/SSHBruteForce" \
    "CryptoCurrency:EC2/BitcoinTool.B!DNS" \
    "Recon:IAMUser/MaliciousIPCaller"

# List findings
aws guardduty list-findings \
  --detector-id $DETECTOR_ID \
  --finding-criteria '{"Criterion":{"severity":{"Gte":7}}}' \
  --query "FindingIds" --output table
```

---

## Phase 3 — View Findings in Console

```
1. GuardDuty → Findings
2. Filter by severity: HIGH, CRITICAL
3. Click a finding → see full details:
   - What happened
   - Which resource was affected
   - Recommended remediation
4. Mark as archived (suppress known-safe findings)
```

---

## Phase 4 — Security Hub Dashboard

```
1. Security Hub → Summary
2. See: Security score, failed checks by standard
3. Security Hub → Findings → filter by CRITICAL
4. Security Hub → Standards → CIS AWS Foundations
   → See which checks are passing/failing
```

---

## Phase 5 — Verify Alert Email

```bash
# The sample findings should trigger the EventBridge rule
# and send an email via SNS

# Check EventBridge rule was triggered
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name TriggeredRules \
  --dimensions Name=RuleName,Value=handson-guardduty-high-severity \
  --start-time $(date -d '1 hour ago' --iso-8601=seconds) \
  --end-time $(date --iso-8601=seconds) \
  --period 3600 \
  --statistics Sum
```

---

## Phase 6 — Investigate a Finding

```bash
# Get full finding details
FINDING_ID="your-finding-id"
aws guardduty get-findings \
  --detector-id $DETECTOR_ID \
  --finding-ids $FINDING_ID \
  | python3 -m json.tool
```

---

## Screenshots to Take
- [ ] GuardDuty enabled with all data sources
- [ ] Sample findings generated (HIGH severity)
- [ ] Security Hub dashboard with security score
- [ ] CIS Foundations standard showing failed checks
- [ ] Alert email received from EventBridge → SNS
- [ ] Finding details showing affected resource and remediation
