# RDS & Aurora — Real-World Use Cases

## Use Case 1: Multi-AZ Production Database Setup

**Business Problem**: Production PostgreSQL database that survives an AZ failure with < 2 minutes downtime.

```bash
REGION="us-east-1"
RG="prod-db"

# 1. Create DB subnet group (spans 3 AZs)
aws rds create-db-subnet-group \
  --db-subnet-group-name "prod-db-subnet-group" \
  --db-subnet-group-description "Production DB subnets" \
  --subnet-ids subnet-aaa subnet-bbb subnet-ccc

# 2. Create security group (only app servers can connect)
SG_DB=$(aws ec2 create-security-group \
  --group-name "sg-rds-prod" \
  --description "RDS — only from app tier" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

aws ec2 authorize-security-group-ingress \
  --group-id $SG_DB \
  --protocol tcp --port 5432 \
  --source-group $SG_APP   # Only app servers

# 3. Store password in Secrets Manager (never hardcode!)
SECRET_ARN=$(aws secretsmanager create-secret \
  --name "prod/rds/postgres/password" \
  --secret-string '{"username":"dbadmin","password":"'$(openssl rand -base64 32)'"}' \
  --query 'ARN' --output text)

DB_PASS=$(aws secretsmanager get-secret-value \
  --secret-id "prod/rds/postgres/password" \
  --query 'SecretString' --output text | jq -r '.password')

# 4. Create Multi-AZ RDS PostgreSQL
aws rds create-db-instance \
  --db-instance-identifier "prod-postgres" \
  --db-instance-class db.r6g.large \
  --engine postgres \
  --engine-version "15.4" \
  --master-username dbadmin \
  --master-user-password "$DB_PASS" \
  --allocated-storage 100 \
  --storage-type gp3 \
  --iops 3000 \
  --storage-encrypted \
  --multi-az \
  --db-subnet-group-name "prod-db-subnet-group" \
  --vpc-security-group-ids $SG_DB \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "sun:04:00-sun:05:00" \
  --deletion-protection \
  --enable-performance-insights \
  --performance-insights-retention-period 7 \
  --enable-cloudwatch-logs-exports '["postgresql","upgrade"]' \
  --tags Key=Environment,Value=production

# 5. Wait and get endpoint
aws rds wait db-instance-available --db-instance-identifier "prod-postgres"
aws rds describe-db-instances \
  --db-instance-identifier "prod-postgres" \
  --query 'DBInstances[0].Endpoint.Address' --output text

# 6. Test failover (simulates AZ failure)
aws rds reboot-db-instance \
  --db-instance-identifier "prod-postgres" \
  --force-failover
# Monitor: endpoint stays the same, DNS updates to standby
```

**What you learn**: Multi-AZ failover, Secrets Manager integration, Performance Insights, forced failover testing.

---

## Use Case 2: Read Replicas for Reporting

**Business Problem**: Analytics queries are slowing down the production database. Separate read traffic to replicas.

```bash
# 1. Create read replica in same region
aws rds create-db-instance-read-replica \
  --db-instance-identifier "prod-postgres-replica-1" \
  --source-db-instance-identifier "prod-postgres" \
  --db-instance-class db.r6g.large \
  --availability-zone us-east-1b \
  --publicly-accessible false

# 2. Create cross-region replica for DR reads
aws rds create-db-instance-read-replica \
  --db-instance-identifier "prod-postgres-replica-eu" \
  --source-db-instance-identifier \
    "arn:aws:rds:us-east-1:123456789:db:prod-postgres" \
  --db-instance-class db.r6g.large \
  --region eu-west-1

# 3. Application connection routing (Python)
import psycopg2
import random

class DatabaseRouter:
    def __init__(self):
        self.primary = psycopg2.connect(
            host=os.environ['DB_PRIMARY_HOST'],
            database='myapp', user='dbadmin',
            password=get_secret('prod/rds/postgres/password')
        )
        self.replicas = [
            psycopg2.connect(host=replica_host, database='myapp',
                             user='dbadmin', password=get_secret(...))
            for replica_host in os.environ['DB_REPLICA_HOSTS'].split(',')
        ]

    def get_write_conn(self):
        return self.primary  # All writes → primary

    def get_read_conn(self):
        return random.choice(self.replicas)  # Round-robin reads

# Usage
router = DatabaseRouter()

# Write: always primary
with router.get_write_conn().cursor() as cur:
    cur.execute("INSERT INTO orders ...")

# Read: any replica (may be slightly behind)
with router.get_read_conn().cursor() as cur:
    cur.execute("SELECT * FROM orders WHERE ...")

# 4. Monitor replication lag
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name ReplicaLag \
  --dimensions Name=DBInstanceIdentifier,Value=prod-postgres-replica-1 \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average
```

**What you learn**: Read replica routing, replication lag monitoring, cross-region replicas for DR.

---

## Use Case 3: RDS Proxy for Lambda Connections

**Business Problem**: Lambda functions create thousands of DB connections, exhausting the connection pool.

```
Without RDS Proxy:
  1000 Lambda invocations → 1000 DB connections → DB overwhelmed

With RDS Proxy:
  1000 Lambda invocations → RDS Proxy (pool of 50 connections) → DB healthy
```

