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

## Files
| File | Purpose |
|------|---------|
| `steps.md` | Console, CLI, Terraform implementation + screenshots checklist |
| `verify.md` | Console verification table, CLI checks, Terraform state, OAC test, expected outputs |
| `cost_estimate.md` | Per-resource cost breakdown |
| `terraform/main.tf` | Terraform — S3, CloudFront, ACM, Route53 |
| `code/deploy_website.sh` | Shell script — sync to S3 + CloudFront cache invalidation |
| `code/index.html` | Sample static site HTML |
| `docs/architecture.md` | Architecture diagrams and notes |

## Code

### `code/deploy_website.sh` — Deploy static site to S3 + CloudFront

```bash
# Make executable
chmod +x code/deploy_website.sh

# Deploy (syncs ./site folder to S3 and invalidates CloudFront cache)
./code/deploy_website.sh my-bucket-name E1ABCDEF123456

# Deploy from a custom source directory
./code/deploy_website.sh my-bucket-name E1ABCDEF123456 ./dist
```

What it does:
- Syncs HTML files with `no-cache` headers
- Syncs CSS/JS with 1-hour cache
- Syncs images/fonts with 1-year immutable cache
- Creates a CloudFront invalidation for `/*`
- Waits for the invalidation to complete
- Prints the CloudFront URL

### `code/index.html` — Sample static site
Open in browser or deploy to S3 to see the AWS-themed landing page.
