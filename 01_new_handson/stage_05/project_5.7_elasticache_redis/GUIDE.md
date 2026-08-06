# Project 5.7 — ElastiCache Redis: Cluster, Cache-Aside Pattern & Connection Pooling

## Overview

Create an Amazon ElastiCache Redis cluster (cache.t3.micro), connect to it from an EC2 instance and/or Lambda function, implement the cache-aside pattern with TTL management, and configure connection pooling for production use.

---

## Prerequisites Check

```bash
# AWS CLI
aws --version

# Verify credentials
aws sts get-caller-identity

AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Check VPC
VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=isDefault,Values=true" \
  --query 'Vpcs[0].VpcId' \
  --output text --region $AWS_REGION)
echo "Default VPC: $VPC_ID"

# Check if redis-cli is available (for testing)
redis-cli --version 2>/dev/null || echo "redis-cli not installed locally — will use EC2/Docker"
```

**Required IAM permissions:**
- `elasticache:CreateCacheCluster`
- `elasticache:DescribeCacheClusters`
- `elasticache:DeleteCacheCluster`
- `elasticache:CreateCacheSubnetGroup`
- `ec2:CreateSecurityGroup`, `ec2:AuthorizeSecurityGroupIngress`

⚠️ **Note:** ElastiCache Redis clusters are **only accessible from within your VPC**. You cannot connect to them directly from your laptop. You need an EC2 instance, Lambda, or VPN in the same VPC.

---

## Decision Point 1: Redis vs Memcached

| Factor | Redis (ElastiCache) | Memcached (ElastiCache) |
|--------|--------------------|-----------------------|
| Data types | Strings, Lists, Sets, Hashes, Sorted Sets, Streams | Strings only |
| Persistence | ✅ RDB snapshots, AOF logging | ❌ No persistence |
| Pub/Sub | ✅ Native | ❌ Not supported |
| Sorted sets (leaderboards) | ✅ O(log N) | ❌ Not available |
| Multi-AZ / Failover | ✅ Automatic with replica | ❌ No replication |
| Cluster mode | ✅ Horizontal sharding | ✅ Multi-node sharding |
| Connection model | Single-threaded (fast) | Multi-threaded |
| Best for | Session storage, pub/sub, rate limiting, leaderboards ✅ | Simple key-value caching at very high throughput |

**Decision:** Use **Redis** unless you have a specific need for Memcached's multi-threaded model. Redis is the default choice for almost all modern applications.

---

## 1. Create a Cache Subnet Group

```bash
# Get subnet IDs in the default VPC
SUBNET_IDS=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[0:2].SubnetId' \
  --output text --region $AWS_REGION)

SUBNET_1=$(echo $SUBNET_IDS | awk '{print $1}')
SUBNET_2=$(echo $SUBNET_IDS | awk '{print $2}')

echo "Subnet 1: $SUBNET_1"
echo "Subnet 2: $SUBNET_2"

# Create subnet group for ElastiCache
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name "my-redis-subnet-group" \
  --cache-subnet-group-description "Redis subnet group for dev" \
  --subnet-ids $SUBNET_1 $SUBNET_2 \
  --region $AWS_REGION

echo "Cache subnet group created"
```

---

## 2. Create a Security Group for Redis

```bash
# Create Redis security group
REDIS_SG=$(aws ec2 create-security-group \
  --group-name "my-redis-sg" \
  --description "ElastiCache Redis security group" \
  --vpc-id $VPC_ID \
  --region $AWS_REGION \
  --query 'GroupId' \
  --output text)

echo "Redis Security Group: $REDIS_SG"

# Get EC2 security group ID (the app that will connect)
# For now, allow all traffic within the VPC CIDR (adjust for production)
VPC_CIDR=$(aws ec2 describe-vpcs \
  --vpc-ids $VPC_ID \
  --query 'Vpcs[0].CidrBlock' \
  --output text --region $AWS_REGION)

aws ec2 authorize-security-group-ingress \
  --group-id $REDIS_SG \
  --protocol tcp \
  --port 6379 \
  --cidr $VPC_CIDR \
  --region $AWS_REGION

echo "Security group configured to allow port 6379 from VPC CIDR $VPC_CIDR"
```

---

## 3. Create the ElastiCache Redis Cluster

### 3A. AWS Console: ElastiCache Console → Create Redis Cluster (Single Node, No Multi-AZ for Dev)

