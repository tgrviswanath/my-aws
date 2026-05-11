# Project 1.2 — Linux Web Server on EC2

## What This Does
Launches an EC2 instance, installs Nginx, configures it as a reverse proxy, and secures SSH access.

## Architecture
```
Internet → Security Group (port 80/443/22) → EC2 (Nginx) → App
```

## Services Used
| Service | Role |
|---------|------|
| EC2 | Virtual machine running Linux |
| Security Groups | Firewall — control inbound/outbound traffic |
| Key Pair | SSH authentication |

## How to Deploy
```bash
cd terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

## Lessons Learned
- Security groups are stateful — inbound rules automatically allow return traffic
- Never open port 22 to `0.0.0.0/0` in production — restrict to your IP
- Use `t3.micro` (free tier eligible) for learning
- User data scripts run once at first boot — useful for automated setup
- Always use key pairs, never password-based SSH
