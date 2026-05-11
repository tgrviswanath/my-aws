# Project 8.4 — GuardDuty + Security Hub

## What This Does
Enables GuardDuty (threat detection) and Security Hub (centralized security findings) to continuously monitor for threats, misconfigurations, and security issues across your AWS account.

## GuardDuty Detects
- Compromised EC2 instances (crypto mining, C2 communication)
- Compromised IAM credentials (unusual API calls from new locations)
- S3 data exfiltration (unusual access patterns)
- Kubernetes threats (EKS audit log analysis)
- Malware on EC2 (EBS volume scanning)

## Security Hub Aggregates
- GuardDuty findings
- AWS Config compliance findings
- Inspector vulnerability findings
- IAM Access Analyzer findings
- Macie data classification findings

## How to Deploy
```bash
cd terraform
terraform init && terraform apply -var="alert_email=your@email.com"
```

## Lessons Learned
- GuardDuty uses ML to establish baselines — findings improve over time
- Finding severity: LOW (1-3.9), MEDIUM (4-6.9), HIGH (7-8.9), CRITICAL (9-10)
- Security Hub standards: CIS AWS Foundations, PCI DSS, AWS Foundational Security
- Suppress findings: mark known-safe findings as suppressed to reduce noise
- GuardDuty sample findings: generate test findings to verify alerting works
