# Verification & Validation — Project 10.2 Disaster Recovery Architecture

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| Primary RDS | RDS → Databases (us-east-1) | `handson-primary-db` Status = **Available**, Multi-AZ = Yes |
| DR RDS Replica | RDS → Databases (us-west-2) | `handson-dr-replica` Status = **Available**, Role = Read replica |
| S3 CRR | S3 → Bucket → Management → Replication | Replication rule to us-west-2 = **Enabled** |
| Route53 Health Check | Route53 → Health checks | `handson-primary-health` Status = **Healthy** |
| Route53 Failover | Route53 → Hosted zones → Records | Primary + Failover records configured |
| ECS (Primary) | ECS → Clusters (us-east-1) | `handson-cluster` running 2 tasks |
| ECS (DR) | ECS → Clusters (us-west-2) | `handson-dr-cluster` running 1 task (warm standby) |

📸 Screenshot: RDS primary and read replica both Available  
📸 Screenshot: Route53 health check showing Healthy  
📸 Screenshot: S3 replication rule enabled  
📸 Screenshot: `dr_failover.py test` output showing DR readiness

---

## 2. AWS CLI Verification

```bash
# 2.1 Confirm primary RDS is available and Multi-AZ
aws rds describe-db-instances \
  --db-instance-identifier handson-primary-db \
  --region us-east-1 \
  --query "DBInstances[0].{Status:DBInstanceStatus,MultiAZ:MultiAZ,Engine:Engine}"
# Expected: Status=available, MultiAZ=true

# 2.2 Confirm DR read replica in us-west-2
aws rds describe-db-instances \
  --db-instance-identifier handson-dr-replica \
  --region us-west-2 \
  --query "DBInstances[0].{Status:DBInstanceStatus,ReplicaOf:ReadReplicaSourceDBInstanceIdentifier,ReplicaLag:StatusInfos}"
# Expected: Status=available, ReplicaOf=handson-primary-db

# 2.3 Check replica lag
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name ReplicaLag \
  --dimensions Name=DBInstanceIdentifier,Value=handson-dr-replica \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-5M +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 \
  --statistics Average \
  --region us-west-2 \
  --query "Datapoints[*].Average"
# Expected: lag in seconds (should be < 60s for warm standby)

# 2.4 Confirm S3 cross-region replication
BUCKET=$(aws s3 ls | grep handson-data | awk '{print $3}' | head -1)
aws s3api get-bucket-replication \
  --bucket $BUCKET \
  --query "ReplicationConfiguration.Rules[*].{Status:Status,Destination:Destination.Bucket}"
# Expected: Status=Enabled, Destination=arn:aws:s3:::handson-dr-bucket-us-west-2

# 2.5 Confirm Route53 health check is healthy
HEALTH_CHECK_ID=$(aws route53 list-health-checks \
  --query "HealthChecks[?HealthCheckConfig.FullyQualifiedDomainName!=null].Id" \
  --output text | head -1)
aws route53 get-health-check-status \
  --health-check-id $HEALTH_CHECK_ID \
  --query "HealthCheckObservations[*].StatusReport.Status" | head -3
# Expected: Success

# 2.6 Test DR readiness (non-destructive)
python code/dr_failover.py test \
  --primary us-east-1 \
  --dr us-west-2
# Expected: DR readiness report — replica lag, S3 replication status, DR region health
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_db_instance.primary
# aws_db_instance.dr_replica
# aws_s3_bucket.primary
# aws_s3_bucket_replication_configuration.main
# aws_route53_health_check.primary
# aws_route53_record.primary
# aws_route53_record.failover
# aws_ecs_cluster.primary
# aws_ecs_cluster.dr

terraform state show aws_db_instance.dr_replica
# Shows: replicate_source_db=handson-primary-db, region=us-west-2

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — DR Readiness Test

```bash
# Non-destructive DR readiness check
python code/dr_failover.py test \
  --primary us-east-1 \
  --dr us-west-2

# Expected output:
# === DR Readiness Report ===
# Primary Region (us-east-1):
#   ✅ RDS: available, Multi-AZ=true
#   ✅ ECS: 2/2 tasks running
#   ✅ Route53 health check: Healthy
#
# DR Region (us-west-2):
#   ✅ RDS Replica: available, lag=2s
#   ✅ ECS: 1/1 tasks running (warm standby)
#   ✅ S3 replication: Enabled, last replicated 5 min ago
#
# RTO estimate: ~10 minutes
# RPO estimate: ~2 seconds (replica lag)
# DR Status: READY ✅
```

---

## 5. Expected Successful Outputs

**CLI — describe-db-instances (primary):**
```json
{ "Status": "available", "MultiAZ": true, "Engine": "mysql" }
```

**CLI — describe-db-instances (DR replica):**
```json
{ "Status": "available", "ReplicaOf": "handson-primary-db" }
```

**dr_failover.py test:**
```
DR Readiness: READY ✅
RDS Replica Lag: 2 seconds
S3 Replication: Enabled (last sync: 5 min ago)
DR ECS Tasks: 1/1 running
Route53 Health: Healthy
Estimated RTO: ~10 minutes
Estimated RPO: ~2 seconds
```

---

## 6. Verification Checklist

- [ ] Primary RDS Status = available, Multi-AZ = true (us-east-1)
- [ ] DR RDS read replica Status = available (us-west-2)
- [ ] RDS replica lag < 60 seconds
- [ ] S3 cross-region replication rule Status = Enabled
- [ ] Route53 health check Status = Healthy
- [ ] Route53 failover records configured (Primary + Secondary)
- [ ] Primary ECS cluster running desired task count
- [ ] DR ECS cluster running warm standby tasks (us-west-2)
- [ ] `dr_failover.py test` reports DR Status = READY
- [ ] `terraform plan` shows no changes
