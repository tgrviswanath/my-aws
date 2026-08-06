# AWS Console UI Steps — RDS MySQL Database

> **Method:** AWS Management Console (browser-based)
> **Estimated time:** 20–30 minutes setup + 5–10 minutes for instance to become available
> **Difficulty:** Beginner–Intermediate

---

## Prerequisites Check

Before opening the AWS Console, confirm:

- [ ] Logged into [AWS Console](https://console.aws.amazon.com) with RDS and EC2 permissions
- [ ] MySQL client installed locally: open a terminal and run `mysql --version`
  - macOS: `brew install mysql-client`
  - Amazon Linux 2023: `sudo dnf install mariadb105`
  - Windows: Install [MySQL Community Server](https://dev.mysql.com/downloads/)
- [ ] Python 3 + PyMySQL installed: `pip install pymysql`
- [ ] Your public IP address is known: [whatismyip.com](https://whatismyip.com)
- [ ] You have a strong password ready for the database admin user

**Important:** RDS is a regional service. Make sure you're in the correct region (check the top-right of the console) — use the same region as your other resources.

---

## Step 1: Create the RDS Security Group

Before creating the RDS instance, create a security group that controls who can connect on MySQL port 3306.

### 1.1 — Navigate to EC2 Security Groups

1. AWS Console search → **EC2**
2. Left sidebar → **Network & Security** → **Security Groups**
3. Click **Create security group**

### 1.2 — Configure the Security Group

| Field | Value |
|-------|-------|
| Security group name | `rds-mysql-sg` |
| Description | `Allow MySQL port 3306 from app layer` |
| VPC | Default VPC |

**Inbound rules:**

Click **Add rule**:
| Type | Protocol | Port | Source | Notes |
|------|----------|------|--------|-------|
| MySQL/Aurora | TCP | 3306 | My IP | Direct access for development |

> For production: Instead of "My IP", use the security group ID of your EC2 app server. This ensures only your app server can reach the database.

Click **Create security group**

📸 **Screenshot checkpoint:** Security group created with the inbound rule showing port 3306.

---

## Step 2: Create the RDS MySQL Instance

### 2.1 — Navigate to RDS

1. AWS Console search → **RDS**
2. Click **RDS** under Services
3. Click **Create database** (orange button)

### 2.2 — Choose a Database Creation Method

Select **Standard create**
(Easy create uses defaults that are harder to understand — use Standard to see all options)

### 2.3 — Engine Options

Select **MySQL**

**Engine version:** MySQL 8.0.x (latest patch version shown — use the default)

### 2.4 — Choose a Template

### Decision Point 1: DB Instance Template

| Template | Instance class | Multi-AZ | Storage | Use case |
|----------|---------------|---------|---------|---------|
| **Free tier** ✅ | db.t2.micro | No | 20 GB gp2 | Learning, dev |
| Dev/Test | db.t3.micro | Optional | 20 GB gp2 | Development |
| Production | db.r6g.large+ | Yes | 100 GB io1 | Live traffic |

**For this project:** Select **Free tier**

> **Note:** Free tier forces db.t2.micro (1 vCPU, 1 GB RAM). If db.t2.micro is unavailable in your region, select "Dev/Test" template and manually choose db.t3.micro.

📸 **Screenshot checkpoint:** Engine selection showing MySQL 8.0 and Free tier template selected.

### 2.5 — Settings

| Field | Value |
|-------|-------|
| DB instance identifier | `mydb` |
| Master username | `admin` |
| Credentials management | Self managed |
| Master password | (choose a strong password, e.g., `MyDbPass123!`) |
| Confirm password | (repeat the password) |

> ⚠️ Write down this password securely. You'll need it to connect.

### 2.6 — Instance Configuration

| Field | Value |
|-------|-------|
| DB instance class | db.t2.micro (auto-selected by Free tier) |
| Multi-AZ deployment | Do not create a standby instance |

### 2.7 — Storage

| Field | Value |
|-------|-------|
| Storage type | General Purpose SSD (gp2) |
| Allocated storage | 20 GB |
| Enable storage autoscaling | ✅ Check |
| Maximum storage threshold | 100 GB |

### 2.8 — Connectivity

| Field | Value |
|-------|-------|
| Compute resource | Don't connect to an EC2 compute resource |
| VPC | Default VPC |
| DB subnet group | default |
| Public access | **Yes** (for this learning exercise — needed to connect from your local machine) |
| VPC security group | Choose existing → select `rds-mysql-sg` |
| Availability Zone | No preference |
| Database port | 3306 |

> **Note on Public Access:** Setting "Yes" allows connecting from your IP (controlled by the security group). For production, set "No" and only connect from within the VPC.

📸 **Screenshot checkpoint:** Connectivity section showing default VPC, `rds-mysql-sg` security group selected, and Public access = Yes.

### 2.9 — Database Authentication

- **Password authentication** (selected by default — use this for now)

### 2.10 — Additional Configuration

Expand **Additional configuration**:

| Field | Value |
|-------|-------|
| Initial database name | `myappdb` |
| DB parameter group | default.mysql8.0 |
| Option group | default.mysql-8-0 |
| Enable automated backups | ✅ Check |
| Backup retention period | 7 days |
| Backup window | No preference |
| Enable Enhanced monitoring | Uncheck (costs extra) |
| Enable auto minor version upgrade | ✅ Check |
| Maintenance window | No preference |
| Enable deletion protection | Uncheck (for easy cleanup) |

### 2.11 — Create the Database

Click **Create database**

You'll see a banner: *"Creating database mydb"* and the status shows **Creating**.

📸 **Screenshot checkpoint:** RDS Databases list showing `mydb` with status "Creating".

**Wait 5–10 minutes** for the status to change to **Available**.

📸 **Screenshot checkpoint:** RDS Databases list showing `mydb` with status "Available" (green).

---

### Troubleshooting — Step 2

**Status stays "Creating" for more than 15 minutes**
- This is unusual. Check the Events tab: RDS → Events. Look for error messages.
- Rarely, a region may have issues. Check the AWS Service Health Dashboard.

**Error: "DB instance class db.t2.micro is not supported"**
- Some newer regions don't support t2 instances. Change to db.t3.micro.

**Error: "Cannot create a publicly accessible DB instance in VPC without internet gateway"**
- Your VPC doesn't have an internet gateway. Use the default VPC which comes with one.

---

## Step 3: Connect to the Database

### 3.1 — Find the Endpoint

1. Click on `mydb` in the RDS Databases list
2. Scroll to **Connectivity & security**
3. Copy the **Endpoint** (e.g., `mydb.abc123def456.us-east-1.rds.amazonaws.com`)

📸 **Screenshot checkpoint:** RDS instance detail showing the endpoint and port (3306).

### 3.2 — Connect via MySQL Client

Open your terminal:

```bash
# Replace <endpoint> with the endpoint you copied
mysql -h mydb.abc123def456.us-east-1.rds.amazonaws.com \
      -u admin \
      -p \
      myappdb
# Enter your password when prompted
```

**Inside the MySQL shell:**
```sql
-- Check you're connected
SELECT VERSION();

-- Show databases
SHOW DATABASES;

-- Create a test table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert data
INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com');

-- Query
SELECT * FROM users;

-- Exit
exit;
```

📸 **Screenshot checkpoint:** Terminal showing successful MySQL connection and `SELECT * FROM users` output.

### Decision Point 2: Connect from EC2 vs Local Machine

| Connection type | Security | Setup |
|----------------|---------|-------|
| **Local machine** | ✅ OK for dev (restrict SG to your IP) | Simple, direct |
| From EC2 (same VPC) | ✅ Best practice | Change SG to allow EC2 SG, set Public access = No |
| From Lambda (same VPC) | ✅ Serverless apps | Configure Lambda in VPC |

---

### Troubleshooting — Step 3

**Error: "Can't connect to MySQL server on '<endpoint>'"**
- Check security group inbound rule: port 3306, source = your IP
- Check Public access = Yes on the RDS instance
- Run `nmap -p 3306 <endpoint>` to test port accessibility
- Your IP may have changed — update the security group rule

**Error: "Access denied for user 'admin'"**
- Wrong password. Reset: RDS → select instance → Modify → New master password

**Error: "Unknown database 'myappdb'"**
- The initial database name wasn't set. Connect without specifying a database:
  `mysql -h <endpoint> -u admin -p` then run `CREATE DATABASE myappdb;`

---

## Step 4: Take a Manual Snapshot

Snapshots are point-in-time backups of your entire database.

### 4.1 — Create a Snapshot

1. RDS → Databases → select `mydb`
2. Click **Actions** → **Take snapshot**
3. **Snapshot name:** `mydb-manual-snapshot-01`
4. Click **Take snapshot**

**Wait 2–5 minutes** for status to change from "Creating" to "Available".

📸 **Screenshot checkpoint:** RDS Snapshots page (left sidebar → Snapshots) showing `mydb-manual-snapshot-01` with status "Available".

### 4.2 — View Automated Backups

1. Left sidebar → **Automated backups**
2. You should see `mydb` with the retention period

---

## Final Expected Outcome

After completing all 4 steps:

- [ ] RDS MySQL instance `mydb` status is "Available"
- [ ] Endpoint is visible (e.g., `mydb.abc123.us-east-1.rds.amazonaws.com`)
- [ ] Security group `rds-mysql-sg` allows port 3306 from your IP
- [ ] `mysql -h <endpoint> -u admin -p` connects successfully
- [ ] Database `myappdb` contains the `users` table with test data
- [ ] Manual snapshot exists and status is "Available"
- [ ] Automated backups enabled with 7-day retention

**Your RDS MySQL database is now:**
- Managed by AWS (no OS patching required)
- Automatically backed up daily
- Accessible from your application layer via the endpoint DNS name
- Ready for production use with Multi-AZ (paid upgrade)
