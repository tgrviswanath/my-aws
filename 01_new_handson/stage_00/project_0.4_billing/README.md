# Project 0.4 — AWS Cost & Billing Fundamentals

## What This Does
Sets up billing protection before doing anything else in AWS. Prevents unexpected charges throughout the entire roadmap.

## ⚠️ Do This Before Any Other AWS Project

## Resources Created
- CloudWatch billing alarm ($10 threshold)
- SNS topic for email notifications
- AWS Budget ($20/month with 50%, 80%, 100% alerts)
- Cost allocation tag strategy

## Services Used
- AWS Billing Dashboard
- CloudWatch (us-east-1 only for billing metrics)
- SNS
- AWS Budgets
- Cost Explorer

## Free Tier Limits Reference
| Service | Free Tier |
|---------|-----------|
| EC2 | 750 hrs/month t2.micro or t3.micro |
| S3 | 5 GB storage, 20K GET, 2K PUT |
| RDS | 750 hrs/month db.t2.micro or db.t3.micro |
| Lambda | 1M requests/month, 400K GB-seconds |
| DynamoDB | 25 GB storage, 25 WCU, 25 RCU |
| CloudWatch | 10 metrics, 1M API requests |

## How to Deploy
```bash
cd terraform
terraform init
terraform plan -var="alert_email=your@email.com"
terraform apply -var="alert_email=your@email.com"
```

## Lessons Learned
- Billing metrics are only available in `us-east-1` — always set that region for billing alarms
- Free tier alerts and billing alarms are separate — enable both
- Tag every resource with `Project`, `Stage`, `Owner` from day one
- Cost Explorer takes 24 hours to activate after first use
