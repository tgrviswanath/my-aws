# Project 10.2 — Disaster Recovery on AWS
## Cross-Region RDS Replica + S3 Replication + Route 53 Failover — RTO < 30 min, RPO < 5 min

---

## Prerequisites Check

- [ ] AWS CLI configured: `aws sts get-caller-identity`
- [ ] IAM permissions: `rds:*`, `s3:*`, `route53:*`
- [ ] Primary region: `us-east-1` | DR region: `us-west-2`
- [ ] RDS instance running in primary region
- [ ] Route 53 hosted zone for your domain
- [ ] S3 versioning enabled on source bucket (required for replication)

```bash
PRIMARY_REGION="us-east-1"
DR_REGION="us-west-2"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
PRIMARY_DB="myapp-prod-db"
```

---

## Decision Point 1

**DR Strategy — which tier fits your requirements?**

| Strategy | RTO | RPO | Cost | Complexity |
|----------|-----|-----|------|-----------|
| **Backup & Restore** ✅ cheapest | Hours | Hours | $ | Low |
| **Pilot Light** ✅ balanced | 10-30 min | Minutes | $$ | Medium |
| **Warm Standby** | Minutes | Seconds | $$$ | High |
| **Multi-Site Active/Active** ✅ most expensive | < 1 min | Near-zero | $$$$ | Very High |

**For this project (RTO < 30 min, RPO < 5 min) → Pilot Light:**
- Cross-region RDS read replica (can be promoted in < 5 min)
- S3 CRR for data (continuous, < 1 min replication lag)
- Route 53 health checks with failover (DNS cutover < 60 sec)
- Minimal DR infrastructure running until needed

**Verdict:** Pilot Light ✅ — meets RTO/RPO requirements at reasonable cost.

---

## 1. Architecture Overview

```
PRIMARY REGION (us-east-1)                DR REGION (us-west-2)
                                          
Route 53 Primary Record ──→ ALB → EC2     Route 53 Secondary Record
                                               (active when primary fails)
RDS Multi-AZ (primary/standby)  ───────→  RDS Read Replica
                │ replication                    │ promote if primary fails
                │                                ▼
                                           RDS Standalone DB
S3 Bucket (source)  ────────────────────→ S3 Bucket (replica)
    versioning ON                             CRR enabled

CloudWatch Health Check (us-east-1)
    → triggers Route 53 DNS failover to us-west-2
    → RPO: < 5 min | RTO: < 30 min
```

---

## 2. Enable RDS Multi-AZ in Primary Region

```bash
# Create/modify RDS to Multi-AZ (primary protection)
aws rds modify-db-instance \
  --db-instance-identifier $PRIMARY_DB \
  --multi-az \
  --apply-immediately \
  --region $PRIMARY_REGION

# Enable automated backups (required for cross-region replica)
aws rds modify-db-instance \
  --db-instance-identifier $PRIMARY_DB \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --apply-immediately \
  --region $PRIMARY_REGION

# Check status
aws rds describe-db-instances \
  --db-instance-identifier $PRIMARY_DB \
  --region $PRIMARY_REGION \
  --query 'DBInstances[0].{MultiAZ:MultiAZ,BackupRetention:BackupRetentionPeriod,Status:DBInstanceStatus}'
```

---

## 3. Create Cross-Region Read Replica

```bash
# Get primary RDS ARN
PRIMARY_DB_ARN=$(aws rds describe-db-instances \
  --db-instance-identifier $PRIMARY_DB \
  --region $PRIMARY_REGION \
  --query 'DBInstances[0].DBInstanceArn' \
  --output text)

# Create read replica in DR region
aws rds create-db-instance-read-replica \
  --db-instance-identifier "${PRIMARY_DB}-replica" \
  --source-db-instance-identifier $PRIMARY_DB_ARN \
  --db-instance-class db.t3.medium \
  --source-region $PRIMARY_REGION \
  --region $DR_REGION \
  --publicly-accessible \
  --deletion-protection \
  --tags '[
    {"Key":"Role","Value":"disaster-recovery"},
    {"Key":"SourceRegion","Value":"us-east-1"}
  ]'

echo "DR replica creation initiated (takes 15-30 minutes)"

# Monitor replica lag
watch -n 30 "aws rds describe-db-instances \
  --db-instance-identifier ${PRIMARY_DB}-replica \
  --region $DR_REGION \
  --query 'DBInstances[0].{Status:DBInstanceStatus,ReplicaLag:ReplicaLag}'"
```

---

## 4. Set Up S3 Cross-Region Replication

