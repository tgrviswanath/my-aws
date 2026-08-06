# Project 5.7 — ElastiCache Redis Caching Layer

**Stage:** 05 | **Level:** Intermediate | **Est. Time:** 45–60 min | **Cost:** ~$26/month (cache.t3.micro)

Add a single-node ElastiCache Redis 7 cluster (`cache.t3.micro`) to the ECS Fargate application from Project 5.4 using the cache-aside pattern. The ECS app checks Redis first on every read request; on a cache miss it queries RDS, writes the result to Redis with a TTL, and returns the response. Redis runs in the same VPC private subnet as the ECS tasks, and a dedicated security group restricts port 6379 access to the ECS task security group only — Redis is never reachable from the public internet or from any other resource in the VPC. Under steady load the cache hit rate exceeds 80%, dropping read latency from ~50 ms (RDS round-trip) to ~1 ms (Redis in-memory lookup).

## Services Used

| Tool | Purpose | Cost |
|---|---|---|
| Amazon ElastiCache for Redis 7 | Single-node in-memory cache (`cache.t3.micro`) — handles read-heavy query results | ~$26/month |
| Amazon ECS (Fargate) | Application tasks that implement cache-aside logic against Redis and RDS | Pay-per-vCPU/memory-second (from Project 5.4) |
| Amazon VPC + Private Subnets | Network isolation — Redis and ECS tasks share the same private subnet tier | Free |
| Security Groups | `redis-sg` allows port 6379 inbound from `ecs-task-sg` only | Free |

## Input / Output

### Input

| Parameter | Value | Source |
|---|---|---|
| ECS Service | `my-fargate-service` on cluster `my-cluster` | Project 5.4 output |
| VPC ID | `vpc-0abc12345def67890` with private subnets in `us-east-1a` and `us-east-1b` | Project 5.4 networking |
| ECS Task Security Group | `sg-0ecs1234` — already attached to Fargate tasks | Project 5.4 output |
| Redis Node Type | `cache.t3.micro` — 0.5 GB RAM, single AZ | Manual selection |
| Redis Version | `7.0` | ElastiCache parameter group family `redis7` |
| Subnet Group | `redis-subnet-group` using private subnets only | Created in this project |
| Redis Security Group | `sg-0redis5678` — inbound 6379 from `sg-0ecs1234` | Created in this project |

### Output

| Result | Detail |
|---|---|
| Redis Endpoint | `my-redis.abc123.ng.0001.use1.cache.amazonaws.com:6379` — accessible only from VPC |
| Read latency (cache hit) | ~1 ms — Redis in-memory lookup vs ~50 ms RDS round-trip |
| Read latency (cache miss) | ~50 ms — falls through to RDS, then writes result to Redis with TTL |
| Cache hit rate | >80% under steady load with repeated queries to the same keys |
| Memory eviction | `allkeys-lru` policy evicts least-recently-used keys when 0.5 GB RAM is full |

## Architecture

```
  Internet
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│                        VPC (10.0.0.0/16)                     │
│                                                              │
│  Public Subnet                                               │
│  ┌──────────────────────────────┐                           │
│  │   Application Load Balancer  │                           │
│  └──────────────┬───────────────┘                           │
│                 │                                            │
│  Private Subnet (10.0.1.0/24 / 10.0.2.0/24)                │
│  ┌──────────────▼──────────────────────────────────────┐    │
│  │  ECS Fargate Tasks  (sg-0ecs1234)                   │    │
│  │                                                     │    │
│  │  1. GET /users/42                                   │    │
│  │  2. Redis GET user:42 ──────────────────────────►  │    │
│  │                        ┌──────────────────────────┐ │    │
│  │  hit → return cached   │  ElastiCache Redis 7     │ │    │
│  │  miss → query RDS      │  cache.t3.micro          │ │    │
│  │       → SET user:42    │  sg-0redis5678           │ │    │
│  │         EX 300         │  port 6379               │ │    │
│  │                        └──────────────────────────┘ │    │
│  │  3. Query RDS (on miss) ──────────────────────────► │    │
│  │                        ┌──────────────────────────┐ │    │
│  │                        │  RDS PostgreSQL (5.4)    │ │    │
│  │                        └──────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

## Quick Start

```cmd
REM ── Step 1: Create subnet group for ElastiCache (private subnets only) ──
aws elasticache create-cache-subnet-group ^
  --cache-subnet-group-name redis-subnet-group ^
  --cache-subnet-group-description "Private subnets for Redis" ^
  --subnet-ids subnet-0private1a subnet-0private1b ^
  --region us-east-1

REM ── Step 2: Create security group for Redis ──
aws ec2 create-security-group ^
  --group-name redis-sg ^
  --description "Redis access from ECS tasks only" ^
  --vpc-id vpc-0abc12345def67890 ^
  --region us-east-1

