# Project 10.2 — Disaster Recovery: Console UI Steps
## Visual Walkthrough for AWS Management Console

---

## Prerequisites Check

- [ ] RDS instance running in `us-east-1`
- [ ] S3 bucket with versioning enabled in `us-east-1`
- [ ] Route 53 hosted zone for your domain
- [ ] IAM permissions: `rds:*`, `s3:*`, `route53:*`
- [ ] ALBs in both `us-east-1` and `us-west-2` (or EC2 instances)

---

## Step 1 — Enable RDS Multi-AZ (Primary Region)

1. Sign in to the console — set region to **US East (N. Virginia)**
2. Navigate to **RDS** → **Databases**
3. Click on your primary database `myapp-prod-db`
4. Click **Modify** (top right)
5. Under **Availability & durability**:
   - Select **Multi-AZ DB instance** ✅
6. Scroll down → **Additional configuration** → **Backup**:
   - **Backup retention period**: `7 days`
   - **Backup window**: `03:00 - 04:00 UTC`
7. Click **Continue** → Select **Apply immediately**
8. Click **Modify DB instance**
9. Wait 10-20 minutes — status shows "Modifying" then "Available"

📸 Screenshot: RDS modify page with Multi-AZ and backup retention settings

---

## Step 2 — Create Cross-Region Read Replica

1. On the RDS database detail page for `myapp-prod-db`
2. Click **Actions** → **Create read replica**
3. **Instance specifications**:
   - **DB instance identifier**: `myapp-prod-db-replica`
   - **DB instance class**: `db.t3.medium` (smaller than primary is OK)
4. **Settings**:
   - **Destination Region**: `US West (Oregon) us-west-2`
   - **Multi-AZ deployment**: No (cost optimization for DR)
5. **Connectivity**:
   - **VPC**: Select VPC in us-west-2
   - **Publicly accessible**: Yes (or No with VPC endpoint)
6. **Additional configuration**:
   - **Enable deletion protection**: ✅
7. Click **Create read replica**
8. Wait 15-30 minutes for replica to be available

📸 Screenshot: Create read replica form showing destination region dropdown set to us-west-2

**Decision Point: Which DR strategy?**
- See GUIDE.md Decision Point 1 comparison table
- This setup implements **Pilot Light** (read replica ready, promote when needed)

---

## Step 3 — Monitor Replica Lag

1. Switch to **US West (Oregon)** region in the console
2. Navigate to **RDS** → **Databases** → `myapp-prod-db-replica`
3. Click **Monitoring** tab
4. Look for **ReplicaLag** metric:
   - Normal: < 60 seconds
   - Acceptable for 5-min RPO: < 300 seconds
5. Set up CloudWatch alarm:
   - Click **CloudWatch metrics** → **Create alarm** on ReplicaLag
   - Threshold: 300 seconds (5 minutes)

📸 Screenshot: RDS monitoring tab showing ReplicaLag graph

---

## Step 4 — Set Up S3 Cross-Region Replication

1. Switch to **US East (N. Virginia)** region
2. Navigate to **S3** → select `myapp-data-primary` bucket
3. **Enable versioning** (if not already):
   - **Properties** tab → **Bucket Versioning** → **Edit** → Enable
4. **Create replication rule**:
   - **Management** tab → **Replication rules** → **Create replication rule**
5. Configure rule:
   - **Rule name**: `replicate-to-uswest2`
   - **Status**: Enabled
   - **Source**: All objects in bucket
   - **Destination**: Select `myapp-data-dr` bucket in us-west-2
     - If bucket doesn't exist: create it first in us-west-2
   - **IAM role**: Create new role (auto-generated)
   - **Replication Time Control**: ✅ Enable (15-min SLA guarantee)
6. Click **Save**

📸 Screenshot: S3 replication rule creation with RTC (15-min guarantee) enabled

---

## Step 5 — Create Route 53 Health Check

1. Navigate to **Route 53** (global service, no region needed)
2. Click **Health checks** in left nav
3. Click **Create health check**
4. Configure:
   - **Name**: `myapp-primary-health`
   - **What to monitor**: `Endpoint`
   - **Protocol**: HTTPS
   - **Specify endpoint by**: Domain name
   - **Domain name**: Your primary ALB DNS name
   - **Port**: 443
   - **Path**: `/health`
5. **Advanced configuration**:
   - **Request interval**: Standard (30 seconds)
   - **Failure threshold**: 3 (90 seconds to failover)
