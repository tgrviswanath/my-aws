# Project 1.1 — Static Website Hosting

## What This Does
Hosts a static website on S3, served globally via CloudFront CDN, with HTTPS via ACM and a custom domain via Route53.

## Architecture
```
User → Route53 (DNS) → CloudFront (CDN + HTTPS) → S3 (origin)
```

## Services Used
| Service | Role |
|---------|------|
| S3 | Store and serve static files |
| CloudFront | CDN — global edge caching + HTTPS |
| ACM | Free SSL/TLS certificate |
| Route53 | DNS — map domain to CloudFront |

## Add-ons Covered
- S3 Versioning (keep history of file changes)
- S3 Lifecycle policies (move old versions to Glacier)
- Glacier archival (long-term cheap storage)

## How to Deploy
```bash
cd terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

## Lessons Learned
- S3 static hosting does NOT support HTTPS — CloudFront is required for that
- ACM certificates for CloudFront must be created in `us-east-1` regardless of your region
- CloudFront distributions take 10–15 minutes to deploy globally
- S3 bucket names must be globally unique
- Use OAC (Origin Access Control) not OAI — OAI is legacy
