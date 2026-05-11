# Architecture — Project 1.1 Static Website Hosting

## Diagram

```
                        ┌─────────────────────────────────────────┐
                        │              AWS Cloud                   │
                        │                                          │
  User's Browser        │  ┌──────────┐    ┌───────────────────┐  │
       │                │  │ Route53  │    │      ACM          │  │
       │ DNS lookup      │  │          │    │  SSL Certificate  │  │
       └───────────────►│  │ A Record │    │  (us-east-1)      │  │
                        │  │ (Alias)  │    └───────────────────┘  │
                        │  └────┬─────┘             │             │
                        │       │                   │ cert        │
                        │       ▼                   ▼             │
                        │  ┌──────────────────────────────────┐   │
                        │  │         CloudFront CDN           │   │
                        │  │  - HTTPS termination             │   │
                        │  │  - Edge caching (global)         │   │
                        │  │  - HTTP → HTTPS redirect         │   │
                        │  │  - Price Class 100               │   │
                        │  └──────────────┬───────────────────┘   │
                        │                 │ OAC (signed requests)  │
                        │                 ▼                        │
                        │  ┌──────────────────────────────────┐   │
                        │  │           S3 Bucket              │   │
                        │  │  - Static files (HTML/CSS/JS)    │   │
                        │  │  - Versioning enabled            │   │
                        │  │  - Private (no public access)    │   │
                        │  │  - Lifecycle → Glacier 30d       │   │
                        │  └──────────────────────────────────┘   │
                        └─────────────────────────────────────────┘
```

## Request Flow

```
1. User visits https://yourdomain.com
2. Route53 resolves DNS → CloudFront IP
3. CloudFront checks edge cache
   ├── Cache HIT  → return cached file immediately
   └── Cache MISS → fetch from S3 origin via OAC
4. CloudFront returns file with HTTPS
5. Browser renders page
```

## Key Design Decisions

| Decision | Reason |
|----------|--------|
| OAC instead of OAI | OAI is legacy; OAC is the current AWS recommendation |
| S3 bucket private | Security — only CloudFront can read files |
| ACM in us-east-1 | CloudFront only accepts certs from us-east-1 |
| PriceClass_100 | Cheapest option — US/Canada/Europe edge locations only |
| Versioning enabled | Allows rollback if you accidentally overwrite files |
| Lifecycle to Glacier | Cost optimization — old versions stored cheaply |
