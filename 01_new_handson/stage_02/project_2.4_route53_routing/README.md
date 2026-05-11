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
