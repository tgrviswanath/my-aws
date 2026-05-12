# Project 8.3 — AWS Config Compliance Automation

## What This Does
Enables AWS Config to continuously audit resource configurations against compliance rules. Automatically detects and alerts on non-compliant resources (e.g. unencrypted S3 buckets, public security groups, missing tags).

## Rules Configured
| Rule | Checks |
|------|--------|
| s3-bucket-server-side-encryption-enabled | All S3 buckets encrypted |
| restricted-ssh | No SG allows SSH from 0.0.0.0/0 |
| restricted-common-ports | No SG allows 3306/5432 from internet |
| required-tags | All EC2/RDS have required tags |
| rds-instance-public-access-check | No RDS publicly accessible |
| iam-password-policy | Password policy meets requirements |
| cloudtrail-enabled | CloudTrail is active |
| root-account-mfa-enabled | Root account has MFA |

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
```

## Lessons Learned
- AWS Config records every configuration change — full audit trail
- Conformance packs: bundle of rules for compliance frameworks (PCI-DSS, HIPAA, CIS)
- Auto-remediation: Config can trigger SSM Automation to fix non-compliant resources
- Config aggregator: view compliance across all accounts in an Organization
- Config rules are evaluated on change AND on a schedule (every 24h)

## Code

### `code/compliance_checker.py` — Check AWS Config compliance rules

```bash
pip install boto3

# Check all Config rules and report violations
python code/compliance_checker.py

# Use a specific region
python code/compliance_checker.py --region us-east-1

# Use a specific AWS profile
python code/compliance_checker.py --profile security-audit
```

What it shows:
- All Config rules with their compliance status (COMPLIANT / NON_COMPLIANT / NOT_APPLICABLE)
- Non-compliant resources grouped by rule
- Severity grouping (CRITICAL, HIGH, MEDIUM)
- Remediation hints for common violations
- Summary: X/Y rules compliant
