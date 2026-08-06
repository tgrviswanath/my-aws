# Project 1.4 — RDS MySQL in Private Subnet

**Stage:** 01 | **Level:** Beginner | **Est. Time:** 2–3 hours | **Cost:** ~$15/month (free tier: db.t2.micro 750 h/month)

Deploy an RDS MySQL 8.0 `db.t3.micro` instance into a private subnet with no public accessibility. A DB subnet group spans two AZs for Multi-AZ readiness. A security group limits port 3306 access to the EC2 bastion only. Connect from an EC2 instance using PyMySQL and run CRUD operations against a test database.

---

## Services Used

| Tool | Purpose | Cost |
|------|---------|------|
| RDS MySQL 8.0 (db.t3.micro) | Managed relational database in private subnet | Free tier: 750 h/month db.t2.micro; ~$15/month t3.micro after |
| VPC / Private Subnets | Network isolation — RDS has no public IP | Free |
| DB Subnet Group | Defines which subnets RDS may use (min 2 AZs) | Free |
| Security Groups | Allow port 3306 from EC2 security group only | Free |
| EC2 (bastion/app) | Connects to RDS over private IP with PyMySQL | See project 1.2 |
| Secrets Manager (optional) | Store DB password instead of plaintext in code | $0.40/secret/month |

---

## Input / Output

### Input
| Type | Description |
|------|-------------|
| VPC with private subnets | Two private subnets in different AZs (e.g. `us-east-1a`, `us-east-1b`) |
| DB subnet group | Named group referencing both private subnets |
| EC2 security group ID | Source for the RDS security group inbound rule |
| MySQL credentials | Master username `admin`, password (16+ chars, store in Secrets Manager) |
| `code/db_connect.py` | PyMySQL script that creates table, inserts rows, queries results |

### Output
| Type | Description |
|------|-------------|
| RDS endpoint | `mydb.abc123.us-east-1.rds.amazonaws.com:3306` |
| MySQL database | `labdb` with table `users` — 3 rows inserted and queried |
| PyMySQL output | `[(1, 'Alice'), (2, 'Bob'), (3, 'Carol')]` printed from EC2 |
| Automated backup | Daily snapshot retained 7 days (default) |

---

## Architecture

```
VPC (10.0.0.0/16)
  │
  ├── Public Subnet (10.0.1.0/24) — us-east-1a
  │     └── EC2 bastion / app server (project 1.2)
  │           │ TCP 3306 → private IP
  │           ▼
  ├── Private Subnet A (10.0.2.0/24) — us-east-1a
  │     └── RDS MySQL primary  ◄── (Multi-AZ standby in subnet B)
  │
  └── Private Subnet B (10.0.3.0/24) — us-east-1b
        └── RDS standby (if Multi-AZ enabled)

Security Groups:
  ec2-sg  → allows outbound TCP 3306 to rds-sg
  rds-sg  → allows inbound TCP 3306 from ec2-sg only (no 0.0.0.0/0)
```

---

## Quick Start

```cmd
REM 1. Create DB subnet group (replace subnet IDs)
aws rds create-db-subnet-group ^
    --db-subnet-group-name my-db-subnet-group ^
    --db-subnet-group-description "Private subnets for RDS" ^
    --subnet-ids subnet-AAA subnet-BBB

REM 2. Create RDS security group allowing 3306 from EC2 security group
aws ec2 create-security-group --group-name rds-sg ^
    --description "RDS MySQL access" --vpc-id vpc-XXXXX
aws ec2 authorize-security-group-ingress --group-id sg-rds123 ^
    --protocol tcp --port 3306 --source-group sg-ec2456

REM 3. Create RDS instance (no public access, private subnets)
aws rds create-db-instance ^
    --db-instance-identifier mydb ^
    --db-instance-class db.t3.micro ^
    --engine mysql ^
    --engine-version 8.0 ^
    --master-username admin ^
    --master-user-password YourPassword123! ^
    --db-name labdb ^
    --db-subnet-group-name my-db-subnet-group ^
    --vpc-security-group-ids sg-rds123 ^
    --no-publicly-accessible ^
    --backup-retention-period 7 ^
    --allocated-storage 20

REM 4. Wait for RDS to be available (~5-10 min)
aws rds wait db-instance-available --db-instance-identifier mydb

REM 5. Get the endpoint
aws rds describe-db-instances --db-instance-identifier mydb ^
    --query "DBInstances[0].Endpoint.Address" --output text

REM 6. SSH to EC2, install PyMySQL, run the test script
REM    (run on EC2 via SSH or EC2 Instance Connect)
REM    pip3 install pymysql
REM    python3 db_connect.py
```

---

## Data Flow

```
1. RDS instance launches in the primary private subnet — no public IP assigned
2. EC2 bastion in the public subnet initiates TCP connection to RDS endpoint on port 3306
3. Security group on RDS allows traffic only from ec2-sg — all other sources are silently dropped
4. PyMySQL (db_connect.py) opens a connection to the RDS endpoint using admin credentials
5. Script creates table `users`, inserts 3 rows (Alice, Bob, Carol) with auto-increment IDs
6. Script runs SELECT * — PyMySQL fetches cursor rows and prints the result set
7. RDS automated backup runs daily in the backup window — point-in-time recovery up to 7 days
8. Parameter group controls session-level MySQL settings (max_connections default 66 for t3.micro)
9. Multi-AZ (if enabled): RDS synchronously replicates to standby in subnet B — failover < 2 min
```

---

## Project Files

| File | Purpose |
|------|---------|
| `README.md` | This file — RDS setup overview |
| `GUIDE.md` | Full walkthrough: subnet group, security groups, RDS creation, PyMySQL |
| `steps.md` | Windows CMD quick-reference for RDS CLI commands |
| `steps_awsconsoleui.md` | Console UI walkthrough: RDS wizard, parameter group, connectivity test |
| `verify.md` | Checklist: RDS available, endpoint reachable from EC2, CRUD working |
| `cost_estimate.md` | Cost breakdown (free tier vs on-demand) |
| `code/db_connect.py` | PyMySQL script: connect, CREATE TABLE, INSERT, SELECT, close |
| `code/` | `create_subnet_group.sh`, parameter group JSON |
| `docs/` | RDS Multi-AZ vs Read Replica comparison, backup retention notes |

---

## Lessons Learned

- RDS in a private subnet with `--no-publicly-accessible` has no public IP — the only way to connect is from inside the VPC (EC2, Lambda in the same VPC, or VPN/Direct Connect); this is best practice
- DB subnet group requires **at least 2 subnets in different AZs** — even if you don't enable Multi-AZ, RDS needs the group to span 2 AZs for the future option; creation fails with only one AZ
- Parameter group controls MySQL engine settings like `max_connections`, `slow_query_log`, and `long_query_time` — the default parameter group cannot be modified; create a custom one and attach it
- Automated backups are enabled by default with 7-day retention — setting `--backup-retention-period 0` disables them and also disables Read Replica creation
- Read replicas provide **read scaling** (separate endpoint, same data); Multi-AZ provides **high availability** (synchronous standby, automatic failover) — they are different features and can be used together
- `db.t3.micro` has `max_connections` of ~66 (calculated from memory: 1 GB × 0.75 / 12 MB per connection) — for a dev lab this is fine, but a production app needs a larger instance class or connection pooling
- PyMySQL needs a `cursor.close()` and `connection.close()` after every operation — unclosed connections accumulate against `max_connections` and cause `Too many connections` errors under load
