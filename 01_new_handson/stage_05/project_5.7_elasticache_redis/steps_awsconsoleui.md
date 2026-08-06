# Project 5.7 — AWS Console UI Steps: ElastiCache Redis

## Prerequisites Check

- [ ] AWS Console access with ElastiCache and EC2 permissions
- [ ] Default VPC exists with at least 2 subnets
- [ ] Note: ElastiCache clusters are VPC-only — no public internet access
- [ ] Plan to use EC2 or Lambda in same VPC for testing
- [ ] Region selected in Console (ElastiCache availability varies by region)

---

## Step 1: Open ElastiCache Console

1. Sign in to [AWS Console](https://console.aws.amazon.com)
2. In the search bar, type **ElastiCache** → click **ElastiCache**
3. You land on the ElastiCache dashboard
4. In the left sidebar, you see:
   - **Redis clusters** — for creating Redis (cluster or non-cluster mode)
   - **Memcached clusters** — for Memcached only
   - **Global datastores** — cross-region replication (advanced)
   - **Subnet groups** — required before cluster creation

📸 Screenshot checkpoint: ElastiCache dashboard showing left sidebar navigation and Redis clusters option

---

## Step 2: Create a Subnet Group

A cache subnet group tells ElastiCache which subnets to use within your VPC.

1. In the left sidebar, click **Subnet groups** (under Redis OSS caches or standalone)
2. Click **Create subnet group**
3. Configure:
   - Name: `my-redis-subnet-group`
   - Description: `Redis subnet group for dev`
   - VPC: select your default VPC (note the VPC ID)
4. Under **Add subnets**:
   - The console shows available AZs — select at least 2 subnets in different AZs
   - Check 2+ subnets
5. Click **Create**

📸 Screenshot checkpoint: Create subnet group form showing VPC selected and 2 subnets checked in different AZs

---

## Step 3: Create a Redis Cluster

1. Click **Redis clusters** in the left sidebar
2. Click **Create Redis cluster**
3. Choose:
   - **Cluster mode**: ❌ Disabled (single shard, simpler for dev)
   - Alternative: Enabled = horizontal sharding (for large datasets)

📸 Screenshot checkpoint: Cluster creation page showing "Cluster mode disabled" option selected

---

## Step 4: Configure Cluster Settings

1. **Cluster info:**
   - Name: `my-redis-dev`
   - Description: `Development Redis cluster`
   - Location: **AWS Cloud**
   - Engine version: **7.0** (or latest stable)
   - Port: **6379** (default)
   - Parameter group: `default.redis7` (default)
   - Node type: click **Change node type** → select **cache.t3.micro**
   
   ⚠️ Important: **There is no free tier for ElastiCache** — cache.t3.micro is the cheapest option at ~$0.017/hour

2. **Replicas:**
   - Number of replicas: **0** (no replica for dev — saves cost)
   - Multi-AZ: **Disabled** (no failover for dev)

3. Click **Next**

📸 Screenshot checkpoint: Cluster info showing name `my-redis-dev`, engine 7.0, node type cache.t3.micro

---

## Step 5: Configure Advanced Settings

1. **Subnet group:**
   - Select: `my-redis-subnet-group` (created in Step 2)

2. **Security groups:**
   - Click **Manage** → add your Redis security group (`my-redis-sg`)
   - If no security group exists yet, create one first (see GUIDE.md Step 2)

3. **Encryption at rest:**
   - Enable: **Disabled** for dev (no additional cost either way)
   - For production: enable with AWS KMS

4. **Encryption in transit:**
   - Enable: **Disabled** for dev (simplifies connection setup)
   - For production: enable and use TLS in your client

5. **Redis AUTH:**
   - Leave disabled for dev (no password)
   - For production: enable and set a strong password

6. **Backups:**
   - Enable automatic backups: **Disabled** for dev (saves storage cost)
   - Snapshot retention: 0 days

7. **Maintenance:**
   - Maintenance window: leave as default (any Sunday 05:00-06:00 UTC)

8. Click **Next**

📸 Screenshot checkpoint: Advanced settings showing subnet group `my-redis-subnet-group` and security group selected

---

## Step 6: Review and Create

1. Review the summary:
   - Cluster ID: `my-redis-dev`
   - Node type: `cache.t3.micro`
   - Engine: `Redis 7.0`
   - Replicas: 0
   - Subnet group: `my-redis-subnet-group`
   - Encryption: Disabled
   - Estimated cost: ~$0.017/hour
2. Click **Create**

📸 Screenshot checkpoint: Review page showing all cluster settings before clicking Create

---

## Step 7: Monitor Cluster Creation

1. You're redirected to the Redis clusters list
2. The cluster `my-redis-dev` shows status: **Creating**
3. Creation takes 5-10 minutes
4. Refresh the page periodically — status changes to **Available**

📸 Screenshot checkpoint: Redis clusters list showing `my-redis-dev` with status "Creating" then "Available"

---

## Step 8: Find the Endpoint

1. Once status is **Available**, click on `my-redis-dev`
2. In the **Cluster detail** page, find:
   - **Primary endpoint**: `my-redis-dev.xxxxxx.0001.use1.cache.amazonaws.com:6379`
3. Copy this endpoint — you'll need it to connect from EC2 or Lambda

📸 Screenshot checkpoint: Cluster detail page showing Primary endpoint with hostname and port 6379

---

## Decision Point: Single Node vs Multi-AZ Replica

| Configuration | Dev | Production |
|--------------|-----|-----------|
| Single node, no replica | ✅ Cheapest | ❌ Single point of failure |
| 1 replica, Multi-AZ enabled | Over-engineered for dev | ✅ Automatic failover |
| Cluster mode enabled | Complex, not needed for small data | ✅ For datasets > 100GB |

For this learning project, single node is appropriate. Enable Multi-AZ in production.

---

## Step 9: Connect from EC2 (Same VPC)

You cannot connect to ElastiCache from your laptop directly. Use an EC2 instance in the same VPC.

1. Launch an EC2 instance (t3.micro, Amazon Linux 2023) in the same VPC
2. Ensure EC2's security group is allowed in the Redis security group (port 6379)
3. Connect via Session Manager or SSH
4. On the EC2 instance:

```bash
# Install Redis client on Amazon Linux 2023
sudo yum install -y redis6

# Test connection (replace with your actual endpoint)
redis-cli -h my-redis-dev.xxxxxx.0001.use1.cache.amazonaws.com -p 6379 ping
# Expected: PONG

# Basic operations
redis-cli -h my-redis-dev.xxxxxx.0001.use1.cache.amazonaws.com -p 6379 SET hello world
redis-cli -h my-redis-dev.xxxxxx.0001.use1.cache.amazonaws.com -p 6379 GET hello
# Expected: world

# SET with TTL
redis-cli -h my-redis-dev.xxxxxx.0001.use1.cache.amazonaws.com -p 6379 SETEX mykey 30 "temporary value"
redis-cli -h my-redis-dev.xxxxxx.0001.use1.cache.amazonaws.com -p 6379 TTL mykey
# Expected: 30 (then decreasing)
```

📸 Screenshot checkpoint: EC2 terminal showing `redis-cli ping` returning PONG and SET/GET operations succeeding

---

## Step 10: Monitor Metrics in Console

1. Click on `my-redis-dev` in ElastiCache Console
2. Navigate to the **Metrics** tab
3. View key metrics:
   - **CacheHits** / **CacheMisses** — hit rate
   - **CurrConnections** — active connections
   - **FreeableMemory** — available memory
   - **Evictions** — if > 0, your cache is full
   - **CPUUtilization** — should stay < 80%
4. Click **View in CloudWatch** to set up dashboards and alarms

📸 Screenshot checkpoint: ElastiCache cluster metrics tab showing CacheHits, CacheMisses, and FreeableMemory graphs

---

## Cleanup via Console

1. Go to ElastiCache → **Redis clusters**
2. Select `my-redis-dev` (checkbox)
3. Click **Actions** → **Delete**
4. In the dialog:
   - Create a final backup: **No** (for dev)
5. Click **Delete**
6. Status shows **Deleting** → cluster disappears after ~5 minutes

After cluster deletion:
7. Go to **Subnet groups** → delete `my-redis-subnet-group`
8. Go to EC2 → Security Groups → delete `my-redis-sg`

📸 Screenshot checkpoint: Delete cluster confirmation dialog for `my-redis-dev`

---

## Troubleshooting

**Cannot connect from EC2 (`Connection refused`):**
- Security group on Redis cluster must allow port 6379 from EC2's security group
- In ElastiCache → `my-redis-dev` → **Modify** → Security groups → add your EC2's SG
- EC2 must be in the same VPC as the Redis cluster

**Status stuck at "Creating" for more than 15 minutes:**
- This is unusual — check for VPC/subnet issues
- Verify the subnet group uses subnets that exist in your VPC
- Try deleting and recreating the cluster

**`redis-cli` not found on Amazon Linux:**
```bash
sudo yum install -y redis6        # Amazon Linux 2023
# or
sudo amazon-linux-extras install redis6  # Amazon Linux 2
```

**"Cannot delete subnet group" error on cleanup:**
- Must delete all clusters using the subnet group before deleting the group
- Wait for cluster deletion to complete first (5-10 minutes)
