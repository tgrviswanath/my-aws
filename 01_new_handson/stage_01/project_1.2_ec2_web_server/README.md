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

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform implementation + screenshots checklist |
| `verify.md` | Console verification table, CLI checks, SSH hardening test, Terraform state, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Terraform — EC2, security group, key pair |
| `code/setup_nginx.sh` | EC2 user-data script — Nginx install, reverse proxy, SSH hardening |
| `docs/architecture.md` | Architecture diagrams and notes |

## Code

### `code/setup_nginx.sh` — EC2 user-data / setup script

**Option A — EC2 User Data (automatic on launch):**
Paste the contents of `setup_nginx.sh` into the EC2 "User data" field when launching an instance.

**Option B — Run manually on an existing instance:**
```bash
# Copy to EC2
scp code/setup_nginx.sh ec2-user@<public-ip>:~/

# Run on the instance
ssh ec2-user@<public-ip>
sudo bash setup_nginx.sh
```

What it does:
- Installs Nginx (supports Amazon Linux 2, AL2023, Ubuntu)
- Creates a static site with instance metadata (ID, AZ, IP)
- Adds a `/health` endpoint returning `{"status":"healthy"}`
- Configures reverse proxy to port 3000 (commented out — uncomment for your app)
- Adds security headers (X-Frame-Options, CSP, HSTS)
- Enables Gzip compression
- Hardens SSH (no root login, key-only auth)
- Sets up log rotation
