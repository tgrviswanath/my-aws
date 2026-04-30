# ElastiCache — Redis & Memcached Deep Dive

## What is ElastiCache?
ElastiCache is a managed in-memory caching service. Reduces database load, improves application response times from milliseconds to microseconds.

---

## Redis vs Memcached

| Feature | Redis | Memcached |
|---------|-------|-----------|
| Data structures | Strings, Lists, Sets, Hashes, Sorted Sets, Streams | Strings only |
| Persistence | ✅ RDB + AOF | ❌ |
| Replication | ✅ Primary + replicas | ❌ |
| Cluster mode | ✅ Sharding | ✅ Multi-node |
| Pub/Sub | ✅ | ❌ |
| Lua scripting | ✅ | ❌ |
| Transactions | ✅ | ❌ |
| Geospatial | ✅ | ❌ |
| Multi-threading | ❌ (single-threaded) | ✅ |
| Use case | Sessions, leaderboards, queues, pub/sub | Simple caching, multi-threaded |

**Choose Redis** for almost all use cases. Memcached only if you need pure multi-threaded caching with no persistence.

---

## Redis Architecture

### Cluster Mode Disabled (Replication Group)
```
Primary Node (read/write)
├── Replica 1 (read only, AZ-b)
└── Replica 2 (read only, AZ-c)
```

### Cluster Mode Enabled (Sharding)
```
Shard 1: Primary + 2 Replicas (slots 0-5460)
Shard 2: Primary + 2 Replicas (slots 5461-10922)
Shard 3: Primary + 2 Replicas (slots 10923-16383)
```
Up to 500 nodes, 500GB+ memory.

---

## Setup

```bash
# Create Redis replication group (cluster mode disabled)
aws elasticache create-replication-group \
  --replication-group-id prod-redis \
  --replication-group-description "Production Redis" \
  --engine redis \
  --engine-version 7.1 \
  --cache-node-type cache.r6g.large \
  --num-cache-clusters 3 \
  --automatic-failover-enabled \
  --multi-az-enabled \
  --cache-subnet-group-name prod-cache-subnet-group \
  --security-group-ids sg-cache-12345678 \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled \
  --auth-token "$(aws secretsmanager get-secret-value \
    --secret-id prod/redis/auth-token --query SecretString --output text)" \
  --snapshot-retention-limit 7 \
  --snapshot-window "03:00-04:00"

# Create Redis cluster mode enabled
aws elasticache create-replication-group \
  --replication-group-id prod-redis-cluster \
  --replication-group-description "Production Redis Cluster" \
  --engine redis \
  --cache-node-type cache.r6g.large \
  --num-node-groups 3 \
  --replicas-per-node-group 2 \
  --automatic-failover-enabled \
  --cluster-mode enabled
```

---

## Common Use Cases

### 1. Session Store

```python
import redis
import json
import uuid

r = redis.Redis(
    host='prod-redis.abc123.cache.amazonaws.com',
    port=6379,
    ssl=True,
    password='your-auth-token',
    decode_responses=True
)

def create_session(user_id: str, data: dict) -> str:
    session_id = str(uuid.uuid4())
    session_data = {'userId': user_id, **data}
    r.setex(
        f'session:{session_id}',
        3600,  # TTL: 1 hour
        json.dumps(session_data)
    )
    return session_id

def get_session(session_id: str) -> dict:
    data = r.get(f'session:{session_id}')
    if data:
        r.expire(f'session:{session_id}', 3600)  # Refresh TTL
        return json.loads(data)
    return None

def delete_session(session_id: str):
    r.delete(f'session:{session_id}')
```

### 2. Database Query Cache

```python
import hashlib
import json

def get_user(user_id: str) -> dict:
    cache_key = f'user:{user_id}'
    
    # Try cache first
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Cache miss — query database
    user = db.query("SELECT * FROM users WHERE id = %s", user_id)
    
    # Store in cache with TTL
    r.setex(cache_key, 300, json.dumps(user))  # 5 min TTL
    return user

def invalidate_user_cache(user_id: str):
    r.delete(f'user:{user_id}')
```

### 3. Rate Limiting

```python
def is_rate_limited(user_id: str, limit: int = 100, window: int = 60) -> bool:
    key = f'rate_limit:{user_id}'
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    results = pipe.execute()
    count = results[0]
    return count > limit
```

### 4. Leaderboard (Sorted Sets)

```python
def update_score(user_id: str, score: float):
    r.zadd('leaderboard', {user_id: score})

def get_top_players(n: int = 10) -> list:
    return r.zrevrange('leaderboard', 0, n-1, withscores=True)

def get_player_rank(user_id: str) -> int:
    rank = r.zrevrank('leaderboard', user_id)
    return rank + 1 if rank is not None else None
```

