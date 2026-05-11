# Steps — Project 5.7 Redis Caching with ElastiCache

## Phase 1 — Deploy

```bash
cd terraform
terraform init
terraform apply -var-file="terraform.tfvars"

REDIS_ENDPOINT=$(terraform output -raw redis_endpoint)
echo "Redis: $REDIS_ENDPOINT:6379"
```

---

## Phase 2 — Test from ECS Task (via SSM)

```bash
# Connect to a running ECS task
TASK_ARN=$(aws ecs list-tasks \
  --cluster handson-cluster \
  --service-name handson-flask-api-service \
  --query "taskArns[0]" --output text)

aws ecs execute-command \
  --cluster handson-cluster \
  --task $TASK_ARN \
  --container flask-api \
  --interactive \
  --command "/bin/sh"

# Inside the container:
# Install redis-cli
apk add redis

# Connect to ElastiCache
redis-cli -h $REDIS_ENDPOINT -p 6379

# Test commands:
PING                          # PONG
SET test "hello"              # OK
GET test                      # "hello"
SETEX session:abc 3600 '{"user":"alice"}'  # OK
TTL session:abc               # 3600
INCR rate_limit:user1:1234    # 1
INCR rate_limit:user1:1234    # 2
```

---

## Phase 3 — Test Cache-Aside Pattern

```bash
# Run the cache patterns demo
python3 << 'EOF'
import os, time
os.environ["REDIS_HOST"] = "YOUR_REDIS_ENDPOINT"

from cache_patterns import get_redis, get_or_set

r = get_redis()

# Simulate DB fetch
def fetch_from_db():
    time.sleep(0.1)  # simulate DB latency
    return [{"id": "1", "name": "Widget A"}, {"id": "2", "name": "Widget B"}]

# First call — cache miss
start = time.time()
data, source = get_or_set(r, "items:all", fetch_from_db, ttl=60)
print(f"Source: {source}, Time: {(time.time()-start)*1000:.1f}ms")

# Second call — cache hit
start = time.time()
data, source = get_or_set(r, "items:all", fetch_from_db, ttl=60)
print(f"Source: {source}, Time: {(time.time()-start)*1000:.1f}ms")
EOF
```

---

## Phase 4 — Test Rate Limiting

```bash
python3 << 'EOF'
import os
os.environ["REDIS_HOST"] = "YOUR_REDIS_ENDPOINT"

from cache_patterns import RateLimiter

limiter = RateLimiter(limit=5, window_seconds=60)

for i in range(7):
    allowed, info = limiter.is_allowed("user:alice")
    status = "✅ ALLOWED" if allowed else "❌ BLOCKED"
    print(f"Request {i+1}: {status} | remaining: {info['remaining']}")
EOF
```

---

## Screenshots to Take
- [ ] ElastiCache cluster in Available state
- [ ] Redis endpoint in private subnet (not publicly accessible)
- [ ] Cache miss vs cache hit latency comparison
- [ ] Redis CLI showing keys and TTLs
- [ ] Rate limiter blocking after limit exceeded
- [ ] `terraform apply` success output
