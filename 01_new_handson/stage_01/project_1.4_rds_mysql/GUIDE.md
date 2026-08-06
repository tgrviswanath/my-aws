# Project 1.4 — RDS MySQL Database

## 1. Overview

**Problem:** Running a MySQL database on an EC2 instance means you're responsible for OS patching, backups, failover, storage scaling, and database version upgrades. That's significant operational overhead for something that should just work.

**Solution:** Amazon RDS (Relational Database Service) is a managed database service. AWS handles patching, automated backups, Multi-AZ failover, and storage auto-scaling. You focus on your schema and queries.

**Objectives:**
- Create an RDS MySQL instance (db.t3.micro) in the default VPC
- Configure security groups so only your EC2 instance (or your IP) can connect on port 3306
- Connect to the database using the `mysql` command-line client
- Connect from Python using PyMySQL
- Take a manual snapshot and restore it

**Expected Result:** A running MySQL database endpoint (e.g., `mydb.abc123.us-east-1.rds.amazonaws.com`) that you can connect to from EC2 or locally, with automated daily backups and point-in-time recovery.

---

## 2. Architecture

```
Application Layer
┌─────────────────────┐
│  EC2 Instance (app)  │  ← Your application server
│  Python + PyMySQL    │
│  Security Group: app-sg
└──────────┬──────────┘
           │ port 3306 (MySQL)
           ▼
┌─────────────────────────────────────────────────────┐
│  Security Group: rds-sg                              │
│  Inbound: 3306 from app-sg only                      │
└──────────┬──────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────┐
│  Amazon RDS MySQL                                    │
│  db.t3.micro (2 vCPU, 1 GB RAM)                     │
│  Engine: MySQL 8.0                                   │
│  Storage: 20 GB gp2, auto-scaling enabled            │
│  Availability Zone: us-east-1a (Single-AZ for dev)  │
│  Automated backups: 7-day retention                  │
└─────────────────────────────────────────────────────┘
           │ (Multi-AZ option)
           ▼
┌─────────────────────┐
│  Standby instance    │  ← Multi-AZ replica (optional, for production)
│  us-east-1b          │    Automatic failover, no manual intervention
└─────────────────────┘
```

**Data Flow:**
1. App connects to RDS endpoint DNS (not IP — the DNS resolves to the correct AZ)
2. MySQL connection on port 3306 (TCP)
3. Credentials: username/password (consider AWS Secrets Manager for production)
4. For Multi-AZ: failover is automatic (~60s), DNS endpoint stays the same

---

## 3. Prerequisites

### AWS Account & Permissions
- [ ] IAM user/role with: `rds:CreateDBInstance`, `rds:DescribeDBInstances`, `ec2:CreateSecurityGroup`, `ec2:AuthorizeSecurityGroupIngress`
- [ ] AWS CLI installed and configured

### Local Tools
- [ ] AWS CLI v2
- [ ] MySQL client: `mysql --version` (install: `sudo yum install mysql` or `brew install mysql-client`)
- [ ] Python 3.x with pip: `python3 --version`
- [ ] PyMySQL: `pip install pymysql`

### Verify Prerequisites
```bash
aws sts get-caller-identity
aws rds describe-db-engine-versions --engine mysql \
  --query 'DBEngineVersions[0].EngineVersion' --output text
mysql --version 2>/dev/null || echo "mysql client not installed"
python3 -c "import pymysql; print('PyMySQL version:', pymysql.__version__)" 2>/dev/null || echo "pymysql not installed"
```

---

## 4. Folder Structure

```
project_1.4_rds_mysql/
├── GUIDE.md                      ← This file
├── steps_awsconsoleui.md         ← Console walkthrough
├── cost_estimate.md              ← Cost breakdown
├── scripts/
│   ├── create_rds.sh             ← CLI script to create RDS
│   ├── connect_mysql.sh          ← MySQL connection helper
│   └── cleanup.sh                ← Teardown script
└── python/
    ├── connect.py                ← Basic PyMySQL connection test
    ├── crud_example.py           ← CREATE, READ, UPDATE, DELETE example
    └── requirements.txt          ← pymysql dependency
```

**`requirements.txt`:**
```
pymysql==1.1.0
```

---

## 5. Implementation

### Decision Point 1: Single-AZ vs Multi-AZ

