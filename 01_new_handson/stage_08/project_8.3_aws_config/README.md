# Project 8.3 — AWS Config Compliance

**Stage:** 08 | **Level:** Intermediate | **Est. Time:** 90 min | **Cost:** ~$0.003/configuration item recorded

Enable AWS Config to continuously record every resource change in the account, enforce the built-in
`s3-bucket-public-read-prohibited` managed rule, and write a custom Lambda rule that flags any EC2
instance missing a required `Name` tag. An SSM Automation remediation action automatically applies
the `Name` tag to non-compliant instances so the environment self-heals without manual intervention.

---

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| AWS Config | Records resource configuration changes; evaluates compliance rules | $0.003/config item |
| AWS Lambda | Custom compliance rule — checks EC2 Name tag on each change event | $0.20/1M requests |
| AWS SSM Automation | Remediation action — runs AWS-AddTagsToResource on non-compliant EC2s | Free (standard) |
| Amazon S3 | Stores configuration snapshots and history stream | $0.023/GB |
| AWS IAM | Config service role; Lambda execution role; SSM remediation role | Free |

---

## Input / Output

### Input

| Parameter | Value | Notes |
|---|---|---|
| Recording scope | All supported resources | Global resources included |
| Managed rule | s3-bucket-public-read-prohibited | No parameters required |
| Custom rule name | ec2-required-name-tag | Lambda-backed rule |
| Required tag key | Name | Must be present on all EC2 instances |
| Remediation document | AWS-AddTagsToResource | SSM Automation document |
| Remediation tag value | auto-remediated | Applied when Name tag is missing |

### Output

| Artifact | Description |
|---|---|
| Config compliance dashboard | Shows COMPLIANT / NON_COMPLIANT count per rule across all resources |
| s3-bucket-public-read-prohibited | Any S3 bucket with public read ACL flagged NON_COMPLIANT immediately |
| ec2-required-name-tag Lambda | Returns COMPLIANT or NON_COMPLIANT based on presence of Name tag |
| SSM remediation | Automatically adds Name=auto-remediated tag to non-compliant EC2 instances |
| S3 snapshots | Configuration history and snapshots stored in config-bucket-123456789012 |

---

## Architecture

```
AWS Account Resources
(EC2, S3, IAM, RDS, ...)
        |
        | change events
        v
+----------------------+
|  AWS Config Recorder |  -- records every resource change
+----------------------+
        |
        |---> S3 Bucket (snapshots + stream)
        |
        v
+----------------------+
|  Config Rules        |
|                      |
|  [Managed Rule]      |  s3-bucket-public-read-prohibited
|  s3-bucket-public-   |  --> evaluates S3 buckets on change
|  read-prohibited     |
|                      |
|  [Custom Rule]       |  ec2-required-name-tag
|  Lambda-backed       |  --> invoked on EC2 config change
+----------------------+
        |
        | NON_COMPLIANT
        v
+----------------------+
|  SSM Automation      |
|  Remediation         |  AWS-AddTagsToResource
|  (auto-triggered)    |  adds Name=auto-remediated
+----------------------+
        |
        v
   EC2 Instance (now tagged)
```

---

## Quick Start

```cmd
REM 1. Create S3 bucket to store Config snapshots
aws s3api create-bucket --bucket config-bucket-123456789012 --region us-east-1

REM 2. Create Config recorder (record all supported resources)
aws configservice put-configuration-recorder ^
  --configuration-recorder name=default,roleARN=arn:aws:iam::123456789012:role/config-service-role ^
  --recording-group allSupported=true,includeGlobalResourceTypes=true

REM 3. Create delivery channel and start recording
aws configservice put-delivery-channel ^
  --delivery-channel name=default,s3BucketName=config-bucket-123456789012
aws configservice start-configuration-recorder --configuration-recorder-name default

REM 4. Enable managed rule: S3 buckets must not allow public read
aws configservice put-config-rule --config-rule file://s3-public-read-rule.json

REM 5. Deploy Lambda and register custom EC2 Name tag rule
aws lambda create-function ^
  --function-name ec2-required-name-tag ^
  --runtime python3.12 ^
  --role arn:aws:iam::123456789012:role/config-lambda-role ^
  --handler lambda_function.lambda_handler ^
  --zip-file fileb://ec2_tag_rule.zip
aws configservice put-config-rule --config-rule file://ec2-name-tag-rule.json

REM 6. Enable auto-remediation using SSM Automation
aws configservice put-remediation-configurations ^
  --remediation-configurations file://remediation-config.json
```

---

## Data Flow

1. EC2 instance is launched without a `Name` tag — Config recorder captures the change event.
2. Config invokes the `ec2-required-name-tag` Lambda with the configuration item JSON.
3. Lambda inspects `configurationItem.tags` — `Name` key is absent, returns `NON_COMPLIANT`.
4. Config updates the compliance dashboard: EC2 appears as NON_COMPLIANT under the rule.
5. SSM Automation remediation fires: `AWS-AddTagsToResource` adds `Name=auto-remediated` to the instance.
6. Config re-evaluates the now-tagged instance and marks it COMPLIANT.
7. S3 bucket with public read ACL is flagged by `s3-bucket-public-read-prohibited` — no remediation configured, stays flagged until manually corrected.

---

## Project Files

| File | Description |
|---|---|
| `lambda_function.py` | Custom Config rule — evaluates EC2 Name tag, returns COMPLIANT/NON_COMPLIANT |
| `s3-public-read-rule.json` | Config rule definition for s3-bucket-public-read-prohibited |
| `ec2-name-tag-rule.json` | Config rule definition referencing the Lambda ARN |
| `remediation-config.json` | SSM remediation configuration: AWS-AddTagsToResource parameters |
| `config-service-role.json` | IAM trust policy and permissions for the Config service role |
| `query_noncompliant.sh` | CLI script listing all non-compliant resources across all rules |

---

## Lessons Learned

- Config recorder must be started before any rules are active — rules only evaluate resources that have been recorded; pre-existing resources need a manual `start-config-rules-evaluation` call.
- AWS provides 180+ managed rules covering CIS benchmarks, PCI-DSS, and HIPAA best practices — all are maintained and updated by AWS without any action on your part.
- Custom Lambda rules receive the full configuration item JSON on every resource change or on a periodic schedule (1h, 3h, 6h, 12h, 24h) — choose change-triggered for real-time compliance.
- SSM Automation remediation uses `AWS-AddTagsToResource` document — the remediation role needs `ec2:CreateTags` and `ssm:StartAutomationExecution` permissions to succeed.
- Config is eventually consistent — after a resource changes, compliance status can lag 15–30 minutes; do not rely on real-time accuracy for security gating decisions.
- All configuration history and snapshots are stored in S3 — enable S3 Object Lock on the Config bucket to prevent tampering with the audit trail.
- Custom rules count as Lambda invocations — high-churn environments (frequent Auto Scaling) can generate thousands of evaluations per hour; use periodic schedule mode to control costs.