```bash
PRIMARY_BUCKET="myapp-data-primary-${ACCOUNT_ID}"
DR_BUCKET="myapp-data-dr-${ACCOUNT_ID}"

# Enable versioning on primary bucket (required for CRR)
aws s3api put-bucket-versioning \
  --bucket $PRIMARY_BUCKET \
  --versioning-configuration Status=Enabled \
  --region $PRIMARY_REGION

# Create DR bucket in secondary region
aws s3 mb s3://${DR_BUCKET} --region $DR_REGION

# Enable versioning on DR bucket
aws s3api put-bucket-versioning \
  --bucket $DR_BUCKET \
  --versioning-configuration Status=Enabled \
  --region $DR_REGION

# Create replication role
cat > /tmp/s3-replication-trust.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "s3.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

REPLICATION_ROLE_ARN=$(aws iam create-role \
  --role-name S3CrossRegionReplicationRole \
  --assume-role-policy-document file:///tmp/s3-replication-trust.json \
  --query 'Role.Arn' --output text)

# Attach replication policy
cat > /tmp/s3-replication-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetReplicationConfiguration","s3:ListBucket"],
      "Resource": "arn:aws:s3:::${PRIMARY_BUCKET}"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObjectVersionForReplication","s3:GetObjectVersionAcl","s3:GetObjectVersionTagging"],
      "Resource": "arn:aws:s3:::${PRIMARY_BUCKET}/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ReplicateObject","s3:ReplicateDelete","s3:ReplicateTags"],
      "Resource": "arn:aws:s3:::${DR_BUCKET}/*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name S3CrossRegionReplicationRole \
  --policy-name S3ReplicationPolicy \
  --policy-document file:///tmp/s3-replication-policy.json

# Configure replication
aws s3api put-bucket-replication \
  --bucket $PRIMARY_BUCKET \
  --replication-configuration "{
    \"Role\": \"$REPLICATION_ROLE_ARN\",
    \"Rules\": [{
      \"ID\": \"ReplicateAll\",
      \"Status\": \"Enabled\",
      \"Filter\": {\"Prefix\": \"\"},
      \"Destination\": {
        \"Bucket\": \"arn:aws:s3:::${DR_BUCKET}\",
        \"ReplicationTime\": {
          \"Status\": \"Enabled\",
          \"Time\": {\"Minutes\": 15}
        },
        \"Metrics\": {\"Status\": \"Enabled\"},
        \"StorageClass\": \"STANDARD\"
      },
      \"DeleteMarkerReplication\": {\"Status\": \"Enabled\"}
    }]
  }" \
  --region $PRIMARY_REGION
```

---

## 5A. Console: Configure Route 53 Failover

1. Navigate to **Route 53** → **Hosted zones** → select your zone
2. Create **Health check** for primary:
   - **Name**: `myapp-primary-health`
   - **Endpoint**: IP/domain of primary ALB
   - **Protocol**: HTTPS, Port 443
   - **Path**: `/health`
   - **Failure threshold**: 3 consecutive failures
3. Create **Primary failover record**:
   - **Record name**: `api.yourdomain.com`
   - **Type**: A (Alias pointing to primary ALB)
   - **Routing policy**: Failover
   - **Failover record type**: Primary
   - **Health check**: Select `myapp-primary-health`
4. Create **Secondary failover record**:
   - **Record name**: `api.yourdomain.com`
   - **Type**: A (Alias pointing to DR region ALB)
   - **Routing policy**: Failover
   - **Failover record type**: Secondary
   - No health check required on secondary

---

## 5B. CLI: Route 53 Health Check and Failover Records

```bash
# Get primary ALB details
PRIMARY_ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names myapp-primary-alb \
  --region $PRIMARY_REGION \
  --query 'LoadBalancers[0].DNSName' --output text)

DR_ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names myapp-dr-alb \
  --region $DR_REGION \
  --query 'LoadBalancers[0].DNSName' --output text)

# Create health check for primary
HEALTH_CHECK_ID=$(aws route53 create-health-check \
  --caller-reference "primary-$(date +%s)" \
  --health-check-config "{
    \"FullyQualifiedDomainName\": \"$PRIMARY_ALB_DNS\",
    \"Port\": 443,
    \"Type\": \"HTTPS\",
    \"ResourcePath\": \"/health\",
    \"RequestInterval\": 30,
    \"FailureThreshold\": 3,
    \"EnableSNI\": true
  }" \
  --query 'HealthCheck.Id' --output text)

HOSTED_ZONE_ID="Z1234567890ABC"  # Your hosted zone ID

# Create failover records
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch "{
    \"Changes\": [
      {
        \"Action\": \"CREATE\",
        \"ResourceRecordSet\": {
          \"Name\": \"api.yourdomain.com\",
          \"Type\": \"CNAME\",
          \"SetIdentifier\": \"primary\",
          \"Failover\": \"PRIMARY\",
          \"TTL\": 60,
          \"HealthCheckId\": \"$HEALTH_CHECK_ID\",
          \"ResourceRecords\": [{\"Value\": \"$PRIMARY_ALB_DNS\"}]
        }
      },
      {
        \"Action\": \"CREATE\",
        \"ResourceRecordSet\": {
          \"Name\": \"api.yourdomain.com\",
          \"Type\": \"CNAME\",
          \"SetIdentifier\": \"secondary\",
          \"Failover\": \"SECONDARY\",
          \"TTL\": 60,
          \"ResourceRecords\": [{\"Value\": \"$DR_ALB_DNS\"}]
        }
      }
    ]
  }"
```

