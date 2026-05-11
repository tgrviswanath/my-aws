# Project 4.3 — URL Shortener

## What This Does
Builds a serverless URL shortener: POST a long URL, get back a short code. Visiting the short URL redirects to the original. Classic event-driven app demonstrating DynamoDB design patterns.

## Architecture
```
POST /shorten → Lambda → DynamoDB (store mapping)
GET  /{code}  → Lambda → DynamoDB (lookup) → 301 Redirect
```

## API
| Method | Path | Description |
|--------|------|-------------|
| POST | /shorten | Submit long URL, get short code |
| GET | /{code} | Redirect to original URL |
| GET | /stats/{code} | View click stats for a short URL |

## DynamoDB Design
```
Table: url-shortener
PK: code (String)  ← short code e.g. "abc123"
Attributes:
  - original_url: "https://very-long-url.com/..."
  - created_at: ISO timestamp
  - clicks: Number (atomic counter)
  - ttl: Unix timestamp (auto-expire after 30 days)
```

## How to Deploy
```bash
cd terraform
terraform init && terraform apply
terraform output api_url
```

## Lessons Learned
- DynamoDB TTL: set a Unix timestamp attribute and DynamoDB auto-deletes expired items
- Atomic counters: use `ADD clicks 1` in UpdateExpression — safe for concurrent increments
- 301 vs 302 redirect: 301 is permanent (browser caches it), 302 is temporary — use 302 for URL shorteners so stats are always tracked
- Short code collision: use random 6-char alphanumeric + check-before-insert pattern
- API Gateway can return 3xx redirects directly from Lambda response
