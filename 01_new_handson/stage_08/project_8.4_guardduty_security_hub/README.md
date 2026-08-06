# Project 8.4 — GuardDuty + Security Hub Threat Detection

**Stage:** 08 | **Level:** Intermediate | **Est. Time:** 90 min | **Cost:** GuardDuty ~$1-5/month; Security Hub $0.0010/finding after 10K free

Enable GuardDuty in us-east-1 to detect threats against VPC, DNS, and CloudTrail data streams.
Generate sample findings to exercise the full detection pipeline, then activate Security Hub to
aggregate GuardDuty findings alongside CIS AWS Foundations benchmark checks into a unified security
score. An EventBridge rule automatically routes any HIGH or CRITICAL finding to an SNS topic that
delivers an email alert within seconds of detection.

---

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| Amazon GuardDuty | Threat detection across VPC Flow Logs, DNS, CloudTrail | ~$1-5/month (volume-based) |
| AWS Security Hub | Aggregates findings; runs CIS benchmark; unified security score | $0.0010/finding after 10K/month free |
| Amazon EventBridge | Routes HIGH/CRITICAL findings to SNS within seconds | $1/million events |
| Amazon SNS | Delivers email alerts for HIGH/CRITICAL findings | $0.50/million emails |
| AWS IAM | EventBridge execution role to publish to SNS | Free |

---

## Input / Output

### Input

| Parameter | Value | Notes |
|---|---|---|
| GuardDuty region | us-east-1 | Must be enabled per-region |
| Sample findings | All finding types | Simulates real attack scenarios |
| Security Hub standard | CIS AWS Foundations Benchmark v1.4 | IAM, logging, networking checks |
| EventBridge filter | severity >= HIGH (7.0+) | Catches HIGH and CRITICAL |
| SNS email | security-alerts@example.com | Confirm subscription before testing |

### Output

| Artifact | Description |
|---|---|
| GuardDuty detector | Detector ID in us-east-1, analyzing VPC/DNS/CloudTrail continuously |
| Sample findings | 45+ finding types generated for pipeline testing (e.g., UnauthorizedAccess:EC2/SSHBruteForce) |
| Security Hub score | Aggregated security posture score 0-100 across all enabled standards |
| CIS benchmark results | Pass/fail status for 43 CIS controls covering IAM password policy, MFA, logging |
| EventBridge → SNS alert | Email notification within ~30 seconds of HIGH/CRITICAL finding |

---

## Architecture

```
VPC Flow Logs  CloudTrail  DNS Logs
      |              |          |
      +------+--------+---------+
             |
             | (analyzed automatically — no manual setup)
             v
     +----------------+
     | Amazon GuardDuty|
     | Detector        |  generates findings (ASFF format)
     | (us-east-1)     |
     +----------------+
             |
             | findings imported
             v
     +----------------+
     | AWS Security Hub|  <-- CIS Benchmark checks run here
     | Security Score  |
     +----------------+
             |
             | all findings
             v
     +----------------+
     | Amazon          |
     | EventBridge     |  rule: severity >= 7.0 (HIGH/CRITICAL)
     +----------------+
             |
             | matched events only
             v
     +----------------+
     | Amazon SNS      |
     | Topic           |  --> email: security-alerts@example.com
     +----------------+
```

---

## Quick Start

```cmd
REM 1. Enable GuardDuty detector in us-east-1
aws guardduty create-detector ^
  --enable --finding-publishing-frequency FIFTEEN_MINUTES --region us-east-1

REM 2. Store detector ID
FOR /F "tokens=*" %i IN ('aws guardduty list-detectors --region us-east-1 --query detectorIds[0] --output text') DO SET DETECTOR_ID=%i

REM 3. Generate sample findings to exercise the pipeline
aws guardduty create-sample-findings --detector-id %DETECTOR_ID% --region us-east-1

REM 4. Enable Security Hub with CIS AWS Foundations standard
aws securityhub enable-security-hub --enable-default-standards --region us-east-1

REM 5. Create SNS topic and subscribe your email
aws sns create-topic --name guardduty-high-critical-alerts --region us-east-1
aws sns subscribe ^
  --topic-arn arn:aws:sns:us-east-1:123456789012:guardduty-high-critical-alerts ^
  --protocol email --notification-endpoint security-alerts@example.com

REM 6. Create EventBridge rule for HIGH/CRITICAL findings
aws events put-rule ^
  --name guardduty-high-critical --event-pattern file://eventbridge-pattern.json ^
  --state ENABLED --region us-east-1

REM 7. Add SNS as EventBridge target
aws events put-targets ^
  --rule guardduty-high-critical ^
  --targets Id=sns-target,Arn=arn:aws:sns:us-east-1:123456789012:guardduty-high-critical-alerts ^
  --region us-east-1
```

---

## Data Flow

1. GuardDuty detector is enabled — it analyzes VPC Flow Logs, Route 53 DNS logs, and CloudTrail management events automatically with no separate log enablement needed.
2. Sample findings are created via API — they are real ASFF objects and trigger the identical pipeline that genuine threats trigger.
3. GuardDuty publishes findings to Security Hub via the native integration using ASFF format.
4. Security Hub aggregates findings, evaluates CIS AWS Foundations benchmark controls, and updates the account security score.
5. Every finding also generates an EventBridge event of type `aws.guardduty` or `aws.securityhub`.
6. EventBridge evaluates the finding's `severity.normalized` field — values ≥70 (HIGH) match the rule.
7. EventBridge publishes the matched finding JSON to the SNS topic; SNS delivers an email within ~30 seconds.

---

## Project Files

| File | Description |
|---|---|
| `eventbridge-pattern.json` | EventBridge event pattern filtering severity HIGH and CRITICAL from GuardDuty |
| `test_sample_findings.sh` | CLI script to generate samples and poll for findings in Security Hub |
| `query_findings.py` | Python script using boto3 to list and filter findings by severity and type |
| `cis_benchmark_report.sh` | CLI commands to export CIS control pass/fail status from Security Hub |
| `sns_policy.json` | SNS topic policy allowing EventBridge to publish to the topic |

---

## Lessons Learned

- GuardDuty analyzes VPC Flow Logs, DNS query logs, and CloudTrail management events automatically — you do not need to enable or configure those log sources separately.
- Sample findings (`create-sample-findings`) are real ASFF finding objects that flow through EventBridge and Security Hub identically to genuine threats — use them to validate the alerting pipeline before going live.
- Security Hub uses ASFF (Amazon Security Finding Format) as a standard schema across all integrated services — consistent field names like `severity.normalized` and `types` make cross-service queries straightforward.
- GuardDuty is regional — a detector in us-east-1 has no visibility into activity in eu-west-1; enable it in every region or use GuardDuty multi-account/Organizations to centralize findings.
- GuardDuty findings are retained for 90 days in the service — export to S3 or Security Hub for longer retention.
- CIS AWS Foundations benchmark in Security Hub covers 43 controls including IAM password policy, MFA on root, CloudTrail enabled, and security group restrictions — many checks are automatically flagged on initial enablement.
- EventBridge `severity.normalized` values map to: LOW < 40, MEDIUM 40-69, HIGH 70-89, CRITICAL 90-100 — use `{ ">=": 70 }` in numeric matching to catch both HIGH and CRITICAL with a single rule.
