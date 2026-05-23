# Stage 8 — Security & Compliance

> Master production-grade AWS security: secrets management, WAF, compliance automation, threat detection, audit logging, and Zero Trust architecture.

---

## Projects

| # | Project | Key Services | Difficulty |
|---|---------|-------------|-----------|
| 8.1 | Secrets Manager + Parameter Store | Secrets Manager, SSM Parameter Store, KMS | ⭐⭐ |
| 8.2 | WAF Application Protection | WAF v2, Managed Rule Groups, CloudWatch | ⭐⭐⭐ |
| 8.3 | AWS Config Compliance Automation | AWS Config, Config Rules, SNS, S3 | ⭐⭐⭐ |
| 8.4 | GuardDuty + Security Hub | GuardDuty, Security Hub, EventBridge, SNS | ⭐⭐⭐ |
| 8.5 | CloudTrail + SIEM Integration | CloudTrail, CloudWatch Logs, S3, Athena | ⭐⭐⭐ |
| 8.6 | Zero Trust Security Lab | IAM Identity Center, MFA, VPC Flow Logs | ⭐⭐⭐⭐ |

---

## Folder Structure

```
stage_08/
├── project_8.1_secrets_manager/
│   ├── src/secrets_client.py
│   ├── terraform/main.tf
│   ├── README.md  |  steps.md  |  verify.md ✅
├── project_8.2_waf/
│   ├── code/waf_tester.py
│   ├── terraform/main.tf
│   ├── README.md  |  steps.md  |  verify.md ✅
├── project_8.3_aws_config/
│   ├── code/compliance_checker.py
│   ├── terraform/main.tf
│   ├── README.md  |  steps.md  |  verify.md ✅
├── project_8.4_guardduty_security_hub/
│   ├── code/security_monitor.py
│   ├── terraform/main.tf
│   ├── README.md  |  steps.md  |  verify.md ✅
├── project_8.5_cloudtrail_siem/
│   ├── code/cloudtrail_analyzer.py
│   ├── terraform/main.tf
│   ├── README.md  |  steps.md  |  verify.md ✅
└── project_8.6_zero_trust/
    ├── code/zero_trust_checker.py
    ├── terraform/main.tf
    ├── README.md  |  steps.md  |  verify.md ✅
```

---

## Quick Start

```bash
cd project_8.1_secrets_manager/terraform
terraform init && terraform apply

# Verify
python src/secrets_client.py
cat verify.md
```

---

## Security Concepts Covered

| Concept | Project | Key Takeaway |
|---------|---------|-------------|
| Secrets management | 8.1 | Never hardcode — use Secrets Manager + SSM |
| WAF protection | 8.2 | OWASP Top 10 blocked by managed rule groups |
| Compliance as code | 8.3 | Config rules evaluate every resource change |
| Threat detection | 8.4 | GuardDuty ML baselines + Security Hub aggregation |
| Audit logging | 8.5 | CloudTrail records every API call — immutable |
| Zero Trust | 8.6 | Never trust network location — always verify identity |

---

## 7. Verification & Validation

Every project in Stage 8 has a `verify.md` covering:

- **AWS Console verification** — what to check and expected state for each resource
- **AWS CLI verification commands** — exact commands with expected outputs
- **Terraform state verification** — `terraform state list`, `terraform state show`, `terraform output`, `terraform plan`
- **Logs / monitoring checks** — confirm secrets accessible, WAF blocking attacks, Config rules evaluating
- **Expected successful outputs** — exact JSON / text output to compare against
- **Health check procedures** — end-to-end tests (WAF attack simulation, GuardDuty sample findings, CloudTrail lookup)
- **Verification checklist** — checkbox list to tick off before marking project complete

### Quick Verification Reference

| Project | Key CLI Check | Expected Result |
|---------|--------------|-----------------|
| 8.1 Secrets Manager | `aws secretsmanager get-secret-value --secret-id handson/db/credentials` | JSON with username/password |
| 8.2 WAF | `curl "http://<ALB>/?id=1'+OR+'1'='1"` | HTTP 403 |
| 8.3 Config | `aws configservice describe-compliance-by-config-rule` | COMPLIANT per rule |
| 8.4 GuardDuty | `aws guardduty get-detector --detector-id $ID` | Status=ENABLED |
| 8.5 CloudTrail | `aws cloudtrail get-trail-status --name handson-trail` | IsLogging=true |
| 8.6 Zero Trust | `python code/zero_trust_checker.py` | Score ≥ 80/100 |

---

## Key Lessons

- **Secrets Manager vs SSM**: Secrets Manager for credentials (rotation, versioning); SSM for config (free tier, hierarchy)
- **WAF Count mode first**: always test rules in Count mode before switching to Block — avoid false positives
- **Config rules**: evaluated on change AND on schedule — full audit trail of every configuration change
- **GuardDuty sample findings**: use `create-sample-findings` to test alerting without real threats
- **CloudTrail**: first trail is free for management events — enable in every account from day 1
- **Zero Trust score**: aim for 80+/100 — perfect score is unrealistic in real environments

---

## Certification Alignment

| Cert | Relevant Projects |
|------|------------------|
| AWS Security Specialty | 8.1, 8.2, 8.3, 8.4, 8.5, 8.6 |
| AWS Solutions Architect Professional | 8.1, 8.3, 8.4, 8.5 |
| AWS SysOps Administrator | 8.3, 8.4, 8.5 |