See `steps_awsconsoleui.md` for the full Console walkthrough.

### 3B. AWS CLI: aws elasticache create-cache-cluster

```bash
# Create single-node Redis cluster (dev configuration)
aws elasticache create-cache-cluster \
  --cache-cluster-id "my-redis-dev" \
  --cache-node-type "cache.t3.micro" \
  --engine "redis" \
  --engine-version "7.0" \
  --num-cache-nodes 1 \
  --cache-subnet-group-name "my-redis-subnet-group" \
  --security-group-ids $REDIS_SG \
  --region $AWS_REGION \
  --preferred-maintenance-window "sun:05:00-sun:06:00" \
  --snapshot-retention-limit 0 \
  --no-auto-minor-version-upgrade

echo "Redis cluster creation initiated..."
echo "This takes 5-10 minutes. Poll status with:"
echo "aws elasticache describe-cache-clusters --cache-cluster-id my-redis-dev --region $AWS_REGION --query 'CacheClusters[0].CacheClusterStatus'"
```

---

## 4. Wait for Cluster to Become Available

```bash
echo "Waiting for Redis cluster to become available..."

while true; do
  STATUS=$(aws elasticache describe-cache-clusters \
    --cache-cluster-id "my-redis-dev" \
    --region $AWS_REGION \
    --query 'CacheClusters[0].CacheClusterStatus' \
    --output text)
  echo "$(date): Status = $STATUS"
  if [ "$STATUS" = "available" ]; then
    break
  fi
  sleep 30
done

# Get the Redis endpoint
REDIS_ENDPOINT=$(aws elasticache describe-cache-clusters \
  --cache-cluster-id "my-redis-dev" \
  --show-cache-node-info \
  --region $AWS_REGION \
  --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' \
  --output text)

REDIS_PORT=$(aws elasticache describe-cache-clusters \
  --cache-cluster-id "my-redis-dev" \
  --show-cache-node-info \
  --region $AWS_REGION \
  --query 'CacheClusters[0].CacheNodes[0].Endpoint.Port' \
  --output text)

echo "Redis endpoint: $REDIS_ENDPOINT:$REDIS_PORT"
```

---

## 5. Connect from EC2 Instance

### 5A. AWS Console: Launch EC2 via Console

1. Go to EC2 Console → **Launch instance**
2. Choose **Amazon Linux 2023 AMI**, instance type **t3.micro**
3. Select the same VPC and a public subnet
4. Under **Security group**, select or create one that allows inbound SSH (port 22) or leave SSH closed and use Session Manager
5. Under **IAM instance profile**, attach `SSMInstanceProfile` (for Session Manager access without SSH keys)
6. In **User data**, paste:
   ```bash
   #!/bin/bash
   yum install -y redis6
   ```
7. Click **Launch instance**
8. Connect via EC2 Instance Connect or Session Manager after ~2 minutes

### 5B. AWS CLI: Launch EC2 for Redis Testing

```bash
# Launch a small EC2 instance to test Redis (in same VPC)
# Using Amazon Linux 2023 AMI

EC2_AMI=$(aws ssm get-parameters-by-path \
  --path "/aws/service/ami-amazon-linux-latest" \
  --query "Parameters[?Name=='/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64'].Value" \
  --output text --region $AWS_REGION)

EC2_SG=$(aws ec2 create-security-group \
  --group-name "my-test-ec2-sg" \
  --description "Test EC2 for Redis" \
  --vpc-id $VPC_ID \
  --region $AWS_REGION \
  --query 'GroupId' \
  --output text)

# Allow SSH (optional — can use SSM Session Manager instead)
aws ec2 authorize-security-group-ingress \
  --group-id $EC2_SG \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0 \
  --region $AWS_REGION

# Update Redis SG to allow from EC2 SG
aws ec2 authorize-security-group-ingress \
  --group-id $REDIS_SG \
  --protocol tcp \
  --port 6379 \
  --source-group $EC2_SG \
  --region $AWS_REGION

# Launch EC2 (using SSM for access — no SSH key needed)
EC2_INSTANCE=$(aws ec2 run-instances \
  --image-id $EC2_AMI \
  --instance-type t3.micro \
  --security-group-ids $EC2_SG \
  --subnet-id $SUBNET_1 \
  --associate-public-ip-address \
  --iam-instance-profile Name=SSMInstanceProfile \
  --user-data "#!/bin/bash
    yum install -y redis6
    echo 'Redis client installed'" \
  --region $AWS_REGION \
  --query 'Instances[0].InstanceId' \
  --output text)

echo "EC2 Instance: $EC2_INSTANCE"
echo "Wait 2-3 minutes for instance to start, then connect via Session Manager"
```

