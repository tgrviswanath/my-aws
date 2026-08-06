# Project 1.1 — Static Website on S3 + CloudFront

**Stage:** 01 | **Level:** Beginner | **Est. Time:** 1–2 hours | **Cost:** ~$0–$1/month

Host a static HTML/CSS/JS website on S3 with HTTPS delivered globally through CloudFront. S3 bucket blocks all public access — CloudFront reads objects using Origin Access Control (OAC), the modern replacement for legacy OAI. Cache invalidation flushes stale content after deployments.

---

## Services Used

| Tool | Purpose | Cost |
|------|---------|------|
| S3 | Store and serve HTML/CSS/JS source files | $0.023/GB/month; first 5 GB free |
| CloudFront | CDN with HTTPS, 400+ edge locations | $0.0085–$0.012 per 10K HTTPS requests; 1 TB/month free |
| ACM (optional) | TLS certificate for custom domain | Free for CloudFront-attached certs |
| OAC | Restricts S3 bucket access to CloudFront only | Free |

---

## Input / Output

### Input
| Type | Description |
|------|-------------|
| `code/index.html` | Home page HTML |
| `code/style.css` | Stylesheet |
| `code/app.js` | Optional JavaScript |
| S3 bucket name | Globally unique, e.g. `my-static-site-abc123` |
| CloudFront OAC | Created in CloudFront console, referenced in S3 bucket policy |

### Output
| Type | Description |
|------|-------------|
| S3 bucket | Private bucket containing website files — no public access |
| CloudFront distribution | HTTPS URL: `https://d1234abcd.cloudfront.net` |
| OAC policy | S3 bucket policy allows `GetObject` only from CloudFront service principal |
| Cached content | Files served from nearest edge location with TTL 86400s (1 day) |

---

## Architecture

```
User browser
  │ HTTPS GET https://d1234abcd.cloudfront.net/index.html
  ▼
CloudFront Edge (nearest of 400+ locations)
  ├── Cache HIT  → return file immediately (no origin call)
  └── Cache MISS → forward to origin
        │ HTTPS (SigV4 signed) → S3 bucket (OAC)
        ▼
S3 Bucket (us-east-1) — public access BLOCKED
  └── s3://my-static-site-abc123/index.html
        └── returns object to CloudFront edge
              └── CloudFront caches + returns to user
```

---

## Quick Start

```cmd
REM 1. Create S3 bucket (replace BUCKET and REGION)
aws s3api create-bucket --bucket my-static-site-abc123 --region us-east-1

REM 2. Block all public access
aws s3api put-public-access-block --bucket my-static-site-abc123 ^
    --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,^
BlockPublicPolicy=true,RestrictPublicBuckets=true

REM 3. Upload website files
aws s3 sync code\ s3://my-static-site-abc123/ --delete

REM 4. Create CloudFront distribution + OAC via console:
REM    CloudFront → Create distribution → Origin domain: my-static-site-abc123.s3.amazonaws.com
REM    Origin access: Origin access control (recommended) → Create OAC
REM    Copy the generated S3 bucket policy and apply it (step 5)

REM 5. Apply OAC bucket policy (copy from CloudFront console after distribution creation)
aws s3api put-bucket-policy --bucket my-static-site-abc123 ^
    --policy file://code/bucket_policy.json

REM 6. Wait for distribution to deploy (~5-10 min), then test
curl -I https://d1234abcd.cloudfront.net/index.html

REM 7. After updating files, invalidate the cache
aws cloudfront create-invalidation ^
    --distribution-id E1234ABCD ^
    --paths "/*"
```

---

## Data Flow

```
1. aws s3 sync uploads HTML/CSS/JS files to the private S3 bucket
2. CloudFront distribution is configured with the S3 bucket as origin and OAC attached
3. OAC bucket policy is applied to S3 — only CloudFront service principal can call GetObject
4. User requests https://d1234abcd.cloudfront.net → DNS resolves to nearest CloudFront PoP
5. CloudFront checks its edge cache for the requested path
6. Cache MISS: CloudFront sends a SigV4-signed request to S3 on behalf of the OAC
7. S3 validates the signature, returns the object to CloudFront
8. CloudFront stores the object in edge cache (TTL = Cache-Control header or default 86400s)
9. CloudFront returns the object to the user over HTTPS (TLS terminated at edge)
10. Cache invalidation (/*) marks all cached objects stale — next request re-fetches from S3
```

---

## Project Files

| File | Purpose |
|------|---------|
| `README.md` | This file — project overview |
| `GUIDE.md` | Full walkthrough: S3 setup, CloudFront distribution, OAC config |
| `steps.md` | Windows CMD reference for S3 sync and invalidation commands |
| `steps_awsconsoleui.md` | Console walkthrough: create distribution, attach OAC, apply policy |
| `verify.md` | Checklist: HTTPS working, S3 not directly accessible, cache invalidation |
| `cost_estimate.md` | Cost breakdown (~$0 for low traffic) |
| `code/` | `index.html`, `style.css`, `app.js`, `bucket_policy.json` |
| `docs/` | OAC vs OAI comparison, CloudFront cache behaviour notes |
| `terraform/` | IaC reference for S3 + CloudFront + OAC |

---

## Lessons Learned

- S3 website endpoint (`http://bucket.s3-website-us-east-1.amazonaws.com`) is HTTP only — CloudFront adds the HTTPS termination; never expose the S3 website endpoint directly
- OAC (Origin Access Control) replaces legacy OAI — OAC supports all S3 API methods and works with server-side encryption (SSE-KMS), which OAI did not
- CloudFront has 400+ edge locations globally — a user in Tokyo gets the cached file from Tokyo, not from your us-east-1 S3 bucket
- Cache invalidation costs $0.005 per path after the first 1,000 paths/month — using `/*` counts as one path, making it cost-effective for small sites
- S3 bucket must have **Block Public Access** fully enabled when using OAC — if public access is on, anyone can bypass CloudFront and hit S3 directly, defeating HTTPS enforcement
- CloudFront distributions take 5–15 minutes to deploy globally — `aws cloudfront wait distribution-deployed` blocks until status is `Deployed`
- Setting the default root object to `index.html` in the CloudFront distribution handles requests to `/` — without it, `/` returns a 403 from S3
