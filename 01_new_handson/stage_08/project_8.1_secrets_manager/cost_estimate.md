# Cost Estimate — Project 8.1: AWS Secrets Manager

## Pricing Model (us-east-1, as of 2024)

| Resource | Unit Price | Notes |
|----------|-----------|-------|
| Secret storage | $0.40 / secret / month | Per unique secret |
| API calls | $0.05 / 10,000 calls | GetSecretValue, DescribeSecret, etc. |
| KMS requests | $0.03 / 10,000 requests | If using CMK |
| Rotation Lambda | ~$0.00 | Usually within Lambda free tier |

---

## Free Tier

- **30-day free trial** per secret when first created
- AWS Lambda: 1M free requests/month (rotation Lambda)
- AWS KMS: 20,000 free requests/month (then $0.03/10K)

After the 30-day trial: $0.40/secret/month applies.

---

## Scenario Estimates

### Minimal Setup (1 secret, low traffic app)
| Item | Quantity | Monthly Cost |
|------|----------|-------------|
| 1 RDS credentials secret | 1 | $0.40 |
| API calls (1 call/min, cached 5 min) | ~8,640/month | $0.04 |
| KMS decrypt calls | ~8,640/month | $0.00 (free tier) |
| Rotation Lambda invocations | 1/month | $0.00 |
| **Total** | | **~$0.44/month** |

### Medium Setup (5 secrets, multiple services)
| Item | Quantity | Monthly Cost |
|------|----------|-------------|
| 5 secrets (DB, API keys, OAuth tokens) | 5 | $2.00 |
| API calls (multiple services, cached) | ~50,000/month | $0.25 |
| KMS requests | ~50,000/month | $0.15 |
| **Total** | | **~$2.40/month** |

### Production Setup (20 secrets, high traffic)
| Item | Quantity | Monthly Cost |
|------|----------|-------------|
| 20 secrets | 20 | $8.00 |
| API calls (microservices, 100K calls) | 100K | $0.50 |
| KMS requests | 100K | $0.30 |
| **Total** | | **~$8.80/month** |

---

## Cost Optimization Tips

1. **Cache credentials in memory** (TTL: 5 minutes) — reduces API call cost significantly
2. **Reuse secrets across environments** with versioning tags rather than duplicate secrets
3. **Use SSM Parameter Store** for non-sensitive config (free for standard parameters)
4. **AWS-managed KMS key** (`aws/secretsmanager`) is free — only pay for CMK if compliance requires

```python
# Cost optimization: cache with TTL
import time
_secret_cache = {}

def get_secret_cached(name, ttl=300):
    now = time.time()
    if name in _secret_cache and now - _secret_cache[name]['ts'] < ttl:
        return _secret_cache[name]['value']
    value = get_secret(name)  # API call
    _secret_cache[name] = {'value': value, 'ts': now}
    return value
```

---

## Total

| Time Period | Estimated Cost |
|-------------|----------------|
| First 30 days (free trial) | $0.00 – $0.10 (KMS only) |
| Month 2+ (1 secret) | ~$0.44/month |
| Month 2+ (5 secrets) | ~$2.40/month |
| Month 2+ (20 secrets) | ~$8.80/month |

**Projected annual cost (1 secret, production use):** ~$5.00/year

---

## Cleanup

To stop all charges immediately:

```bash
# Force delete (no recovery window — immediate, use with caution)
aws secretsmanager delete-secret \
  --secret-id "prod/myapp/rds-credentials" \
  --force-delete-without-recovery

# Standard delete with 7-day recovery window (safer)
aws secretsmanager delete-secret \
  --secret-id "prod/myapp/rds-credentials" \
  --recovery-window-in-days 7

# Delete CMK (schedule, minimum 7 days)
aws kms schedule-key-deletion \
  --key-id alias/secrets-manager-rds \
  --pending-window-in-days 7

# Remove rotation Lambda
aws lambda delete-function \
  --function-name SecretsManagerRDSPostgreSQLRotation

# Verify deletion
aws secretsmanager list-secrets \
  --query 'SecretList[?Name==`prod/myapp/rds-credentials`]'
```

**Charges stop** as soon as secret is deleted (or enters pending deletion window).
