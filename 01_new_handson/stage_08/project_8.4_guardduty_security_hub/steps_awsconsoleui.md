# Project 8.4 — GuardDuty + Security Hub: Console UI Steps
## Visual Walkthrough for AWS Management Console

---

## Prerequisites Check

- [ ] IAM permissions: `guardduty:*`, `securityhub:*`, `events:*`
- [ ] Region: **US East (N. Virginia) us-east-1**
- [ ] Note the 30-day free trial for both services
- [ ] EC2 instances or active AWS usage (GuardDuty analyzes real traffic)

---

## Step 1 — Enable GuardDuty

1. Search for **GuardDuty** in the console
2. Click **Get Started**
3. Review what GuardDuty analyzes (VPC Flow Logs, CloudTrail, DNS queries)
4. Note the **30-day free trial** message prominently displayed
5. Click **Enable GuardDuty**
6. GuardDuty is now active — begins analyzing in background

📸 Screenshot: GuardDuty welcome page with 30-day free trial badge and Enable button

**Decision Point: Enable optional protection plans?**
- **S3 Protection** ✅ — monitors S3 data plane operations (recommend enabling)
- **EKS Protection** — only if you use EKS
- **Lambda Protection** — only if you use Lambda
- **RDS Protection** — monitors RDS login activity
- **Malware Protection** — scans EBS volumes (additional cost)

---

## Step 2 — View GuardDuty Dashboard

1. You land on the **Findings** page (empty if new account)
2. Left nav shows:
   - **Summary** — overview dashboard with finding counts by severity
   - **Findings** — list of all active findings
   - **Accounts** — for multi-account (Organizations) setup
   - **Lists** — trusted IP lists and threat intelligence
   - **Settings** — finding frequency, S3 export, suppression rules
3. Click **Summary** to see the threat severity chart

📸 Screenshot: GuardDuty summary dashboard showing finding count by severity level

---

## Step 3 — Generate Sample Findings (Testing)

1. In left nav: **Settings**
2. Scroll to **Sample findings** section
3. Click **Generate sample findings**
4. Confirm by clicking **Generate**
5. Wait ~30 seconds
6. Navigate to **Findings** — you'll see ~50+ sample findings
7. Filter by **Severity**: HIGH → see SSH brute force, crypto mining, C&C activity samples

📸 Screenshot: Findings list with sample HIGH severity findings colored red

---

## Step 4 — Inspect a Finding

1. Click on any HIGH severity finding
2. **Finding details** panel shows:
   - **Finding type** (e.g., `UnauthorizedAccess:EC2/SSHBruteForce`)
   - **Severity**: 2 (Low) to 9 (Critical)
   - **Count**: How many times detected
   - **Resource**: Affected EC2 instance or IAM role
   - **Action details**: Source IP, port, protocol
   - **Evidence**: How GuardDuty determined this was malicious
3. Note the **Actor** section — shows attacker IP, country, organization

📸 Screenshot: Finding detail panel with SSH brute force finding showing attacker IP details

---

## Step 5 — Enable Security Hub

1. Search for **Security Hub** in the console
2. Click **Go to Security Hub**
3. **Enable Security Hub** page shows available standards:
   - ✅ **AWS Foundational Security Best Practices v1.0.0** (recommended)
   - ✅ **CIS AWS Foundations Benchmark v1.2.0**
   - ❌ **PCI DSS v3.2.1** (only if needed for compliance)
4. Select the first two standards
5. Click **Enable Security Hub**
6. Initial processing takes 2-10 minutes

📸 Screenshot: Security Hub setup page with security standards checkboxes

---

## Step 6 — Explore Security Hub Summary

1. Navigate to **Security Hub** → **Summary**
2. **Security score** shows percentage compliance per standard
3. **Insights** section shows pre-built aggregations:
   - "AWS resources with the most findings"
   - "EC2 instances with the most findings"
4. **Latest findings** shows recent HIGH/CRITICAL findings
5. GuardDuty findings automatically appear here (integration enabled by default)

