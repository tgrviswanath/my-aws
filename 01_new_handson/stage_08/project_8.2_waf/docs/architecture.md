# Architecture — Project 8.2 WAF Application Protection

## Traffic Flow with WAF

```
Internet
    │
    │ HTTP/HTTPS request
    ▼
AWS WAF Web ACL (evaluated before ALB)
    │
    │ Rules evaluated in priority order:
    │
    ├── Priority 1: Rate limit (100 req/5min/IP)
    │     └── BLOCK if exceeded
    │
    ├── Priority 5: Blocked IP set
    │     └── BLOCK if IP in list
    │
    ├── Priority 10: Core Rule Set (OWASP Top 10)
    │     └── BLOCK on match
    │
    ├── Priority 20: SQL injection rules
    │     └── BLOCK on match
    │
    ├── Priority 30: Known bad inputs (XSS, log4j)
    │     └── BLOCK on match
    │
    └── Default action: ALLOW
          │
          ▼
         ALB → ECS Tasks
```

## WAF Rule Actions

| Action | Effect |
|--------|--------|
| Block | Return 403 Forbidden |
| Allow | Pass request through |
| Count | Log but don't block (testing mode) |
| CAPTCHA | Challenge with CAPTCHA |

## Testing Strategy

```
Phase 1: Deploy all rules in COUNT mode
  → Monitor logs for false positives
  → Tune rules if legitimate traffic is flagged

Phase 2: Switch critical rules to BLOCK
  → SQL injection, XSS, known bad inputs

Phase 3: Enable rate limiting
  → Start with high threshold, lower gradually
```
