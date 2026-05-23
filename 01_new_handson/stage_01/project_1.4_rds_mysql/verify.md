# Verification & Validation — Project 1.4 RDS MySQL Deployment

---

## 1. AWS Console Verification

| Resource | Where to check | Expected state |
|---|---|---|
| RDS Instance | RDS → Databases | `mysql-lab-01`, Status = **Available** |
| Engine | Instance details | MySQL 8.0 |
| Instance Class | Instance details | `db.t3.micro` |
| Public Access | Connectivity tab | Publicly accessible = **No** |
| Security Group | Connectivity tab | `rds-sg` — port 3306 from EC2 SG only |
| Automated Backups | Maintenance & backups tab | Backup retention = **7 days** |
| Subnet Group | Connectivity tab | `rds-subnet-group` with 2+ AZs |

📸 Screenshot: RDS instance showing Status = Available  
📸 Screenshot: Security group showing port 3306 source = `web-server-sg` (not `0.0.0.0/0`)  
📸 Screenshot: MySQL connection from EC2 terminal  
📸 Screenshot: SQL query results showing inserted rows

---

## 2. AWS CLI Verification

```bash
# 2.1 RDS instance available
aws rds describe-db-instances \
  --db-instance-identifier mysql-lab-01 \
  --query "DBInstances[0].{Status:DBInstanceStatus,Class:DBInstanceClass,Engine:Engine,EngineVersion:EngineVersion,PublicAccess:PubliclyAccessible,Endpoint:Endpoint.Address}"
# Expected: Status=available, Class=db.t3.micro, PublicAccess=false

# 2.2 Backup retention set
aws rds describe-db-instances \
  --db-instance-identifier mysql-lab-01 \
  --query "DBInstances[0].BackupRetentionPeriod"
# Expected: 7

# 2.3 Security group restricts to EC2 SG only
aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=rds-sg" \
  --query "SecurityGroups[0].IpPermissions[?FromPort==\`3306\`].{Source:UserIdGroupPairs[0].GroupId,CIDR:IpRanges}"
# Expected: Source=web-server-sg ID, CIDR=null (no CIDR-based access)

# 2.4 Manual snapshot created
aws rds describe-db-snapshots \
  --db-instance-identifier mysql-lab-01 \
  --query "DBSnapshots[*].{ID:DBSnapshotIdentifier,Status:Status,Type:SnapshotType}"
# Expected: at least 1 manual snapshot with Status=available

# 2.5 Connect from EC2 and run query
# SSH to EC2 first, then:
mysql -h YOUR_RDS_ENDPOINT -u admin -p -e "SHOW DATABASES;"
# Expected: appdb listed
```

---

## 3. Terraform State Verification

```bash
cd terraform

terraform state list
# Expected:
# aws_db_instance.mysql
# aws_db_subnet_group.rds
# aws_security_group.rds
# aws_security_group_rule.rds_from_ec2

terraform state show aws_db_instance.mysql
# Shows: engine=mysql, instance_class=db.t3.micro,
#        publicly_accessible=false, backup_retention_period=7

terraform output rds_endpoint
# Expected: mysql-lab-01.xxxx.us-east-1.rds.amazonaws.com

terraform plan
# Expected: No changes. Infrastructure is up-to-date.
```

---

## 4. Health Check — Database Operations

```bash
# SSH to EC2, then connect to RDS
ssh -i ~/Downloads/ec2-lab-key.pem ec2-user@<EC2_PUBLIC_IP>
mysql -h <RDS_ENDPOINT> -u admin -p

# Inside MySQL:
SHOW DATABASES;
# Expected: appdb listed

USE appdb;
SHOW TABLES;
# Expected: users table listed

SELECT COUNT(*) FROM users;
# Expected: 3 (alice, bob, charlie)

SELECT * FROM users;
# Expected: 3 rows with correct data

SHOW INDEX FROM users;
# Expected: idx_username index present

EXIT;
```

---

## 5. Expected Successful Outputs

**CLI — RDS instance:**
```json
{
  "Status": "available",
  "Class": "db.t3.micro",
  "Engine": "mysql",
  "EngineVersion": "8.0.x",
  "PublicAccess": false,
  "Endpoint": "mysql-lab-01.xxxx.us-east-1.rds.amazonaws.com"
}
```

**MySQL query output:**
```
+----+----------+----------------------+---------------------+
| id | username | email                | created_at          |
+----+----------+----------------------+---------------------+
|  1 | alice    | alice@example.com    | 2024-01-01 12:00:00 |
|  2 | bob      | bob@example.com      | 2024-01-01 12:00:00 |
|  3 | charlie  | charlie@example.com  | 2024-01-01 12:00:00 |
+----+----------+----------------------+---------------------+
```

**db_operations.py output:**
```
✅ Connected to RDS MySQL
✅ Table 'orders' created
✅ 5 orders inserted
Orders:
  #1  laptop    999.99  completed
  #2  mouse      29.99  pending
  ...
```

---

## 6. Verification Checklist

- [ ] RDS instance status = available
- [ ] Engine = MySQL 8.0, class = db.t3.micro
- [ ] Public access = No
- [ ] Security group: port 3306 from EC2 SG only (no `0.0.0.0/0`)
- [ ] Subnet group spans 2+ AZs
- [ ] Backup retention = 7 days
- [ ] MySQL connection from EC2 succeeds
- [ ] `appdb` database created
- [ ] `users` table with 3 rows inserted
- [ ] `idx_username` index created
- [ ] Manual snapshot created and status = available
- [ ] `terraform plan` shows no changes
- [ ] `db_operations.py` runs successfully