---

## 6. Test Redis from EC2

Once connected to EC2 via Session Manager or SSH:

```bash
# On the EC2 instance — replace with your actual endpoint
REDIS_HOST="my-redis-dev.xxxxxx.use1.cache.amazonaws.com"
REDIS_PORT=6379

# Basic connectivity test
redis-cli -h $REDIS_HOST -p $REDIS_PORT ping
# Expected: PONG

# Basic SET and GET
redis-cli -h $REDIS_HOST -p $REDIS_PORT SET mykey "Hello ElastiCache"
redis-cli -h $REDIS_HOST -p $REDIS_PORT GET mykey
# Expected: "Hello ElastiCache"

# SET with TTL (expire in 60 seconds)
redis-cli -h $REDIS_HOST -p $REDIS_PORT SETEX session:user123 60 '{"userId":"123","role":"admin"}'
redis-cli -h $REDIS_HOST -p $REDIS_PORT TTL session:user123
# Expected: 60 (decreasing)

# Check TTL after a few seconds
sleep 5
redis-cli -h $REDIS_HOST -p $REDIS_PORT TTL session:user123
# Expected: 55 (approximately)

# Test key expiry check
redis-cli -h $REDIS_HOST -p $REDIS_PORT EXISTS mykey
# Expected: 1

# Redis info
redis-cli -h $REDIS_HOST -p $REDIS_PORT INFO server | grep -E "redis_version|tcp_port"
```

---

## 7. Cache-Aside Pattern (Python Example)

```bash
# On the EC2 instance, install Python and required library
pip3 install redis

# Create cache-aside example
cat > /tmp/cache_aside.py << 'PYEOF'
import redis
import json
import time
import os

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
DEFAULT_TTL = 60  # seconds

# Connection pool — reuse connections efficiently
pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    max_connections=10,
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True,
    decode_responses=True
)

def get_redis():
    return redis.Redis(connection_pool=pool)

def get_user(user_id: str) -> dict:
    """Cache-aside pattern: check cache first, fall back to DB."""
    r = get_redis()
    cache_key = f"user:{user_id}"
    
    # 1. Check cache
    cached = r.get(cache_key)
    if cached:
        print(f"[CACHE HIT] user:{user_id}")
        return json.loads(cached)
    
    # 2. Cache miss — fetch from "database" (simulated)
    print(f"[CACHE MISS] Fetching user:{user_id} from DB")
    time.sleep(0.1)  # simulate DB latency
    
    user = {
        "id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com",
        "fetched_at": time.time()
    }
    
    # 3. Store in cache with TTL
    r.setex(cache_key, DEFAULT_TTL, json.dumps(user))
    print(f"[CACHED] user:{user_id} for {DEFAULT_TTL}s")
    
    return user

def invalidate_user(user_id: str):
    """Invalidate cache on update."""
    r = get_redis()
    r.delete(f"user:{user_id}")
    print(f"[INVALIDATED] user:{user_id}")

if __name__ == "__main__":
    # First call — cache miss, fetches from DB
    user = get_user("42")
    print("Result:", user)
    
    # Second call — cache hit
    user = get_user("42")
    print("Result:", user)
    
    # Invalidate and refetch
    invalidate_user("42")
    user = get_user("42")
    print("After invalidation:", user)
    
    # Check TTL
    r = get_redis()
    ttl = r.ttl("user:42")
    print(f"TTL remaining: {ttl}s")
PYEOF

# Run the cache-aside example
REDIS_HOST=$REDIS_HOST python3 /tmp/cache_aside.py
```

---

## 8. TTL Management Patterns

