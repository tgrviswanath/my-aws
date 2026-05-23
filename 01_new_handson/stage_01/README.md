# Stage 01 — AWS Foundations (5 Projects)

Core AWS services hands-on — S3, EC2, IAM, RDS, and Python automation.
Every project uses all three methods: Console, CLI, and Terraform.

---

## Project Index

| # | Project | Key Services | Difficulty | Cost (2hr lab) |
|---|---------|-------------|-----------|----------------|
| 1.1 | [Static Website Hosting](project_1.1_static_website/) | S3, CloudFront, ACM, Route53 | 🟢 Beginner | ~$0.01 |
| 1.2 | [Linux Web Server on EC2](project_1.2_ec2_web_server/) | EC2, Security Groups, Key Pairs | 🟢 Beginner | ~$0.01 |
| 1.3 | [IAM Security Foundations](project_1.3_iam/) | IAM Users, Groups, Roles, Policies | 🟢 Beginner | Free |
| 1.4 | [RDS MySQL Deployment](project_1.4_rds_mysql/) | RDS, EC2, Security Groups | 🟢 Beginner | ~$0.02 |
| 1.5 | [Python AWS Automation](project_1.5_python_automation/) | boto3, S3, EC2, RDS | 🟢 Beginner | ~$0.01 |

> ⚠️ Complete stage_00 project 0.4 (billing setup) before starting any project here.

---

## Each Project Contains

```
project_1.x_name/
├── README.md        — what it does, services used, lessons learned, file index
├── steps.md         — Console | CLI | Terraform phases + screenshots checklist
├── verify.md        — Console verification | CLI checks | Terraform state
│                      Health checks | Expected outputs | Verification checklist
├── cost_estimate.md — per-resource cost breakdown
├── code/            — runnable scripts and demos
├── terraform/       — Terraform configuration
└── docs/
    └── architecture.md
```

### verify.md covers (present in all 5 projects)

| Section | What it contains |
|---------|------------------|
| Console Verification | Table with exact navigation path, resource name, expected state + screenshot markers |
| CLI Verification | Commands with expected JSON/text outputs for each resource |
| Terraform State Verification | `terraform state list`, `terraform state show`, `terraform plan` no-drift check |
| Health Checks | Project-specific tests (OAC block, SSH hardening, permission denied, MySQL queries) |
| Expected Outputs | Actual JSON/text samples for every key command |
| Verification Checklist | Final pass/fail checklist |

---

## Recommended Order

```
1.3 → 1.2 → 1.4 → 1.1 → 1.5
```

- Do **1.3 first** — IAM setup is needed before creating other resources securely
- Do **1.2** — EC2 skills needed for 1.4 (RDS connection via bastion)
- Do **1.4** — RDS needed for 1.5 (backup_manager.py)
- Do **1.1** — S3 + CloudFront (independent)
- Do **1.5** — ties everything together with Python automation

---

## Quick Cost Reference

| Project | Key cost driver | Free tier? |
|---------|----------------|-----------|
| 1.1 Static Website | CloudFront requests, S3 storage | Mostly free tier |
| 1.2 EC2 Web Server | EC2 t3.micro hours | ✅ 750 hrs/month free |
| 1.3 IAM | No cost | ✅ Always free |
| 1.4 RDS MySQL | db.t3.micro hours | ✅ 750 hrs/month free |
| 1.5 Python Automation | S3 API calls | ✅ Mostly free tier |

**Always run `terraform destroy` after each lab.**