---

## 6. Promote RDS Replica During Failover

```bash
# DISASTER SCENARIO: Primary region is down
# Step 1: Promote read replica to standalone DB in DR region

aws rds promote-read-replica \
  --db-instance-identifier "${PRIMARY_DB}-replica" \
  --region $DR_REGION \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00"

# Monitor promotion (takes 3-10 minutes)
watch -n 10 "aws rds describe-db-instances \
  --db-instance-identifier ${PRIMARY_DB}-replica \
  --region $DR_REGION \
  --query 'DBInstances[0].{Status:DBInstanceStatus,MultiAZ:MultiAZ}'"

# Step 2: Get new DB endpoint in DR region
DR_DB_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier "${PRIMARY_DB}-replica" \
  --region $DR_REGION \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

echo "DR Database endpoint: $DR_DB_ENDPOINT"

# Step 3: Update Secrets Manager in DR region with new endpoint
aws secretsmanager put-secret-value \
  --secret-id "prod/myapp/rds-credentials" \
  --secret-string "{
    \"host\": \"$DR_DB_ENDPOINT\",
    \"port\": 5432,
    \"username\": \"admin\",
    \"password\": \"YOUR_PASSWORD\"
  }" \
  --region $DR_REGION
```

---

## 7. Test Failover (Chaos Engineering)

```bash
# Test Route 53 failover by temporarily blocking health check endpoint
# DO NOT do this in production without change window

# 1. Check current DNS resolution
nslookup api.yourdomain.com

# 2. Force health check to fail (add restrictive SG rule temporarily)
# 3. Wait 3 health check intervals (90 seconds)
# 4. Verify DNS now resolves to DR region ALB
nslookup api.yourdomain.com
# Should now return DR ALB IP

# Check health check status
aws route53 get-health-check-status \
  --health-check-id $HEALTH_CHECK_ID \
  --query 'HealthCheckObservations[].{Region:Region,Status:StatusReport.Status}'
```

---

## 8. Set Up DR Runbook Automation

```bash
# Create SSM document for DR failover runbook
cat > /tmp/dr-runbook.json << 'EOF'
{
  "schemaVersion": "2.2",
  "description": "DR Failover Runbook for myapp",
  "mainSteps": [
    {
      "action": "aws:runShellScript",
      "name": "PromoteRDSReplica",
      "inputs": {
        "runCommand": [
          "aws rds promote-read-replica --db-instance-identifier myapp-prod-db-replica --region us-west-2",
          "echo 'RDS promotion initiated'"
        ]
      }
    }
  ]
}
EOF

aws ssm create-document \
  --name "DR-Failover-Runbook" \
  --document-type Command \
  --content file:///tmp/dr-runbook.json
```

---

## 9. Monitor Replication Lag

```bash
# CloudWatch alarm for replication lag
aws cloudwatch put-metric-alarm \
  --alarm-name "RDS-ReplicaLag-High" \
  --alarm-description "RDS replica lag exceeds 5 minutes — RPO at risk" \
  --namespace AWS/RDS \
  --metric-name ReplicaLag \
  --dimensions Name=DBInstanceIdentifier,Value="${PRIMARY_DB}-replica" \
  --statistic Average \
  --period 60 \
  --threshold 300 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions "arn:aws:sns:${DR_REGION}:${ACCOUNT_ID}:dr-alerts" \
  --region $DR_REGION

# Check current replication metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name ReplicaLag \
  --dimensions Name=DBInstanceIdentifier,Value="${PRIMARY_DB}-replica" \
  --start-time $(date -d '1 hour ago' --utc +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date --utc +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 \
  --statistics Average \
  --region $DR_REGION
```

---

## 10. Verify Complete DR Setup