6. Click **Create health check**

📸 Screenshot: Health check creation form with HTTPS endpoint and /health path

---

## Step 6 — Create Route 53 Failover Records

1. Navigate to **Route 53** → **Hosted zones** → select your zone
2. Click **Create record**
3. **Primary record:**
   - **Record name**: `api`
   - **Record type**: A
   - **Alias**: Yes → select your primary ALB (us-east-1)
   - **Routing policy**: Failover
   - **Failover record type**: Primary
   - **Health check**: Select `myapp-primary-health`
   - **Record ID**: `primary-us-east-1`
4. Click **Create records**
5. Click **Create record** again for secondary:
   - Same name: `api`
   - **Alias**: Yes → select DR ALB (us-west-2)
   - **Routing policy**: Failover
   - **Failover record type**: Secondary
   - **Record ID**: `secondary-us-west-2`
   - No health check on secondary (always available as fallback)

📸 Screenshot: Route 53 records list showing primary and secondary failover records

---

## Step 7 — Test Failover (Simulate Disaster)

1. Go to **Route 53** → **Health checks**
2. Click on `myapp-primary-health`
3. In a new tab, stop your primary ALB or block port 443
4. Watch health check status change from **Healthy** to **Unhealthy**
5. After 3 failures (90 seconds), DNS switches to secondary
6. Test: `nslookup api.yourdomain.com` should return DR ALB IP
7. Re-enable primary → after health check passes, DNS switches back

📸 Screenshot: Health check showing Unhealthy status and Route 53 switching to secondary

---

## Step 8 — Promote RDS Replica (During Real Disaster)

When primary region is truly unavailable:

1. Switch console to **US West (Oregon)** region
2. Navigate to **RDS** → **Databases** → `myapp-prod-db-replica`
3. Click **Actions** → **Promote read replica**
4. Confirm the promotion dialog
5. Wait 3-10 minutes — replica becomes standalone writable database
6. Note the new endpoint in **Connectivity & security** tab
7. Update your application's database connection string to the new endpoint

📸 Screenshot: RDS Actions dropdown showing "Promote read replica" option

**Troubleshooting — Promotion fails:**
- Ensure no ongoing replication issues (check replication lag first)
- Replica must be in "Available" state before promoting

---

## Step 9 — Monitor DR State with CloudWatch Dashboard

1. Navigate to **CloudWatch** → **Dashboards** → **Create dashboard**
2. **Dashboard name**: `DR-Monitoring`
3. Add widgets:
   - **RDS ReplicaLag** (us-west-2 region)
   - **S3 ReplicationLatency** for your bucket
   - **Route53 HealthCheckStatus**
4. Set auto-refresh to 1 minute

📸 Screenshot: CloudWatch dashboard with RPO-related metrics

---

## Step 10 — Verify Complete DR Setup

1. **RDS** (us-east-1): Primary shows Multi-AZ=Yes
2. **RDS** (us-west-2): Replica shows Status=Available, ReplicaLag < 60s
3. **S3**: Replication rule shows "Enabled" with RTC
4. **Route 53**: Two failover records for `api.yourdomain.com`
5. **Route 53 Health Checks**: Health check shows "Healthy"

📸 Screenshot: Route 53 records list with both primary (HEALTHY badge) and secondary failover records

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Replica creation fails | No automated backup on primary | Enable backup retention period (1+ days) |
| Replica lag keeps growing | Network issues or write-heavy primary | Check RDS performance insights |
| S3 replication delayed | Large objects in flight | Normal for large files; RTC gives 15-min SLA |
| Route 53 not failing over | Incorrect health check config | Verify health check passes `/health` path |
| Promoted replica not accepting writes | Still in read-only mode | Wait for promotion to fully complete |

---

## Console Navigation Quick Reference

```
DR Setup Checklist (Console)
├── RDS (us-east-1)
│   ├── Modify → Multi-AZ ✅
│   ├── Actions → Create read replica → us-west-2
│   └── Monitoring → ReplicaLag metric
├── S3 (us-east-1 bucket)
│   ├── Properties → Versioning → Enable
│   └── Management → Replication rules → Create
├── Route 53 (global)
│   ├── Health checks → Create (primary ALB)
│   └── Hosted zones → Create failover records (Primary + Secondary)
└── CloudWatch
    ├── Alarms → ReplicaLag threshold
    └── Dashboard → DR monitoring view
```