| Feature | Single-AZ | Multi-AZ |
|---------|-----------|---------|
| Cost | Low (~$12.50/month) | 2× (~$25/month) |
| Availability | ~99.95% | ~99.99% |
| Failover | Manual (restart) | Automatic (~60s) |
| Use case | ✅ Dev, learning, testing | ✅ Production |
| Maintenance window downtime | Brief downtime | None (failover) |
| Backup performance impact | Slight | None (backup from standby) |

**For this project:** Use **Single-AZ** (dev/learning setup).

---

### Prerequisites Check

```bash
# 1. Get your default VPC and subnets
VPC_ID=$(aws ec2 describe-vpcs \
  --filters Name=isDefault,Values=true \
  --query 'Vpcs[0].VpcId' --output text)
echo "Default VPC: $VPC_ID"

# 2. List availability zones
aws ec2 describe-availability-zones \
  --query 'AvailabilityZones[*].ZoneName' --output table

# 3. Check RDS free tier eligibility (db.t2.micro)
aws rds describe-orderable-db-instance-options \
  --engine mysql \
  --db-instance-class db.t2.micro \
  --query 'OrderableDBInstanceOptions[0].[DBInstanceClass,MultiAZCapable]' \
  --output text 2>/dev/null || echo "db.t2.micro not available in this region"
```

---

### 5A. Console Implementation

See `steps_awsconsoleui.md` for the full AWS Console walkthrough.

**High-level Console steps:**
1. RDS → Create database → Standard create
2. Engine: MySQL 8.0 → Template: Free tier
3. DB instance ID: `mydb` → Master username: `admin` → Set password
4. DB instance class: db.t3.micro (or db.t2.micro for free tier)
5. Storage: 20 GB gp2, enable auto-scaling
6. VPC: default → Create new security group `rds-sg`
7. Database name: `myappdb`
8. Backup retention: 7 days
9. Create database (takes ~5 minutes)
10. Copy the endpoint → connect with `mysql` client

---

### 5B. CLI Implementation

#### Step 1: Set Variables

```bash
REGION="us-east-1"
DB_INSTANCE_ID="mydb"
DB_NAME="myappdb"
DB_USER="admin"
DB_PASSWORD="MySecurePass123!"  # Change this!
DB_CLASS="db.t3.micro"

VPC_ID=$(aws ec2 describe-vpcs \
  --filters Name=isDefault,Values=true \
  --query 'Vpcs[0].VpcId' --output text)

MY_IP=$(curl -s https://checkip.amazonaws.com)
echo "VPC: $VPC_ID, Your IP: $MY_IP"
```

#### Step 2: Create RDS Security Group

```bash
RDS_SG_ID=$(aws ec2 create-security-group \
  --group-name rds-mysql-sg \
  --description "RDS MySQL - allow port 3306 from app tier" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

echo "RDS Security Group ID: $RDS_SG_ID"

# Allow MySQL from your IP (for direct connection during development)
aws ec2 authorize-security-group-ingress \
  --group-id $RDS_SG_ID \
  --protocol tcp \
  --port 3306 \
  --cidr "$MY_IP/32"

echo "✅ Security group configured — port 3306 open to $MY_IP"
```

#### Step 3: Create DB Subnet Group

```bash
# Get subnet IDs from default VPC
SUBNET_IDS=$(aws ec2 describe-subnets \
  --filters Name=vpcId,Values=$VPC_ID \
  --query 'Subnets[*].SubnetId' \
  --output text | tr '\t' ' ')

echo "Subnets: $SUBNET_IDS"

aws rds create-db-subnet-group \
  --db-subnet-group-name mydb-subnet-group \
  --db-subnet-group-description "Default VPC subnets for RDS" \
  --subnet-ids $SUBNET_IDS

echo "✅ DB subnet group created"
```

#### Step 4: Create RDS MySQL Instance