```bash
echo "=== Disaster Recovery Verification ==="

# 1. RDS Multi-AZ enabled
aws rds describe-db-instances \
  --db-instance-identifier $PRIMARY_DB \
  --region $PRIMARY_REGION \
  --query 'DBInstances[0].MultiAZ'

# 2. Read replica in DR region
aws rds describe-db-instances \
  --db-instance-identifier "${PRIMARY_DB}-replica" \
  --region $DR_REGION \
  --query 'DBInstances[0].{Status:DBInstanceStatus,ReplicaLag:ReplicaLag}'

# 3. S3 replication configured
aws s3api get-bucket-replication --bucket $PRIMARY_BUCKET \
  --query 'ReplicationConfiguration.Rules[0].Status'

# 4. Route 53 health check active
aws route53 get-health-check \
  --health-check-id $HEALTH_CHECK_ID \
  --query 'HealthCheck.HealthCheckConfig.{Type:Type,Threshold:FailureThreshold}'

# 5. Failover records exist
aws route53 list-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --query 'ResourceRecordSets[?Name==`api.yourdomain.com.`].{Name:Name,SetId:SetIdentifier,Failover:Failover}'

echo "=== DR Verification Complete ==="
echo "RPO target: < 5 min (RDS replica lag + S3 replication)"
echo "RTO target: < 30 min (promote replica + DNS failover)"
```

---

## Troubleshooting

**RDS replica lag high:**
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS --metric-name ReplicaLag \
  --dimensions Name=DBInstanceIdentifier,Value="${PRIMARY_DB}-replica" \
  --start-time $(date -d '30 min ago' --utc +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date --utc +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Average --region $DR_REGION
```

**S3 replication not working:**
```bash
aws s3api get-bucket-replication-metrics --bucket $PRIMARY_BUCKET
# Check replication role permissions
```

**Route 53 health check failing:**
```bash
aws route53 get-health-check-status --health-check-id $HEALTH_CHECK_ID
# Ensure security group allows Route 53 health checkers (53.x.x.x range)
```

---

## Expected Outcome

- ✅ RDS Multi-AZ primary in us-east-1
- ✅ Cross-region read replica in us-west-2 (< 5 min lag = RPO met)
- ✅ S3 CRR with Replication Time Control (15-min SLA)
- ✅ Route 53 failover records with health checks
- ✅ DNS failover in < 60 seconds when primary fails
- ✅ Manual replica promotion procedure documented and tested
- ✅ CloudWatch alerts for replication lag

---

## Cleanup

```bash
# Delete Route 53 failover records
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{"Changes":[{"Action":"DELETE","ResourceRecordSet":{"Name":"api.yourdomain.com","Type":"CNAME","SetIdentifier":"primary","Failover":"PRIMARY","TTL":60,"ResourceRecords":[{"Value":"PRIMARY_ALB_DNS"}]}}]}'

# Delete health check
aws route53 delete-health-check --health-check-id $HEALTH_CHECK_ID

# Delete DR RDS replica
aws rds delete-db-instance \
  --db-instance-identifier "${PRIMARY_DB}-replica" \
  --skip-final-snapshot \
  --region $DR_REGION

# Delete S3 replication
aws s3api delete-bucket-replication --bucket $PRIMARY_BUCKET
aws s3 rm s3://${DR_BUCKET} --recursive
aws s3 rb s3://${DR_BUCKET} --region $DR_REGION

# Delete replication IAM role
aws iam delete-role-policy \
  --role-name S3CrossRegionReplicationRole \
  --policy-name S3ReplicationPolicy
aws iam delete-role --role-name S3CrossRegionReplicationRole

echo "DR cleanup complete"
```

---

## 5. Hands-on Implementation

### 5A. AWS Console Method
Follow the steps_awsconsoleui.md guide for step-by-step console walkthrough.

**Summary:**
1. Navigate to the relevant AWS service console
2. Create required resources using the wizard
3. Configure settings per the architecture
4. Test the deployment

### 5B. AWS CLI Method
Follow the steps.md guide for complete CLI command reference.

`ash
# Set region
export AWS_DEFAULT_REGION=us-east-1

# Verify identity
aws sts get-caller-identity

# Create main resource (see steps.md for full commands)
aws ec2 describe-vpcs --output table
`

**Prerequisites Check:**
- âœ… AWS CLI configured with ws configure
- âœ… Correct region set to us-east-1
- âœ… IAM permissions verified

**Decision Point 1:** Console vs CLI implementation
| Option | Pros | For This Project |
|--------|------|-----------------|
| AWS Console | Visual, beginner-friendly | âœ… First time |
| AWS CLI | Repeatable, scriptable | âœ… Automation |

**Expected Outcome:** All resources deployed and healthy in AWS Console.

**Troubleshooting:** If deployment fails, check IAM permissions and CloudWatch Logs.
