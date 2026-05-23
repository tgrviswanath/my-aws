# Project 2.4 — Route53 Advanced Routing

## What This Does
Configures advanced Route53 routing policies: failover, weighted, latency-based, and health checks. Demonstrates how DNS can be used as a traffic management layer.

## Routing Policies Covered

| Policy | Use Case |
|--------|---------|
| Simple | Single resource, no health checks |
| Weighted | A/B testing, gradual traffic shifts (e.g. 90/10 split) |
| Latency | Route users to the lowest-latency region |
| Failover | Active/passive — switch to backup if primary fails |
| Geolocation | Route based on user's country/continent |
| Health Check | Monitor endpoint and remove unhealthy resources |

## Services Used
- Route53 (hosted zone, records, health checks)
- CloudWatch (health check alarms)
- SNS (health check notifications)
- EC2 or ALB (endpoints being routed to)

## How to Deploy
```bash
cd terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

## Lessons Learned
- Health checks are billed separately (~$0.50/month each)
- Failover routing requires health checks on the primary record
- Weighted routing with weight=0 sends no traffic (useful for draining)
- Latency routing uses AWS's internal latency data — not real-time
- TTL matters: low TTL = faster failover but more DNS queries (cost)

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform implementation + failover test + screenshots checklist |
| `verify.md` | Console verification table, CLI checks, failover timing test, Terraform state, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Terraform — health checks, weighted, failover, latency records |
| `code/dns_checker.py` | Python script — inspects Route53 routing policies and health check status |
| `docs/architecture.md` | Architecture diagrams and notes |

## Code

### `code/dns_checker.py` — Inspect Route53 routing policies and health checks

```bash
pip install boto3

# List all hosted zones in your account
python code/dns_checker.py --list-zones

# Check a specific hosted zone
python code/dns_checker.py --hosted-zone-id Z1234567890ABC

# Use a specific AWS profile
python code/dns_checker.py --hosted-zone-id Z1234567890ABC --profile my-profile
```

What it shows:
- All record sets with their routing policy (Simple, Weighted, Failover, Latency, Geolocation, MultiValue)
- SetIdentifier and HealthCheckId for each record
- Health check status (healthy/unhealthy checker count)
- Routing policy summary table
- DNS report with total record count
