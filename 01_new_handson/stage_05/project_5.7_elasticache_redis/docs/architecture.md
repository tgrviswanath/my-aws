# Architecture — Project 5.7 Redis Caching with ElastiCache

## Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                    AWS VPC                                        │
│                                                                    │
│  PRIVATE SUBNETS                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              ECS Fargate Tasks                            │    │
│  │  app-sg: allows outbound to redis-sg:6379                 │    │
│  │                                                            │    │
│  │  Request flow:                                             │    │
│  │  1. Check Redis (cache-aside)                             │    │
│  │  2. HIT  → return cached data (~1ms)                      │    │
│  │  3. MISS → query RDS (~50ms)                              │    │
│  │         → store in Redis (TTL: 60s)                       │    │
│  │         → return data                                     │    │
│  └──────────────────────────┬─────────────────────────────── ┘   │
│                             │ :6379 (from app-sg only)            │
│  ┌──────────────────────────▼─────────────────────────────── ┐   │
│  │         ElastiCache Redis: handson-redis-cluster           │   │
│  │  cache.t3.micro | Redis 7.1                                │   │
│  │  Encryption: in-transit + at-rest                          │   │
│  │  Eviction: allkeys-lru                                     │   │
│  │  redis-sg: inbound 6379 from app-sg only                   │   │
│  └────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
```

## Cache Key Strategy

```
items:all                    → list of all items (TTL: 60s)
items:{id}                   → single item (TTL: 300s)
session:{session_id}         → user session (TTL: 3600s)
rate_limit:{user}:{window}   → request count (TTL: window_seconds)
lock:{job_name}              → distributed lock (TTL: 30s)
```

## Performance Impact

```
Without cache:
  GET /items → MySQL query → ~50ms

With cache:
  GET /items (miss) → MySQL → Redis store → ~55ms (first time)
  GET /items (hit)  → Redis → ~1ms (subsequent requests)

Cache hit rate of 90% reduces DB load by 90%.
```
