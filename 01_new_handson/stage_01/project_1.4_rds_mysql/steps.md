# Steps — Project 1.4 RDS MySQL Deployment

## Phase 1 — Console

### 1.1 Create DB Subnet Group
1. Go to **RDS** → **Subnet groups** → **Create DB subnet group**
2. Name: `rds-subnet-group`
3. VPC: default VPC
4. Add subnets from at least 2 AZs

### 1.2 Create Security Group for RDS
1. Go to **EC2** → **Security Groups** → **Create**
2. Name: `rds-sg`
3. Inbound: MySQL/Aurora port 3306, source = `web-server-sg` (only EC2 can connect)
4. No inbound from `0.0.0.0/0` — ever

### 1.3 Launch RDS Instance
1. Go to **RDS** → **Create database**
2. Engine: MySQL 8.0
3. Template: **Free tier**
4. DB instance identifier: `mysql-lab-01`
5. Master username: `admin`
6. Master password: (use a strong password — save it)
7. Instance class: `db.t3.micro`
8. Storage: 20 GB gp2
9. **Disable** Multi-AZ (free tier doesn't support it)
10. VPC: default, Subnet group: `rds-subnet-group`
11. Public access: **No**
12. Security group: `rds-sg`
13. Backup retention: 7 days
14. Create database

---

## Phase 2 — Connect from EC2

```bash
# SSH into your EC2 instance (from Project 1.2)
ssh -i ~/Downloads/ec2-lab-key.pem ec2-user@YOUR_EC2_IP

# Install MySQL client
sudo yum install -y mysql

# Connect to RDS (get endpoint from RDS console)
mysql -h YOUR_RDS_ENDPOINT -u admin -p

# Enter password when prompted
```

---

## Phase 3 — Basic SQL Operations

```sql
-- Create a database
CREATE DATABASE appdb;
USE appdb;

-- Create a table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert data
INSERT INTO users (username, email) VALUES
    ('alice', 'alice@example.com'),
    ('bob', 'bob@example.com'),
    ('charlie', 'charlie@example.com');

-- Query data
SELECT * FROM users;
SELECT username, email FROM users WHERE id > 1;
SELECT COUNT(*) FROM users;

-- Update
UPDATE users SET email = 'alice@newdomain.com' WHERE username = 'alice';

-- Create an index
CREATE INDEX idx_username ON users(username);

-- Show tables and structure
SHOW TABLES;
DESCRIBE users;
SHOW CREATE TABLE users;
```

---

## Phase 4 — Backup and Restore

```bash
# Create a manual snapshot via CLI
aws rds create-db-snapshot \
  --db-instance-identifier mysql-lab-01 \
  --db-snapshot-identifier mysql-lab-01-manual-snap-$(date +%Y%m%d)

# List snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier mysql-lab-01

# Restore from snapshot (creates a new instance)
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier mysql-lab-01-restored \
  --db-snapshot-identifier mysql-lab-01-manual-snap-YYYYMMDD
```

---

## Phase 5 — AWS CLI

```bash
# Describe RDS instance
aws rds describe-db-instances \
  --db-instance-identifier mysql-lab-01 \
  --query "DBInstances[0].{Endpoint:Endpoint.Address,Status:DBInstanceStatus,Class:DBInstanceClass}"

# Modify instance (e.g. change backup retention)
aws rds modify-db-instance \
  --db-instance-identifier mysql-lab-01 \
  --backup-retention-period 7 \
  --apply-immediately

# Stop instance when not using (saves free tier hours)
aws rds stop-db-instance --db-instance-identifier mysql-lab-01
```

---

## Phase 6 — Terraform

```bash
cd terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
terraform output rds_endpoint
```

---

## Screenshots to Take
- [ ] RDS instance running (green "Available" status)
- [ ] Security group showing port 3306 restricted to EC2 SG only
- [ ] MySQL connection from EC2 terminal
- [ ] SQL queries running successfully
- [ ] Automated backup enabled (7-day retention)
- [ ] Manual snapshot created
- [ ] `terraform apply` success output
