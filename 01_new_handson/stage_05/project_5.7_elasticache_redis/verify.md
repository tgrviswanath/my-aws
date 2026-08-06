# Project 5.7 — Verification Guide: ElastiCache Redis

---

## Section 1: Infrastructure Verification

### 1.1 Cache Cluster is Available

```bash
AWS_REGION="us-east-1"

aws elasticache describe-cache-clusters \
  --cache-cluster-id "my-redis-dev" \
  --region $AWS_REGION \
  --query 'CacheClusters[0].{
    ID: CacheClusterId,
    Status: CacheClusterStatus,
    NodeType: CacheNodeType,
    Engine: Engine,
    EngineVersion: EngineVersion,
    NumNodes: NumCacheNodes
  }' \
  --output table
```

Expected: `Status = available`, `NodeType = cache.t3.micro`, `Engine = redis`

### 1.2 Endpoint is Available

```bash
aws elasticache describe-cache-clusters \
  --cache-cluster-id "my-redis-dev" \
  --show-cache-node-info \
  --region $AWS_REGION \
  --query 'CacheClusters[0].CacheNodes[0].Endpoint.{Host:Address,Port:Port}' \
  --output table
```

Expected: Host is a `.cache.amazonaws.com` hostname, Port is 6379.

### 1.3 Subnet Group Exists

```bash
aws elasticache describe-cache-subnet-groups \
  --cache-subnet-group-name "my-redis-subnet-group" \
  --region $AWS_REGION \
  --query 'CacheSubnetGroups[0].{Name:CacheSubnetGroupName,VPC:VpcId,Subnets:Subnets[*].SubnetIdentifier}' \
  --output table
```

Expected: 2 subnets listed in the group.

### 1.4 Security Group Allows Port 6379

```bash
REDIS_SG=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=my-redis-sg" \
  --query 'SecurityGroups[0].GroupId' \
  --output text --region $AWS_REGION)

aws ec2 describe-security-groups \
  --group-ids $REDIS_SG \
  --region $AWS_REGION \
  --query 'SecurityGroups[0].IpPermissions[?FromPort==`6379`].{Port:FromPort,Source:IpRanges[0].CidrIp}' \
  --output table
```

Expected: Port 6379 is open with a source CIDR or source security group.

### 1.5 CloudWatch Metrics Available

```bash
aws cloudwatch list-metrics \
  --namespace "AWS/ElastiCache" \
  --dimensions "Name=CacheClusterId,Value=my-redis-dev" \
  --region $AWS_REGION \
  --query 'Metrics[*].MetricName' \
  --output text | tr '\t' '\n' | sort | head -10
```

Expected: Metrics like `CacheHits`, `CacheMisses`, `CurrConnections`, `FreeableMemory` are present.

---

## Section 2: Functionality Verification

Run these commands from an EC2 instance in the same VPC (not from local machine):

### 2.1 Ping Test

```bash
# From EC2 instance — replace with actual endpoint
REDIS_HOST=$(aws elasticache describe-cache-clusters \
  --cache-cluster-id my-redis-dev \
  --show-cache-node-info \
  --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' \
  --output text --region $AWS_REGION)

redis-cli -h $REDIS_HOST -p 6379 ping
# Expected: PONG
```

### 2.2 SET and GET Operations

```bash
# Write a key
redis-cli -h $REDIS_HOST -p 6379 SET verify:test "Hello from ElastiCache"

# Read it back
RESULT=$(redis-cli -h $REDIS_HOST -p 6379 GET verify:test)
echo "GET result: $RESULT"
# Expected: Hello from ElastiCache
```

### 2.3 TTL Management Works

```bash
# Set with 30-second TTL
redis-cli -h $REDIS_HOST -p 6379 SETEX ttl:test 30 "temporary"

# Check TTL immediately
redis-cli -h $REDIS_HOST -p 6379 TTL ttl:test
# Expected: 30

# Wait 5 seconds, check again
sleep 5
redis-cli -h $REDIS_HOST -p 6379 TTL ttl:test
# Expected: ~25 (decreasing)

# After 30 seconds, key should not exist
sleep 26
redis-cli -h $REDIS_HOST -p 6379 EXISTS ttl:test
# Expected: 0 (key expired)
```

### 2.4 Connection Pool Verification (Python)

```bash
python3 -c "
import redis
import os

pool = redis.ConnectionPool(
    host=os.environ['REDIS_HOST'],
    port=6379,
    max_connections=5,
    decode_responses=True
)

r1 = redis.Redis(connection_pool=pool)
r2 = redis.Redis(connection_pool=pool)

r1.set('conn_test', 'pool_works')
result = r2.get('conn_test')
print('Connection pool test:', result)
assert result == 'pool_works', 'FAILED'
print('PASSED: Connection pool sharing works correctly')
" REDIS_HOST=$REDIS_HOST
```

### 2.5 Sorted Set Operations (Leaderboard)

```bash
# Add scores
redis-cli -h $REDIS_HOST -p 6379 ZADD leaderboard 1500 alice
redis-cli -h $REDIS_HOST -p 6379 ZADD leaderboard 2200 bob
redis-cli -h $REDIS_HOST -p 6379 ZADD leaderboard 1800 carol

# Get top 3
redis-cli -h $REDIS_HOST -p 6379 ZREVRANGE leaderboard 0 2 WITHSCORES
# Expected: bob 2200, carol 1800, alice 1500

# Clean up
redis-cli -h $REDIS_HOST -p 6379 DEL leaderboard
```

---

## Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| `Connection refused` from EC2 | `redis-cli: Could not connect to Redis at host:6379` | EC2 security group not in Redis SG inbound rules; add EC2's SG as source on port 6379 in the Redis security group |
| Cannot access from local machine | All connection attempts fail | ElastiCache is VPC-only — must use EC2, Lambda, or AWS Client VPN from within the VPC |
| High `Evictions` metric in CloudWatch | Cache is full, evicting keys | Increase node type (cache.t3.small or larger) or reduce TTLs to free memory faster |
| Redis AUTH failure | `NOAUTH Authentication required` | Redis AUTH was enabled at cluster creation — pass the token: `redis-cli -h $host -a $token`; check token in Secrets Manager |
| `TTL` returns -1 | Key exists but has no expiry | You used `SET` without `EX` option; use `EXPIRE key <seconds>` to add TTL retroactively, or `SETEX` on creation |