### 5. Pub/Sub (Real-time notifications)

```python
# Publisher
def publish_event(channel: str, event: dict):
    r.publish(channel, json.dumps(event))

# Subscriber
def subscribe_to_events(channel: str):
    pubsub = r.pubsub()
    pubsub.subscribe(channel)
    for message in pubsub.listen():
        if message['type'] == 'message':
            event = json.loads(message['data'])
            process_event(event)
```

### 6. Distributed Lock

```python
import time

def acquire_lock(resource: str, ttl: int = 30) -> str | None:
    lock_id = str(uuid.uuid4())
    acquired = r.set(
        f'lock:{resource}',
        lock_id,
        nx=True,   # Only set if not exists
        ex=ttl     # Expire after ttl seconds
    )
    return lock_id if acquired else None

def release_lock(resource: str, lock_id: str) -> bool:
    # Lua script for atomic check-and-delete
    script = """
    if redis.call('get', KEYS[1]) == ARGV[1] then
        return redis.call('del', KEYS[1])
    else
        return 0
    end
    """
    result = r.eval(script, 1, f'lock:{resource}', lock_id)
    return bool(result)
```

---

## Caching Strategies

### Cache-Aside (Lazy Loading)
```
App → Cache hit? → Return data
              ↓ miss
         → Database → Store in cache → Return data
```
Pros: Only caches requested data. Cons: Cache miss penalty, stale data possible.

### Write-Through
```
App → Write to cache AND database simultaneously
```
Pros: Cache always fresh. Cons: Write penalty, unused data cached.

### Write-Behind (Write-Back)
```
App → Write to cache → Async write to database
```
Pros: Fast writes. Cons: Data loss risk if cache fails before DB write.

### Read-Through
```
App → Cache → (on miss) Cache fetches from DB → Returns to App
```
Cache manages DB reads. App only talks to cache.

---

## Eviction Policies

| Policy | Behavior | Use Case |
|--------|---------|---------|
| noeviction | Return error when full | Critical data, never evict |
| allkeys-lru | Evict least recently used | General caching |
| volatile-lru | Evict LRU with TTL set | Mixed TTL/no-TTL data |
| allkeys-lfu | Evict least frequently used | Frequency-based caching |
| allkeys-random | Evict random key | Random access patterns |
| volatile-ttl | Evict soonest-to-expire | TTL-based eviction |

---

## Monitoring

```bash
# Key CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ElastiCache \
  --metric-name CacheHits \
  --dimensions Name=CacheClusterId,Value=prod-redis-001 \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum

# Important metrics:
# CacheHits / CacheMisses → Hit ratio (target > 90%)
# Evictions → Memory pressure (should be 0)
# CurrConnections → Connection count
# EngineCPUUtilization → CPU usage
# DatabaseMemoryUsagePercentage → Memory usage (alert at 80%)
# ReplicationLag → Replica lag (should be < 1s)
```

---

## Interview Q&A

### Q1: What is the difference between Redis and Memcached?
Redis supports rich data structures (lists, sets, sorted sets, hashes), persistence, replication, pub/sub, and Lua scripting. Memcached is simpler — strings only, multi-threaded, no persistence. Choose Redis for almost everything. Memcached only if you need pure multi-threaded caching with no other features.

### Q2: What caching strategy would you use for a product catalog?
Cache-aside (lazy loading) with write-through on updates. On read: check cache, miss → query DB, store in cache with TTL (e.g., 1 hour). On product update: update DB, then invalidate or update cache. Use longer TTLs for stable data (categories), shorter for frequently changing data (prices, inventory).

### Q3: How do you handle cache invalidation?
1. TTL-based: Set appropriate expiry, accept eventual consistency
2. Event-driven: On DB write, publish event → Lambda invalidates cache keys
3. Write-through: Update cache on every DB write
4. Versioned keys: `user:v2:123` — change version to invalidate all
5. Tag-based: Group related keys, invalidate by tag
Cache invalidation is one of the hardest problems in CS — design for eventual consistency where possible.

### Q4: What is a cache stampede and how do you prevent it?
Cache stampede (thundering herd): Many requests hit a cache miss simultaneously, all query the database at once. Prevention: (1) Mutex/lock — only one request fetches from DB, others wait, (2) Probabilistic early expiration — refresh cache slightly before TTL expires, (3) Background refresh — async refresh before expiry, (4) Stale-while-revalidate — serve stale data while refreshing.

### Q5: How does ElastiCache Redis handle failover?
In a replication group, if the primary fails, ElastiCache promotes a replica to primary (Multi-AZ automatic failover). DNS endpoint updates to point to new primary. Failover takes ~1-2 minutes. Applications should implement retry logic with exponential backoff. Use the cluster endpoint (not individual node endpoints) so failover is transparent.