```bash
aws rds create-db-instance \
  --db-instance-identifier $DB_INSTANCE_ID \
  --db-instance-class $DB_CLASS \
  --engine mysql \
  --engine-version "8.0" \
  --master-username $DB_USER \
  --master-user-password "$DB_PASSWORD" \
  --allocated-storage 20 \
  --storage-type gp2 \
  --storage-encrypted \
  --db-name $DB_NAME \
  --vpc-security-group-ids $RDS_SG_ID \
  --db-subnet-group-name mydb-subnet-group \
  --backup-retention-period 7 \
  --no-multi-az \
  --publicly-accessible \
  --tags Key=Name,Value=$DB_INSTANCE_ID \
  --region $REGION

echo "RDS instance creation started. This takes 5–10 minutes..."
echo "Waiting for instance to be available..."
aws rds wait db-instance-available --db-instance-identifier $DB_INSTANCE_ID
echo "✅ RDS instance is available!"
```

#### Step 5: Get the Endpoint

```bash
DB_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier $DB_INSTANCE_ID \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

echo "Database endpoint: $DB_ENDPOINT"
echo "Connection string: mysql -h $DB_ENDPOINT -u $DB_USER -p"
```

#### Step 6: Connect with MySQL Client

```bash
# Connect and create a test table
mysql -h "$DB_ENDPOINT" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" << 'SQL'
-- Create a test table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert test data
INSERT INTO users (name, email) VALUES
    ('Alice Johnson', 'alice@example.com'),
    ('Bob Smith', 'bob@example.com');

-- Verify
SELECT * FROM users;
SQL

echo "✅ Connected and test data inserted"
```

#### Step 7: Connect with Python (PyMySQL)

```python
# python/connect.py
import pymysql
import os

# Connection config
config = {
    'host': 'mydb.abc123.us-east-1.rds.amazonaws.com',  # Replace with your endpoint
    'user': 'admin',
    'password': 'MySecurePass123!',  # In production: use AWS Secrets Manager
    'database': 'myappdb',
    'port': 3306,
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

connection = pymysql.connect(**config)

try:
    with connection.cursor() as cursor:
        # Read
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        for user in users:
            print(f"ID: {user['id']}, Name: {user['name']}, Email: {user['email']}")

        # Insert
        cursor.execute(
            "INSERT INTO users (name, email) VALUES (%s, %s)",
            ('Charlie Brown', 'charlie@example.com')
        )
    connection.commit()
    print("✅ Insert committed")

finally:
    connection.close()
```

```bash
# Run the Python script
python3 python/connect.py
```

#### Step 8: Take a Manual Snapshot

```bash
aws rds create-db-snapshot \
  --db-instance-identifier $DB_INSTANCE_ID \
  --db-snapshot-identifier mydb-snapshot-$(date +%Y%m%d)

echo "Snapshot creation started..."
aws rds wait db-snapshot-completed \
  --db-snapshot-identifier mydb-snapshot-$(date +%Y%m%d)
echo "✅ Snapshot complete"

# List all snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier $DB_INSTANCE_ID \
  --query 'DBSnapshots[*].[DBSnapshotIdentifier,Status,SnapshotCreateTime]' \
  --output table
```

---

## 6. Code Deep Dive

### RDS Security Group Architecture

```
EC2 instance (app-sg) → port 3306 → RDS (rds-sg)

Best practice: Do NOT allow 0.0.0.0/0 on port 3306.
Only allow traffic from:
  - Your EC2 security group (app-sg)
  - Your bastion host IP (for debugging)
  - Never from the internet
```

### Why Use Parameter Groups

```bash
# Default parameter group = MySQL defaults
# Custom parameter group = tune MySQL settings

aws rds create-db-parameter-group \
  --db-parameter-group-name mydb-params \
  --db-parameter-group-family mysql8.0 \
  --description "Custom MySQL 8.0 parameters"

# Example: Enable slow query log
aws rds modify-db-parameter-group \
  --db-parameter-group-name mydb-params \
  --parameters "ParameterName=slow_query_log,ParameterValue=1,ApplyMethod=immediate" \
               "ParameterName=long_query_time,ParameterValue=2,ApplyMethod=immediate"
```

### Connection Pooling (Production Pattern)

```python
# For production apps, use a connection pool instead of single connections
from sqlalchemy import create_engine

engine = create_engine(
    f"mysql+pymysql://admin:password@{db_endpoint}/myappdb",
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True  # Reconnect on stale connections
)
```

---

## 7. Verification

