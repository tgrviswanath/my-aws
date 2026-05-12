# Project 5.7 — Redis Caching with ElastiCache

## What This Does
Deploys Amazon ElastiCache for Redis and integrates it with the ECS application from Project 5.4. Demonstrates caching patterns: cache-aside, TTL management, session storage, and rate limiting.

## Caching Patterns Covered

| Pattern | Description | Use Case |
|---------|-------------|---------|
| Cache-aside | App checks cache first, falls back to DB | Read-heavy data |
| Write-through | Write to cache and DB simultaneously | Consistency critical |
| TTL expiry | Auto-expire stale data | Frequently changing data |
| Session store | Store user sessions in Redis | Stateless app servers |
| Rate limiting | Count requests per user per window | API protection |
| Distributed lock | Prevent concurrent operations | Job scheduling |

## Architecture
```
ECS Tasks → ElastiCache Redis (private subnet)
              └── Cache-aside for DB queries
              └── Session storage
              └── Rate limiting counters
```

## Services Used
- ElastiCache (Redis 7.x)
- ECS Fargate (from Project 5.4)
- VPC (private subnet for Redis)
- Security Groups (Redis only accessible from ECS tasks)

## How to Deploy
```bash
cd terraform
terraform init && terraform apply -var-file="terraform.tfvars"
terraform output redis_endpoint
```

## Lessons Learned
- ElastiCache Redis must be in a private subnet — never expose port 6379 to the internet
- Redis cluster mode vs single node: cluster mode for high availability, single node for dev
- TTL strategy: too short = cache misses; too long = stale data
- Redis eviction policy: `allkeys-lru` evicts least recently used keys when memory is full
- Use Redis Cluster for production — single node is a single point of failure
- Connection pooling: reuse Redis connections across Lambda/ECS invocations

## Code

### `src/cache_patterns.py` — Redis caching patterns

```bash
pip install redis boto3

# Set Redis connection
export REDIS_HOST=my-cluster.abc123.cache.amazonaws.com
export REDIS_PORT=6379

python src/cache_patterns.py
```

Patterns demonstrated:
| Pattern | Use case |
|---------|---------|
| Cache-aside | Read from cache, fallback to DB on miss |
| Write-through | Write to cache and DB simultaneously |
| TTL expiry | Auto-expire stale data |
| Cache invalidation | Delete cache on data update |
