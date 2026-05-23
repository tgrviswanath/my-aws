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

## Phase 5 — Verification & Validation

### 5.1 AWS Console Verification
1. **ElastiCache** → **Redis clusters** → confirm cluster status = **Available**
2. **ElastiCache** → cluster → **Configuration** → confirm subnet group uses private subnets
3. **ElastiCache** → cluster → **Security** → confirm no public access
4. **VPC** → **Security Groups** → confirm Redis SG allows port 6379 only from ECS SG
5. **CloudWatch** → **Metrics** → ElastiCache → confirm `CacheHits` and `CacheMisses` metrics flowing

### 5.2 CLI Verification Commands
```bash
REDIS_ENDPOINT=$(cd terraform && terraform output -raw redis_endpoint)

# Confirm cluster is available
aws elasticache describe-cache-clusters \
  --query "CacheClusters[?Engine=='redis'].{ID:CacheClusterId,Status:CacheClusterStatus,Engine:Engine,Node:CacheNodeType}" \
  --output table
# Expected: Status=available

# Confirm cluster is in private subnet (no public endpoint)
aws elasticache describe-replication-groups \
  --query "ReplicationGroups[*].{ID:ReplicationGroupId,Status:Status,AtRestEncryption:AtRestEncryptionEnabled,TransitEncryption:TransitEncryptionEnabled}"
# Expected: Status=available

# Confirm subnet group uses private subnets
aws elasticache describe-cache-subnet-groups \
  --query "CacheSubnetGroups[*].{Name:CacheSubnetGroupName,Subnets:Subnets[*].SubnetIdentifier}"
# Expected: subnet IDs matching private subnets

# Confirm security group only allows port 6379 from ECS SG
aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=*redis*" \
  --query "SecurityGroups[*].IpPermissions[*].{Port:FromPort,Source:UserIdGroupPairs[0].GroupId}"
# Expected: port 6379 from ECS security group ID only
```

### 5.3 Functional Tests
```bash
# Test 1: Redis PING from ECS task
TASK_ARN=$(aws ecs list-tasks --cluster handson-cluster \
  --service-name handson-flask-api-service \
  --query "taskArns[0]" --output text)
aws ecs execute-command \
  --cluster handson-cluster --task $TASK_ARN \
  --container flask-api --interactive --command "/bin/sh" <<'CMDS'
redis-cli -h $REDIS_ENDPOINT -p 6379 PING
CMDS
# Expected: PONG

# Test 2: Cache miss vs cache hit latency
# Run from ECS task or local with REDIS_HOST set:
python3 - <<'EOF'
import os, time, json
os.environ["REDIS_HOST"] = "YOUR_REDIS_ENDPOINT"
from cache_patterns import get_redis, get_or_set

r = get_redis()
def slow_db():
    time.sleep(0.1)
    return [{"id": "1", "name": "Widget"}]

# Cache miss
t0 = time.time()
data, src = get_or_set(r, "test:items", slow_db, ttl=30)
miss_ms = (time.time() - t0) * 1000
print(f"Cache MISS: {src}, {miss_ms:.1f}ms")

# Cache hit
t0 = time.time()
data, src = get_or_set(r, "test:items", slow_db, ttl=30)
hit_ms = (time.time() - t0) * 1000
print(f"Cache HIT:  {src}, {hit_ms:.1f}ms")
print(f"Speedup: {miss_ms/hit_ms:.0f}x faster")
EOF
# Expected: HIT is ~100x faster than MISS

# Test 3: TTL expiry works
redis-cli -h $REDIS_ENDPOINT SETEX ttl_test 5 "expires_soon"
redis-cli -h $REDIS_ENDPOINT TTL ttl_test   # Expected: 5
sleep 6
redis-cli -h $REDIS_ENDPOINT EXISTS ttl_test  # Expected: 0 (expired)

# Test 4: Rate limiter blocks after limit
python3 - <<'EOF'
import os
os.environ["REDIS_HOST"] = "YOUR_REDIS_ENDPOINT"
from cache_patterns import RateLimiter

limiter = RateLimiter(limit=3, window_seconds=60)
for i in range(5):
    allowed, info = limiter.is_allowed("test:user")
    print(f"Request {i+1}: {'ALLOWED' if allowed else 'BLOCKED'} | remaining={info['remaining']}")
EOF
# Expected: requests 1-3 ALLOWED, 4-5 BLOCKED

# Test 5: Redis is NOT reachable from outside VPC
redis-cli -h $REDIS_ENDPOINT -p 6379 PING --timeout 3 2>&1 || echo "BLOCKED as expected"
# Expected: connection refused / timeout (private subnet, no public access)
```

### 5.4 Terraform State Verification
```bash
cd terraform
terraform state list | grep -E "elasticache|redis"
# Expected: aws_elasticache_cluster or aws_elasticache_replication_group resource

terraform output
# Expected: redis_endpoint, redis_port

# Confirm no drift
terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

### 5.5 Logs & Monitoring Checks
```bash
# Check CloudWatch ElastiCache metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ElastiCache \
  --metric-name CacheHits \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Sum \
  --query "Datapoints[*].{Time:Timestamp,Hits:Sum}"
# Expected: non-zero hits after running cache tests

aws cloudwatch get-metric-statistics \
  --namespace AWS/ElastiCache \
  --metric-name CurrConnections \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Average \
  --query "Datapoints[*].Sum"
# Expected: > 0 (active connections from ECS tasks)
```

### 5.6 Expected Successful Outputs
| Check | Expected Result |
|-------|----------------|
| Cluster status | `available` |
| `PING` from ECS task | `PONG` |
| Cache miss latency | ~100ms (simulated DB) |
| Cache hit latency | < 2ms |
| TTL expiry | Key gone after TTL seconds |
| Rate limiter | Blocks after limit exceeded |
| External access | Connection refused (private) |

### 5.7 Verification Checklist
- [ ] ElastiCache cluster status = available
- [ ] Cluster in private subnet (no public endpoint)
- [ ] Security group allows port 6379 from ECS SG only
- [ ] `PING` from ECS task returns `PONG`
- [ ] Cache miss: ~100ms, cache hit: < 2ms (speedup confirmed)
- [ ] TTL expiry works (key disappears after TTL)
- [ ] Rate limiter blocks requests after limit
- [ ] Redis NOT reachable from outside VPC
- [ ] CloudWatch shows CacheHits metric
- [ ] Terraform state contains ElastiCache resource, no drift

---

## Screenshots to Take
- [ ] ElastiCache cluster in Available state
- [ ] Redis endpoint in private subnet (not publicly accessible)
- [ ] Cache miss vs cache hit latency comparison
- [ ] Redis CLI showing keys and TTLs
- [ ] Rate limiter blocking after limit exceeded
- [ ] `terraform apply` success output