📸 Screenshot: Security Hub summary with security score gauges and recent findings

---

## Step 7 — View Compliance by Standard

1. Click **Security standards** in left nav
2. Click on **AWS Foundational Security Best Practices**
3. See controls grouped by service (EC2, S3, IAM, RDS...)
4. **Failed** controls shown in red — click any to see which resources fail
5. Common initial failures:
   - `IAM.4` — Hardware MFA not enabled for root
   - `CloudTrail.1` — CloudTrail not enabled in all regions
   - `EC2.2` — VPC default security group blocks all traffic

📸 Screenshot: Security standard compliance view with failed controls listed

**Decision Point: Which findings to fix first?**
- Fix CRITICAL first (9.0-10.0 severity)
- Fix HIGH next (7.0-8.9 severity)
- Review and suppress intentional configurations

---

## Step 8 — Set Up EventBridge Auto-Remediation

1. Navigate to **Amazon EventBridge** → **Rules**
2. Click **Create rule**
3. **Name**: `guardduty-high-severity-response`
4. **Description**: `Auto-respond to HIGH GuardDuty findings`
5. **Rule type**: `Rule with an event pattern`
6. Click **Next**
7. **Event pattern**:
   - **Event source**: AWS services
   - **Service**: GuardDuty
   - **Event type**: GuardDuty Finding
   - Add custom pattern to filter HIGH severity:
```json
{
  "source": ["aws.guardduty"],
  "detail-type": ["GuardDuty Finding"],
  "detail": {
    "severity": [{"numeric": [">=", 7.0]}]
  }
}
```
8. Click **Next** → **Target**: Lambda function `guardduty-auto-remediate`
9. Click **Create rule**

📸 Screenshot: EventBridge rule creation with GuardDuty event pattern and Lambda target

---

## Step 9 — Configure Finding Archive and Suppression

1. In **GuardDuty** → **Findings**
2. Select sample findings you want to suppress
3. Click **Actions** → **Archive** (hides from active view)
4. For systematic suppression: **Settings** → **Suppression rules**
5. Click **Add suppression rule**:
   - Rule name: `suppress-sample-findings`
   - Finding type: contains `[SAMPLE]`
6. Sample findings auto-archived going forward

📸 Screenshot: Suppression rule configuration with finding type filter

---

## Step 10 — Enable Threat Intelligence

1. In GuardDuty left nav: **Lists**
2. Two types of lists:
   - **Trusted IP list** — IPs to never flag as malicious (your office, VPN)
   - **Threat IP list** — Known bad IPs to always alert on
3. Click **Add a trusted IP list**:
   - **List name**: `office-ips`
   - **List format**: Plaintext
   - **Location**: S3 URL of your IP list file
4. Click **Add list**

📸 Screenshot: GuardDuty Lists page with trusted IPs and threat intel sections

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| No findings after enabling | Account has no traffic | Generate sample findings (Step 3) |
| Security Hub shows 0 findings from GuardDuty | Integration not configured | Security Hub → Integrations → Enable GuardDuty |
| EventBridge rule not firing | Rule disabled or wrong event pattern | Check rule state, test with sample finding |
| Security score is 0% | Processing not complete | Wait 10-30 minutes for initial scan |
| Free trial ended unexpectedly | 30-day per account, not per user | Check GuardDuty → Settings → Trial status |

---

## Console Navigation Quick Reference

```
AWS Console
├── GuardDuty
│   ├── Summary          → Threat overview dashboard
│   ├── Findings         → All findings, filter by severity
│   ├── Accounts         → Multi-account management
│   ├── Lists            → Trusted/threat IP lists
│   └── Settings         → Detector config, export findings
│
└── Security Hub
    ├── Summary          → Security posture overview
    ├── Findings         → All aggregated findings
    ├── Insights         → Grouped finding views
    ├── Security standards → CIS, FSBP compliance scores
    ├── Integrations     → Connect GuardDuty, Macie, Config
    └── Settings         → Finding aggregation, exports
```
