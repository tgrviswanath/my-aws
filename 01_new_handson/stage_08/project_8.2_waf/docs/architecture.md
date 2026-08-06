# Architecture — Project 8.2 WAF Application Protection

## Traffic Flow with WAF

```
Internet
    │ HTTP/HTTPS request
    ▼
AWS WAF Web ACL (evaluated BEFORE ALB receives request)
    │
    │ Rules evaluated in priority order (lower = higher priority):
    │
    ├── Priority 1: Rate limit (100 req/5min/IP)
    │     └── BLOCK if exceeded → 429 Too Many Requests
    │
    ├── Priority 5: Blocked IP set
    │     └── BLOCK if IP in list → 403 Forbidden
    │
    ├── Priority 10: AWS Core Rule Set (OWASP Top 10)
    │     └── BLOCK on SQL injection, XSS, etc.
    │
    ├── Priority 20: SQL injection rules
    │     └── BLOCK on SQL patterns in query/body
    │
    ├── Priority 30: Known bad inputs (XSS, log4j)
    │     └── BLOCK on known attack patterns
    │
    └── Default action: ALLOW
          │
          ▼
         ALB → ECS Tasks
```

## WAF Logging

```
WAF blocks request
    │
    │ Log entry written to CloudWatch: aws-waf-logs-handson
    ▼
Log entry contains:
  {
    "action": "BLOCK",
    "terminatingRuleId": "AWSManagedRulesSQLiRuleSet",
    "httpRequest": {
      "clientIp": "1.2.3.4",
      "uri": "/items?id=1' OR '1'='1",
      "method": "GET"
    }
  }
```

## Testing Strategy

```
Phase 1: Deploy all rules in COUNT mode
  → Monitor logs for false positives
  → Tune rules if legitimate traffic is flagged

Phase 2: Switch to BLOCK mode
  → SQL injection, XSS, known bad inputs

Phase 3: Enable rate limiting
  → Start high (1000/5min), lower gradually
```

## Input / Output

### Input
| Type | Description | Example |
|------|-------------|---------|
| AWS Account | Active subscription | IAM user with required permissions |
| Configuration | Service settings | CIDR blocks, instance types, regions |
| Source Data | Application or data files | Docker images, SQL scripts, CSV files |

### Output
| Type | Description | Access |
|------|-------------|--------|
| AWS Resources | Deployed infrastructure | AWS Console or CLI |
| Service Endpoints | HTTP/HTTPS URLs, connection strings | Resource overview |
| CloudWatch Logs | Execution and audit trail | CloudWatch Log groups |
| Metrics | Performance data | CloudWatch Metrics |

## Key Concepts
| Concept | Explanation |
|---------|-------------|
| IAM Role | AWS identity for services â€” no static credentials |
| Security Group | Virtual firewall for EC2/RDS â€” stateful |
| VPC | Isolated network â€” your private AWS cloud |
| Region | Geographic AWS datacenter location |
| Availability Zone | Isolated datacenters within a region |
| CloudWatch | AWS monitoring and logging service |
| Free Tier | AWS free usage limits per service per month |
