# RDS & Aurora — Managed Relational Databases

## Amazon RDS

RDS manages relational databases — provisioning, patching, backups, and failover are handled by AWS.

### Supported Engines
- MySQL, PostgreSQL, MariaDB
- Oracle, SQL Server
- Aurora MySQL, Aurora PostgreSQL

### RDS vs Self-Managed EC2 Database

| Feature | RDS | EC2 + DB |
|---------|-----|---------|
| OS access | ❌ | ✅ |
| Automated backups | ✅ | Manual |
| Multi-AZ failover | ✅ | Manual |
| Read replicas | ✅ | Manual |
| Patching | AWS managed | You manage |
| Cost | Higher | Lower |
| Control | Less | Full |

---

## RDS Instance Classes

| Class | Use Case |
|-------|---------|
| db.t3/t4g | Dev/test, low traffic |
| db.m5/m6i | General production |
| db.r5/r6i | Memory-intensive (large datasets) |
| db.x2g | Largest memory (SAP HANA) |

---

## Multi-AZ Deployment

Synchronous replication to standby in another AZ. Automatic failover in 1-2 minutes.

```
Primary (us-east-1a) ←→ Synchronous replication ←→ Standby (us-east-1b)
        ↑
   DNS endpoint (same endpoint, auto-switches on failover)
```

```bash
# Create Multi-AZ RDS instance
aws rds create-db-instance \
  --db-instance-identifier prod-mysql \
  --db-instance-class db.m5.large \
  --engine mysql \
  --engine-version 8.0.35 \
  --master-username admin \
  --master-user-password "$(aws secretsmanager get-secret-value \
    --secret-id prod/mysql/password --query SecretString --output text)" \
  --allocated-storage 100 \
  --storage-type gp3 \
  --iops 3000 \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:us-east-1:123456789:key/abc-123 \
  --multi-az \
  --db-subnet-group-name prod-db-subnet-group \
  --vpc-security-group-ids sg-db-12345678 \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "sun:04:00-sun:05:00" \
  --deletion-protection \
  --enable-performance-insights \
  --performance-insights-retention-period 7 \
  --enable-cloudwatch-logs-exports '["error","general","slowquery"]'
```

---

## Read Replicas

Asynchronous replication for read scaling. Up to 15 replicas (Aurora), 5 (RDS).

```bash
# Create read replica
aws rds create-db-instance-read-replica \
  --db-instance-identifier prod-mysql-replica-1 \
  --source-db-instance-identifier prod-mysql \
  --db-instance-class db.m5.large \
  --availability-zone us-east-1b \
  --publicly-accessible false

# Promote replica to standalone (for migration/DR)
aws rds promote-read-replica \
  --db-instance-identifier prod-mysql-replica-1

# Cross-region read replica
aws rds create-db-instance-read-replica \
  --db-instance-identifier prod-mysql-replica-eu \
  --source-db-instance-identifier arn:aws:rds:us-east-1:123456789:db:prod-mysql \
  --db-instance-class db.m5.large \
  --region eu-west-1
```

---

## RDS Backups

```bash
# Automated backups (point-in-time recovery)
# Retention: 1-35 days
# Stored in S3 (free up to DB size)

# Manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier prod-mysql \
  --db-snapshot-identifier prod-mysql-snapshot-$(date +%Y%m%d)

# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier prod-mysql-restored \
  --db-snapshot-identifier prod-mysql-snapshot-20240101

# Point-in-time restore
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier prod-mysql \
  --target-db-instance-identifier prod-mysql-pitr \
  --restore-time 2024-01-15T10:30:00Z
```

---

## RDS Proxy

Manages connection pooling — critical for Lambda and serverless workloads.

```
Lambda functions → RDS Proxy → RDS Instance
(thousands of connections)  (pool of ~100 connections)
```

```bash
aws rds create-db-proxy \
  --db-proxy-name prod-mysql-proxy \
  --engine-family MYSQL \
  --auth '[{
    "AuthScheme": "SECRETS",
    "SecretArn": "arn:aws:secretsmanager:us-east-1:123456789:secret:prod/mysql",
    "IAMAuth": "REQUIRED"
  }]' \
  --role-arn arn:aws:iam::123456789:role/rds-proxy-role \
  --vpc-subnet-ids subnet-private-aaa subnet-private-bbb \
  --vpc-security-group-ids sg-proxy-12345678 \
  --require-tls
```

---

## Amazon Aurora

Aurora is AWS's cloud-native relational database — MySQL and PostgreSQL compatible, up to 5x faster than MySQL, 3x faster than PostgreSQL.

### Aurora Architecture

```
Aurora Cluster
├── Writer Instance (primary)
│   └── Reads + Writes
├── Reader Instance 1 (replica)
│   └── Reads only
├── Reader Instance 2 (replica)
│   └── Reads only
└── Shared Cluster Volume (6 copies across 3 AZs)
    ├── AZ-a: 2 copies
    ├── AZ-b: 2 copies
    └── AZ-c: 2 copies
```

**Key difference from RDS**: Storage is separate from compute. All instances share the same storage volume. Failover is faster (~30s vs 1-2min for RDS Multi-AZ).

### Aurora vs RDS

| Feature | Aurora | RDS Multi-AZ |
|---------|--------|-------------|
| Storage | Auto-scales to 128TB | Manual provisioning |
| Replicas | Up to 15 | Up to 5 |
| Failover | ~30 seconds | 1-2 minutes |
| Replication | Shared storage (instant) | Async (replicas) |
| Cost | ~20% more than RDS | Standard |
| Serverless | ✅ Aurora Serverless v2 | ❌ |

