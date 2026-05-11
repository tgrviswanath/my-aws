# Project 8.2 — WAF Application Protection

## What This Does
Deploys AWS WAF (Web Application Firewall) in front of the ALB to protect against SQL injection, XSS, bot traffic, and rate limiting.

## Rules Configured
| Rule | Protects Against |
|------|-----------------|
| AWS Managed — Core Rule Set | OWASP Top 10 |
| AWS Managed — SQL Database | SQL injection |
| AWS Managed — Known Bad Inputs | XSS, log4j, etc. |
| Rate limiting | DDoS, brute force (100 req/5min per IP) |
| Geo blocking | Block specific countries |
| IP allowlist | Allow only known IPs (admin paths) |

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
terraform output waf_arn
```

## Lessons Learned
- WAF rules are evaluated in priority order — lower number = higher priority
- Count mode: test rules without blocking — see what would be blocked first
- WAF logs: send to S3/CloudWatch/Firehose for analysis
- Managed rule groups: AWS maintains them — auto-updated for new threats
- Rate limiting: per IP, per session, or per custom key (e.g. user ID)
- False positives: use Count mode first, review logs, then switch to Block