```bash
# From EC2 with redis-cli connected:

# Pattern 1: Session storage (expire on inactivity using EXPIRE + PERSIST)
redis-cli -h $REDIS_HOST SET "session:abc123" '{"user":"alice"}' EX 1800  # 30 min

# Pattern 2: Rate limiting (INCR + EXPIRE)
redis-cli -h $REDIS_HOST INCR "ratelimit:user123:$(date +%s -d 'now - now % 60')"
redis-cli -h $REDIS_HOST EXPIRE "ratelimit:user123:$(date +%s -d 'now - now % 60')" 60

# Pattern 3: Cache stampede prevention (SET NX — only set if not exists)
redis-cli -h $REDIS_HOST SET "lock:compute:job1" "locked" NX EX 30
# Only one process will get this lock

# Pattern 4: Sorted set for leaderboard
redis-cli -h $REDIS_HOST ZADD leaderboard 1500 "user:alice"
redis-cli -h $REDIS_HOST ZADD leaderboard 2200 "user:bob"
redis-cli -h $REDIS_HOST ZADD leaderboard 1800 "user:carol"
redis-cli -h $REDIS_HOST ZREVRANGE leaderboard 0 2 WITHSCORES
# Expected: bob 2200, carol 1800, alice 1500

# View all keys with pattern
redis-cli -h $REDIS_HOST KEYS "session:*"
redis-cli -h $REDIS_HOST KEYS "user:*"
```

---

## 9. Monitor Redis with CloudWatch

```bash
# ElastiCache automatically sends metrics to CloudWatch
# View key metrics
aws cloudwatch get-metric-statistics \
  --namespace "AWS/ElastiCache" \
  --metric-name "CacheHits" \
  --dimensions "Name=CacheClusterId,Value=my-redis-dev" \
  --start-time "$(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ')" \
  --end-time "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
  --period 300 \
  --statistics Sum \
  --region $AWS_REGION

# Key metrics to monitor:
# - CacheHits / CacheMisses → hit ratio
# - CurrConnections → connection pool health
# - FreeableMemory → memory pressure
# - Evictions → if > 0, cache is full and evicting keys
# - CPUUtilization → should stay < 80%
```

---

## 10. Cleanup

```bash
# Terminate EC2 test instance
aws ec2 terminate-instances \
  --instance-ids $EC2_INSTANCE \
  --region $AWS_REGION

# Delete ElastiCache cluster
aws elasticache delete-cache-cluster \
  --cache-cluster-id "my-redis-dev" \
  --region $AWS_REGION

# Wait for deletion
echo "Waiting for cluster deletion..."
while true; do
  STATUS=$(aws elasticache describe-cache-clusters \
    --cache-cluster-id "my-redis-dev" \
    --region $AWS_REGION \
    --query 'CacheClusters[0].CacheClusterStatus' \
    --output text 2>/dev/null)
  if [ -z "$STATUS" ] || echo "$STATUS" | grep -q "Error\|not found"; then
    echo "Cluster deleted"
    break
  fi
  echo "Status: $STATUS — waiting..."
  sleep 30
done

# Delete subnet group
aws elasticache delete-cache-subnet-group \
  --cache-subnet-group-name "my-redis-subnet-group" \
  --region $AWS_REGION

# Delete security groups
sleep 30  # wait for dependencies to clear
aws ec2 delete-security-group --group-id $REDIS_SG --region $AWS_REGION
aws ec2 delete-security-group --group-id $EC2_SG --region $AWS_REGION

echo "Cleanup complete"
```

---

## Troubleshooting

**Cannot connect: "Connection refused":**
- ElastiCache only accepts connections from within the VPC
- Verify your EC2/Lambda is in the same VPC
- Check security group allows port 6379 from the client's security group

**`AUTHFAILED` error:**
- If you enabled Redis AUTH (password), pass `-a <password>` to redis-cli
- For in-transit encryption, use `redis-cli --tls`

**High eviction count in CloudWatch:**
```bash
redis-cli -h $REDIS_HOST INFO memory | grep used_memory_human
# If near maxmemory, increase instance size or reduce TTLs
```

**Connection pool exhausted in Python:**
- Increase `max_connections` in ConnectionPool
- Check for connection leaks (missing `r.close()` or context managers)

---

## Expected Outcome

After completing this guide:

- ✅ ElastiCache Redis cluster (cache.t3.micro) in `available` state
- ✅ `redis-cli ping` returns PONG from EC2 in same VPC
- ✅ SET/GET operations working with correct values
- ✅ TTL (SETEX) correctly expires keys after configured time
- ✅ Cache-aside pattern Python script executes showing cache hit on second call
- ✅ Connection pool configured with max 10 connections
- ✅ CloudWatch metrics visible in Console