REM ── Step 3: Allow inbound 6379 only from ECS task security group ──
aws ec2 authorize-security-group-ingress ^
  --group-id sg-0redis5678 ^
  --protocol tcp ^
  --port 6379 ^
  --source-group sg-0ecs1234 ^
  --region us-east-1

REM ── Step 4: Create the Redis cluster (single node, no cluster mode) ──
aws elasticache create-cache-cluster ^
  --cache-cluster-id my-redis ^
  --cache-node-type cache.t3.micro ^
  --engine redis ^
  --engine-version 7.0 ^
  --num-cache-nodes 1 ^
  --cache-subnet-group-name redis-subnet-group ^
  --security-group-ids sg-0redis5678 ^
  --region us-east-1

REM ── Step 5: Wait for cluster to become 'available' ──
aws elasticache describe-cache-clusters ^
  --cache-cluster-id my-redis ^
  --query "CacheClusters[0].CacheClusterStatus" ^
  --region us-east-1

REM ── Step 6: Get Redis endpoint ──
aws elasticache describe-cache-clusters ^
  --cache-cluster-id my-redis ^
  --show-cache-node-info ^
  --query "CacheClusters[0].CacheNodes[0].Endpoint" ^
  --region us-east-1

REM ── Step 7: Update ECS task definition with REDIS_HOST environment variable ──
REM   Add to container environment:
REM   {"name": "REDIS_HOST", "value": "my-redis.abc123.ng.0001.use1.cache.amazonaws.com"}
REM   {"name": "REDIS_PORT", "value": "6379"}

REM ── Step 8: Delete cluster when done to stop $26/month billing ──
aws elasticache delete-cache-cluster ^
  --cache-cluster-id my-redis ^
  --region us-east-1
```

## Data Flow

1. HTTP request arrives at the ALB and is routed to an ECS Fargate task in the private subnet.
2. The application code extracts the resource key (e.g., `user:42`) and issues a Redis `GET user:42`.
3. **Cache hit path:** Redis returns the cached JSON value in ~1 ms; the app returns the response immediately — RDS is never queried.
4. **Cache miss path:** Redis returns `nil`; the app queries RDS PostgreSQL for the record (~50 ms).
5. The app serializes the RDS result and writes it to Redis: `SET user:42 <json> EX 300` (5-minute TTL for user records).
6. The app returns the response to the client; subsequent requests for `user:42` within 300 seconds are served from Redis.
7. When Redis RAM reaches 0.5 GB, the `allkeys-lru` eviction policy automatically removes least-recently-used keys to make room for new writes.
8. When a user record is updated in RDS, the app issues `DEL user:42` to Redis to invalidate the stale cache entry.

## Project Files

| File | Description |
|---|---|
| `create-cluster.sh` | AWS CLI commands to create subnet group, security group rules, and Redis cluster |
| `redis-sg-rules.json` | Security group inbound rule: TCP 6379 from ECS task SG only |
| `task-def-with-redis.json` | Updated ECS task definition adding `REDIS_HOST` and `REDIS_PORT` environment variables |
| `cache_aside.py` | Python snippet showing cache-aside pattern: GET → miss → RDS → SET with TTL |
| `README.md` | This file |

## Lessons Learned

- **ElastiCache cannot live in a public subnet** — the service requires subnets with no internet gateway route; attempting to place a Redis cluster in a public subnet fails at creation time with a subnet validation error.
- **Cluster mode disabled vs enabled** — single primary node (cluster mode disabled) is sufficient until your dataset exceeds the node's RAM (0.5 GB for t3.micro); cluster mode enabled shards keys across multiple nodes but requires the application to use a cluster-aware Redis client.
- **Connection pooling is critical** — creating a new TCP connection to Redis per request adds ~5–10 ms overhead and can exhaust the connection limit (~65,000 per node) under load; use a singleton connection pool (e.g., `redis-py`'s `ConnectionPool`) initialized once at app startup.
- **`maxmemory-policy allkeys-lru` is the safest default** — without an eviction policy, Redis returns `OOM` errors when RAM is full and refuses new writes; `allkeys-lru` silently evicts cold keys, keeping the cache functional without application changes.
- **TTL strategy is workload-dependent** — use short TTLs (60 seconds) for high-write data like session counters or inventory levels, and longer TTLs (1 hour or more) for reference data like product catalogues that change infrequently.
- **ElastiCache Redis 7 supports TLS in-transit and AUTH tokens** — enable `TransitEncryptionEnabled=true` and set an auth token to prevent any process that accidentally reaches port 6379 (misconfigured SG) from reading cache data.
- **Invalidate on write, rely on TTL as a safety net** — issuing `DEL user:42` in the same RDS transaction that updates the record keeps the cache consistent immediately; the TTL catches any invalidation that a code path missed.