```bash
# 1. Create RDS Proxy
aws rds create-db-proxy \
  --db-proxy-name "prod-postgres-proxy" \
  --engine-family POSTGRESQL \
  --auth '[{
    "AuthScheme": "SECRETS",
    "SecretArn": "'$SECRET_ARN'",
    "IAMAuth": "REQUIRED"
  }]' \
  --role-arn arn:aws:iam::123456789:role/rds-proxy-role \
  --vpc-subnet-ids subnet-aaa subnet-bbb \
  --vpc-security-group-ids $SG_DB \
  --require-tls

# 2. Register target (point proxy to RDS instance)
aws rds register-db-proxy-targets \
  --db-proxy-name "prod-postgres-proxy" \
  --db-instance-identifiers "prod-postgres"

# 3. Get proxy endpoint
PROXY_ENDPOINT=$(aws rds describe-db-proxies \
  --db-proxy-name "prod-postgres-proxy" \
  --query 'DBProxies[0].Endpoint' --output text)

# 4. Lambda connects to proxy (not RDS directly)
# Lambda function environment variable:
# DB_HOST = prod-postgres-proxy.proxy-xxxx.us-east-1.rds.amazonaws.com

# Lambda IAM policy (for IAM auth to proxy)
aws iam put-role-policy \
  --role-name "lambda-execution-role" \
  --policy-name "RDSProxyAccess" \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": "rds-db:connect",
      "Resource": "arn:aws:rds-db:us-east-1:123456789:dbuser:prx-xxxx/dbadmin"
    }]
  }'
```

**What you learn**: Connection pooling, RDS Proxy IAM auth, Lambda + RDS architecture.

---

## Use Case 4: Aurora Serverless v2 for Variable Workloads

**Business Problem**: Dev/staging database that should cost $0 when not in use but scale instantly for load tests.

```bash
# 1. Create Aurora Serverless v2 cluster
aws rds create-db-cluster \
  --db-cluster-identifier "dev-aurora-serverless" \
  --engine aurora-postgresql \
  --engine-version "15.4" \
  --master-username dbadmin \
  --manage-master-user-password \
  --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=16 \
  --db-subnet-group-name "dev-db-subnet-group" \
  --vpc-security-group-ids $SG_DB \
  --storage-encrypted \
  --deletion-protection false

# 2. Add serverless writer instance
aws rds create-db-instance \
  --db-instance-identifier "dev-aurora-serverless-writer" \
  --db-cluster-identifier "dev-aurora-serverless" \
  --db-instance-class db.serverless \
  --engine aurora-postgresql

# 3. Monitor ACU usage (billing)
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name ServerlessDatabaseCapacity \
  --dimensions Name=DBClusterIdentifier,Value=dev-aurora-serverless \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 \
  --statistics Average

# Cost: 0.5 ACU minimum × $0.12/ACU-hr = $0.06/hr when idle
# vs db.t3.medium always-on = $0.068/hr
# Serverless scales to 0 ACU after 5 min of inactivity (pause feature)
```

**What you learn**: Aurora Serverless v2 scaling, ACU billing, pause/resume for dev environments.

---

## Use Case 5: Point-in-Time Recovery (PITR)

**Business Problem**: Developer accidentally ran `DELETE FROM orders WHERE 1=1`. Restore to 5 minutes before the mistake.

```bash
# 1. Find the time just before the accident
# (Check CloudTrail or application logs for the exact time)
RESTORE_TIME="2024-01-15T14:25:00Z"  # 5 min before accident at 14:30

# 2. Restore to new instance (non-destructive — original still running)
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier "prod-postgres" \
  --target-db-instance-identifier "prod-postgres-restored" \
  --restore-time $RESTORE_TIME \
  --db-instance-class db.r6g.large \
  --db-subnet-group-name "prod-db-subnet-group" \
  --vpc-security-group-ids $SG_DB

# 3. Wait for restore to complete
aws rds wait db-instance-available \
  --db-instance-identifier "prod-postgres-restored"

# 4. Connect to restored instance and export the missing data
RESTORED_HOST=$(aws rds describe-db-instances \
  --db-instance-identifier "prod-postgres-restored" \
  --query 'DBInstances[0].Endpoint.Address' --output text)

# Export deleted orders to CSV
psql -h $RESTORED_HOST -U dbadmin -d myapp \
  -c "\COPY (SELECT * FROM orders WHERE deleted_at IS NULL) TO '/tmp/recovered_orders.csv' CSV HEADER"

# 5. Import recovered data back to production
psql -h $PROD_HOST -U dbadmin -d myapp \
  -c "\COPY orders FROM '/tmp/recovered_orders.csv' CSV HEADER ON CONFLICT DO NOTHING"

# 6. Delete the restored instance (costs money while running)
aws rds delete-db-instance \
  --db-instance-identifier "prod-postgres-restored" \
  --skip-final-snapshot
```

**What you learn**: PITR restore, non-destructive recovery, data export/import pattern.

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Single-AZ in production | AZ failure = hours of downtime | Always use Multi-AZ |
| Hardcoding DB password | Credential exposure | Use Secrets Manager |
| No deletion protection | Accidental DB deletion | Enable `--deletion-protection` |
| Lambda connecting directly to RDS | Connection exhaustion | Use RDS Proxy |
| Not monitoring replication lag | Stale reads from replica | Alert when lag > 30 seconds |
| Skipping Performance Insights | Can't diagnose slow queries | Enable from day 1 (free 7 days) |
