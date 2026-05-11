# Project 1.4 — RDS MySQL Deployment

## What This Does
Deploys a managed MySQL database on RDS, connects to it from an EC2 instance, and configures backups and Multi-AZ.

## Architecture
```
EC2 (bastion/app) → Security Group → RDS MySQL (private subnet)
```

## Services Used
| Service | Role |
|---------|------|
| RDS | Managed MySQL database |
| EC2 | Connect to RDS (bastion host) |
| Security Groups | Control DB access |
| Parameter Groups | MySQL configuration |

## Key Concepts
| Concept | Description |
|---------|-------------|
| Multi-AZ | Standby replica in another AZ for failover |
| Automated backups | Daily snapshots retained for 7 days |
| Parameter group | MySQL config (max_connections, charset, etc.) |
| Subnet group | Which subnets RDS can use |
| Private subnet | RDS should never be publicly accessible |

## How to Deploy
```bash
cd terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

## Lessons Learned
- RDS should always be in a private subnet — never expose port 3306 to the internet
- Multi-AZ is for high availability, not read scaling (use Read Replicas for that)
- Automated backups are enabled by default — set retention to at least 7 days
- Use Secrets Manager (Project 8.1) to store DB credentials — never hardcode them
- `db.t3.micro` is free tier eligible