### Aurora Serverless v2

```bash
# Create Aurora Serverless v2 cluster
aws rds create-db-cluster \
  --db-cluster-identifier prod-aurora-serverless \
  --engine aurora-postgresql \
  --engine-version 15.4 \
  --master-username admin \
  --manage-master-user-password \
  --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=128 \
  --db-subnet-group-name prod-db-subnet-group \
  --vpc-security-group-ids sg-db-12345678 \
  --storage-encrypted \
  --deletion-protection

# Add serverless writer instance
aws rds create-db-instance \
  --db-instance-identifier prod-aurora-serverless-writer \
  --db-cluster-identifier prod-aurora-serverless \
  --db-instance-class db.serverless \
  --engine aurora-postgresql
```

### Aurora Global Database

```bash
# Create global database (primary region)
aws rds create-global-cluster \
  --global-cluster-identifier my-global-db \
  --source-db-cluster-identifier arn:aws:rds:us-east-1:123456789:cluster:prod-aurora

# Add secondary region
aws rds create-db-cluster \
  --db-cluster-identifier prod-aurora-eu \
  --global-cluster-identifier my-global-db \
  --engine aurora-postgresql \
  --region eu-west-1 \
  --db-subnet-group-name prod-db-subnet-group-eu
```

**RPO**: ~1 second. **RTO**: < 1 minute (managed failover).

---

## Parameter Groups & Option Groups

```bash
# Create custom parameter group
aws rds create-db-parameter-group \
  --db-parameter-group-name prod-mysql-params \
  --db-parameter-group-family mysql8.0 \
  --description "Production MySQL parameters"

# Tune parameters
aws rds modify-db-parameter-group \
  --db-parameter-group-name prod-mysql-params \
  --parameters \
    ParameterName=innodb_buffer_pool_size,ParameterValue={DBInstanceClassMemory*3/4},ApplyMethod=pending-reboot \
    ParameterName=max_connections,ParameterValue=1000,ApplyMethod=immediate \
    ParameterName=slow_query_log,ParameterValue=1,ApplyMethod=immediate \
    ParameterName=long_query_time,ParameterValue=2,ApplyMethod=immediate
```

---

## CloudFormation Template

```yaml
Resources:
  DBSubnetGroup:
    Type: AWS::RDS::DBSubnetGroup
    Properties:
      DBSubnetGroupDescription: Production DB subnet group
      SubnetIds:
        - !Ref PrivateSubnetA
        - !Ref PrivateSubnetB

  DBSecret:
    Type: AWS::SecretsManager::Secret
    Properties:
      Name: prod/mysql/credentials
      GenerateSecretString:
        SecretStringTemplate: '{"username": "admin"}'
        GenerateStringKey: password
        PasswordLength: 32
        ExcludeCharacters: '"@/\'

  RDSInstance:
    Type: AWS::RDS::DBInstance
    DeletionPolicy: Snapshot
    Properties:
      DBInstanceIdentifier: prod-mysql
      DBInstanceClass: db.m5.large
      Engine: mysql
      EngineVersion: "8.0.35"
      MasterUsername: !Sub "{{resolve:secretsmanager:${DBSecret}:SecretString:username}}"
      MasterUserPassword: !Sub "{{resolve:secretsmanager:${DBSecret}:SecretString:password}}"
      AllocatedStorage: 100
      StorageType: gp3
      StorageEncrypted: true
      MultiAZ: true
      DBSubnetGroupName: !Ref DBSubnetGroup
      VPCSecurityGroups:
        - !Ref DBSecurityGroup
      BackupRetentionPeriod: 7
      DeletionProtection: true
      EnablePerformanceInsights: true
```

---

## Interview Q&A

### Q1: What is the difference between RDS Multi-AZ and Read Replicas?
**Multi-AZ**: Synchronous replication to standby in another AZ. Purpose: high availability and failover. Standby cannot serve reads. Automatic failover in 1-2 minutes. Same region only.
**Read Replicas**: Asynchronous replication. Purpose: read scaling and reporting. Can serve read traffic. Can be promoted to standalone. Can be cross-region. No automatic failover.

### Q2: What is Aurora and how does it differ from RDS?
Aurora is AWS's cloud-native database. Key differences: (1) Shared storage volume across all instances — no replication lag between writer and readers, (2) Storage auto-scales to 128TB, (3) Up to 15 read replicas, (4) Faster failover (~30s), (5) Aurora Serverless v2 for variable workloads, (6) Global Database for multi-region with ~1s RPO.

### Q3: How do you handle database connections from Lambda?
Lambda can create thousands of concurrent connections, exhausting the database connection pool. Solutions: (1) RDS Proxy — manages connection pooling, Lambda connects to proxy which maintains a pool to RDS, (2) Aurora Serverless — scales connections automatically, (3) Connection pooling in Lambda (reuse connections across warm invocations), (4) Reduce Lambda concurrency with reserved concurrency.

### Q4: What is RDS Performance Insights?
Performance Insights is a database performance monitoring tool. It shows database load by wait events, SQL queries, users, and hosts. The "DB Load" metric shows how many queries are running vs waiting. Use it to identify: slow queries, lock contention, CPU bottlenecks, I/O bottlenecks. Free for 7 days retention, paid for longer.

### Q5: How do you perform a zero-downtime RDS upgrade?
1. Create a read replica
2. Upgrade the read replica to the new version
3. Test the application against the replica
4. Promote the replica to primary
5. Update application connection string
6. Or: Use Aurora Blue/Green Deployments — creates a staging environment, applies changes, then switches over with minimal downtime (~1 minute).