```bash
# Check RDS instance status
aws rds describe-db-instances \
  --db-instance-identifier $DB_INSTANCE_ID \
  --query 'DBInstances[0].[DBInstanceStatus,Endpoint.Address,DBInstanceClass]' \
  --output table
# Expected: available, endpoint, db.t3.micro

# Check automated backups are enabled
aws rds describe-db-instances \
  --db-instance-identifier $DB_INSTANCE_ID \
  --query 'DBInstances[0].BackupRetentionPeriod'
# Expected: 7

# List all DB instances
aws rds describe-db-instances \
  --query 'DBInstances[*].[DBInstanceIdentifier,DBInstanceStatus,DBInstanceClass,Engine]' \
  --output table

# Test connection from MySQL client
mysql -h "$DB_ENDPOINT" -u "$DB_USER" -p"$DB_PASSWORD" \
  -e "SELECT VERSION(); SHOW DATABASES;"
```

---

## 8. Observations

### RDS vs Self-Managed MySQL on EC2

| Aspect | RDS MySQL | MySQL on EC2 |
|--------|-----------|-------------|
| OS access | ❌ No SSH to DB server | ✅ Full OS access |
| Automated backups | ✅ Built-in | ❌ Manual setup |
| Read replicas | ✅ 1-click | ❌ Manual replication setup |
| Multi-AZ failover | ✅ Automatic | ❌ Manual failover |
| Patch management | ✅ AWS managed | ❌ Your responsibility |
| Cost | Higher (managed tax) | Lower (but ops overhead) |

### Monitoring RDS Performance

```bash
# Check CPU utilization in CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=$DB_INSTANCE_ID \
  --start-time $(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%SZ') \
  --period 300 \
  --statistics Average \
  --output table
```

---

## 9. Screenshots

Capture at these key steps:
1. RDS Create database page with MySQL 8.0 and Free tier template selected
2. DB instance configuration showing db.t3.micro and storage settings
3. RDS Databases list showing `mydb` with status "Available"
4. RDS instance detail page showing the endpoint URL
5. Terminal showing `mysql` client connected and `SELECT * FROM users` output
6. Terminal showing Python `connect.py` script output
7. RDS Snapshots page showing the manual snapshot with status "Available"

---

## 10. Cleanup

**Important:** RDS charges continue even when idle. Delete when done.

```bash
# 1. Delete the RDS instance (skip final snapshot for dev cleanup)
aws rds delete-db-instance \
  --db-instance-identifier $DB_INSTANCE_ID \
  --skip-final-snapshot \
  --delete-automated-backups

echo "Waiting for instance deletion (takes 5-10 minutes)..."
aws rds wait db-instance-deleted --db-instance-identifier $DB_INSTANCE_ID
echo "✅ RDS instance deleted"

# 2. Delete manual snapshots
aws rds delete-db-snapshot \
  --db-snapshot-identifier mydb-snapshot-$(date +%Y%m%d) 2>/dev/null

# 3. Delete DB subnet group
aws rds delete-db-subnet-group \
  --db-subnet-group-name mydb-subnet-group

# 4. Delete security group
aws ec2 delete-security-group --group-id $RDS_SG_ID
echo "✅ All resources cleaned up"
```

### Console Cleanup

1. RDS → Databases → select `mydb` → Actions → Delete
   - Uncheck "Create final snapshot"
   - Confirm deletion by typing `delete me`
2. RDS → Subnet groups → delete `mydb-subnet-group`
3. EC2 → Security Groups → delete `rds-mysql-sg`

---

**Prerequisites Check:**
- âœ… Required permissions: Contributor/Admin IAM role
- âœ… AWS CLI configured: ws sts get-caller-identity
- âœ… Region set: ws configure get region

**Decision Point 1:** Choose your implementation approach
| Option | Use Case | For This Project |
|--------|----------|-----------------|
| AWS Console | Visual, learning | âœ… Good for first time |
| AWS CLI | Automation, scripting | âœ… Recommended for repeatability |

### 5A. AWS Console Method
Follow the steps_awsconsoleui.md guide for detailed console walkthrough.

### 5B. AWS CLI Method
Follow the steps.md guide for complete CLI command reference.

**Expected Outcome:**
- All AWS resources created and in Running/Active/Available state
- Service responding to requests correctly
- No errors in CloudWatch Logs

**Troubleshooting:**
- Resource creation fails: verify IAM permissions with ws iam get-user
- Service unreachable: check security group inbound rules
- CLI errors: run ws sts get-caller-identity to verify authentication
