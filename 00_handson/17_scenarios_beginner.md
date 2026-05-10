# Level 1 — Beginner Hands-On Scenarios

> **Goal**: Understand the basic cloud workflow.  
> **Prerequisites**: AWS account, AWS CLI configured, basic Linux knowledge.

---

## Scenario 1 — Host a Static Website in S3

**Skills**: S3, IAM, Static website hosting  
**Time**: 30 minutes  
**Cost**: ~$0.00 (free tier)

### What You'll Learn
- Object storage concepts
- Bucket policies and permissions
- Public vs private access
- Static website hosting

### Step-by-Step

```bash
BUCKET="my-static-website-$(date +%s)"  # Unique name
REGION="us-east-1"

# Step 1: Create S3 bucket
aws s3api create-bucket \
  --bucket $BUCKET \
  --region $REGION

echo "Bucket created: $BUCKET"

# Step 2: Create a simple HTML page
cat > index.html << 'EOF'
<!DOCTYPE html>
<html>
<head><title>My AWS Website</title></head>
<body>
  <h1>Hello from AWS S3! 🚀</h1>
  <p>This page is hosted on Amazon S3.</p>
  <p>Bucket: BUCKET_NAME</p>
</body>
</html>
EOF

# Replace placeholder
sed -i "s/BUCKET_NAME/$BUCKET/" index.html

cat > error.html << 'EOF'
<!DOCTYPE html>
<html><body><h1>404 - Page Not Found</h1></body></html>
EOF

# Step 3: Enable static website hosting
aws s3api put-bucket-website \
  --bucket $BUCKET \
  --website-configuration '{
    "IndexDocument": {"Suffix": "index.html"},
    "ErrorDocument": {"Key": "error.html"}
  }'

# Step 4: Allow public read access
aws s3api put-public-access-block \
  --bucket $BUCKET \
  --public-access-block-configuration \
    BlockPublicAcls=false,IgnorePublicAcls=false,\
    BlockPublicPolicy=false,RestrictPublicBuckets=false

aws s3api put-bucket-policy \
  --bucket $BUCKET \
  --policy "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Principal\": \"*\",
      \"Action\": \"s3:GetObject\",
      \"Resource\": \"arn:aws:s3:::${BUCKET}/*\"
    }]
  }"

# Step 5: Upload files
aws s3 cp index.html s3://$BUCKET/
aws s3 cp error.html s3://$BUCKET/

# Step 6: Get website URL
echo ""
echo "✅ Website URL:"
echo "http://${BUCKET}.s3-website-${REGION}.amazonaws.com"
echo ""
echo "Open this URL in your browser!"
```

### Verify
```bash
# Check bucket contents
aws s3 ls s3://$BUCKET/

# Test with curl
curl -s http://${BUCKET}.s3-website-${REGION}.amazonaws.com | head -20
```

### Cleanup
```bash
aws s3 rm s3://$BUCKET --recursive
aws s3api delete-bucket --bucket $BUCKET
```

### What You Learned
- ✅ S3 bucket creation
- ✅ Static website hosting configuration
- ✅ Bucket policies for public access
- ✅ Object upload via CLI

### Common Mistakes
| Mistake | Fix |
|---------|-----|
| 403 Forbidden | Check bucket policy and public access block settings |
| Bucket name taken | S3 bucket names are globally unique — add random suffix |
| Wrong region URL | URL format varies by region |

---

## Scenario 2 — Launch Linux Server in EC2

**Skills**: EC2, SSH, Linux basics, Security Groups  
**Time**: 45 minutes  
**Cost**: ~$0.01 (t3.micro for 1 hour)

### What You'll Learn
- Cloud servers and virtualization
- Linux administration
- Security groups as firewalls
- SSH key-based authentication

### Step-by-Step

```bash
REGION="us-east-1"
KEY_NAME="my-ec2-key"
SG_NAME="my-web-sg"

# Step 1: Create SSH key pair
aws ec2 create-key-pair \
  --key-name $KEY_NAME \
  --query 'KeyMaterial' \
  --output text > ${KEY_NAME}.pem

chmod 400 ${KEY_NAME}.pem
echo "Key pair created: ${KEY_NAME}.pem"

# Step 2: Create security group
VPC_ID=$(aws ec2 describe-vpcs \
  --filters Name=isDefault,Values=true \
  --query 'Vpcs[0].VpcId' --output text)

SG_ID=$(aws ec2 create-security-group \
  --group-name $SG_NAME \
  --description "Web server security group" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

# Allow SSH from your IP only
MY_IP=$(curl -s https://checkip.amazonaws.com)
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp --port 22 \
  --cidr "${MY_IP}/32"

# Allow HTTP from anywhere
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp --port 80 \
  --cidr "0.0.0.0/0"

echo "Security group created: $SG_ID"

# Step 3: Get latest Amazon Linux 2023 AMI
AMI_ID=$(aws ec2 describe-images \
  --owners amazon \
  --filters \
    'Name=name,Values=al2023-ami-*-x86_64' \
    'Name=state,Values=available' \
  --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
  --output text)

echo "Using AMI: $AMI_ID"

# Step 4: Launch EC2 instance with user data (auto-install Nginx)
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type t3.micro \
  --key-name $KEY_NAME \
  --security-group-ids $SG_ID \
  --user-data '#!/bin/bash
    yum update -y
    yum install -y nginx
    systemctl start nginx
    systemctl enable nginx
    echo "<h1>Hello from EC2!</h1><p>Instance: $(hostname)</p>" > /usr/share/nginx/html/index.html' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=my-web-server}]' \
  --query 'Instances[0].InstanceId' \
  --output text)

echo "Instance launched: $INSTANCE_ID"

# Step 5: Wait for instance to be running
echo "Waiting for instance to start..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

# Step 6: Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

echo ""
echo "✅ Instance is running!"
echo "Public IP: $PUBLIC_IP"
echo ""
echo "SSH command:"
echo "  ssh -i ${KEY_NAME}.pem ec2-user@${PUBLIC_IP}"
echo ""
echo "Website URL:"
echo "  http://${PUBLIC_IP}"
```

### Connect and Explore

```bash
# SSH into the server
ssh -i ${KEY_NAME}.pem ec2-user@${PUBLIC_IP}

# Once inside, explore Linux:
whoami                          # Current user
uname -a                        # OS info
df -h                           # Disk usage
free -m                         # Memory
cat /etc/os-release             # OS version
systemctl status nginx          # Nginx status
tail -f /var/log/nginx/access.log  # Live access logs

# Install something
sudo yum install -y htop
htop                            # Interactive process monitor (q to quit)

# Check Nginx config
cat /etc/nginx/nginx.conf
ls /usr/share/nginx/html/

# Modify the webpage
sudo bash -c 'echo "<h1>I modified this!</h1>" > /usr/share/nginx/html/index.html'
# Refresh browser to see change

# Exit
exit
```

### Cleanup
```bash
aws ec2 terminate-instances --instance-ids $INSTANCE_ID
aws ec2 wait instance-terminated --instance-ids $INSTANCE_ID
aws ec2 delete-security-group --group-id $SG_ID
aws ec2 delete-key-pair --key-name $KEY_NAME
rm -f ${KEY_NAME}.pem
```

### What You Learned
- ✅ EC2 instance lifecycle (launch → running → terminated)
- ✅ Key pairs for SSH authentication
- ✅ Security groups as firewalls
- ✅ User data for bootstrapping
- ✅ Linux server administration

---

## Scenario 3 — Create IAM Users & Roles

**Skills**: IAM, Security, Least Privilege  
**Time**: 30 minutes  
**Cost**: $0.00 (IAM is free)

### What You'll Learn
- Identity and access management
- Least privilege principle
- Users vs roles
- Policy attachment

### Step-by-Step

```bash
# Step 1: Create a developer group with limited permissions
aws iam create-group --group-name "Developers"

# Attach read-only policy to group
aws iam attach-group-policy \
  --group-name "Developers" \
  --policy-arn "arn:aws:iam::aws:policy/ReadOnlyAccess"

# Step 2: Create a developer user
aws iam create-user --user-name "alice"

# Add user to group
aws iam add-user-to-group \
  --user-name "alice" \
  --group-name "Developers"

# Create console password
aws iam create-login-profile \
  --user-name "alice" \
  --password "TempPass123!" \
  --password-reset-required

# Create access keys (for CLI/SDK)
aws iam create-access-key \
  --user-name "alice" \
  --query 'AccessKey.{ID:AccessKeyId,Secret:SecretAccessKey}'

# Step 3: Create a custom policy (S3 access to specific bucket only)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws iam create-policy \
  --policy-name "S3BucketAccess" \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Action\": [\"s3:GetObject\", \"s3:PutObject\", \"s3:ListBucket\"],
      \"Resource\": [
        \"arn:aws:s3:::my-dev-bucket\",
        \"arn:aws:s3:::my-dev-bucket/*\"
      ]
    }]
  }"

# Step 4: Create EC2 role (for applications running on EC2)
aws iam create-role \
  --role-name "EC2AppRole" \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach S3 access to the role
aws iam attach-role-policy \
  --role-name "EC2AppRole" \
  --policy-arn "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"

# Create instance profile (needed to attach role to EC2)
aws iam create-instance-profile \
  --instance-profile-name "EC2AppProfile"

aws iam add-role-to-instance-profile \
  --instance-profile-name "EC2AppProfile" \
  --role-name "EC2AppRole"

# Step 5: Simulate what alice can do
aws iam simulate-principal-policy \
  --policy-source-arn "arn:aws:iam::${ACCOUNT_ID}:user/alice" \
  --action-names "s3:ListAllMyBuckets" "ec2:DescribeInstances" "iam:CreateUser" \
  --query 'EvaluationResults[*].{Action:EvalActionName,Decision:EvalDecision}' \
  --output table

echo "✅ IAM setup complete!"
```

### Cleanup
```bash
aws iam remove-user-from-group --user-name alice --group-name Developers
aws iam delete-login-profile --user-name alice
aws iam list-access-keys --user-name alice --query 'AccessKeyMetadata[*].AccessKeyId' --output text | \
  xargs -I{} aws iam delete-access-key --user-name alice --access-key-id {}
aws iam detach-group-policy --group-name Developers --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess
aws iam delete-user --user-name alice
aws iam delete-group --group-name Developers
```

### What You Learned
- ✅ IAM users, groups, roles, policies
- ✅ Least privilege principle
- ✅ Difference between users (humans) and roles (services)
- ✅ Policy simulation to test permissions

---

## Scenario 4 — Create RDS MySQL Database

**Skills**: RDS, SQL, Networking  
**Time**: 30 minutes  
**Cost**: ~$0.02 (db.t3.micro for 1 hour)

### What You'll Learn
- Managed database services
- DB security (no public access)
- Connecting from EC2 to RDS
- Basic SQL operations

### Step-by-Step

```bash
REGION="us-east-1"
DB_IDENTIFIER="my-mysql-db"
DB_PASSWORD="MySecurePass123!"

# Step 1: Create DB subnet group (uses default VPC subnets)
SUBNET_IDS=$(aws ec2 describe-subnets \
  --filters Name=defaultForAz,Values=true \
  --query 'Subnets[*].SubnetId' \
  --output text | tr '\t' ' ')

aws rds create-db-subnet-group \
  --db-subnet-group-name "my-db-subnet-group" \
  --db-subnet-group-description "My DB subnet group" \
  --subnet-ids $SUBNET_IDS

# Step 2: Create security group for RDS
VPC_ID=$(aws ec2 describe-vpcs \
  --filters Name=isDefault,Values=true \
  --query 'Vpcs[0].VpcId' --output text)

SG_DB=$(aws ec2 create-security-group \
  --group-name "rds-sg" \
  --description "RDS MySQL security group" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

# Allow MySQL from your IP only
MY_IP=$(curl -s https://checkip.amazonaws.com)
aws ec2 authorize-security-group-ingress \
  --group-id $SG_DB \
  --protocol tcp --port 3306 \
  --cidr "${MY_IP}/32"

# Step 3: Create RDS MySQL instance
aws rds create-db-instance \
  --db-instance-identifier $DB_IDENTIFIER \
  --db-instance-class db.t3.micro \
  --engine mysql \
  --engine-version "8.0" \
  --master-username admin \
  --master-user-password "$DB_PASSWORD" \
  --allocated-storage 20 \
  --storage-type gp2 \
  --db-subnet-group-name "my-db-subnet-group" \
  --vpc-security-group-ids $SG_DB \
  --publicly-accessible \
  --backup-retention-period 0 \
  --no-multi-az \
  --tags Key=Name,Value=my-mysql-db

echo "Creating RDS instance... (takes ~5 minutes)"
aws rds wait db-instance-available --db-instance-identifier $DB_IDENTIFIER

# Step 4: Get endpoint
DB_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier $DB_IDENTIFIER \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

echo ""
echo "✅ RDS MySQL is ready!"
echo "Endpoint: $DB_ENDPOINT"
echo "Port: 3306"
echo "Username: admin"
```

### Connect and Practice SQL

```bash
# Install MySQL client (if not installed)
sudo apt install mysql-client -y  # Ubuntu
# or
brew install mysql-client          # macOS

# Connect to RDS
mysql -h $DB_ENDPOINT -u admin -p"$DB_PASSWORD"
```

```sql
-- Once connected, practice SQL:

-- Create database
CREATE DATABASE myapp;
USE myapp;

-- Create table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(200) UNIQUE NOT NULL,
    age INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert data
INSERT INTO users (name, email, age) VALUES
    ('Alice', 'alice@example.com', 30),
    ('Bob', 'bob@example.com', 25),
    ('Charlie', 'charlie@example.com', 35),
    ('Diana', 'diana@example.com', 28);

-- Query data
SELECT * FROM users;
SELECT name, age FROM users WHERE age > 25 ORDER BY age DESC;
SELECT COUNT(*) as total, AVG(age) as avg_age FROM users;

-- Update
UPDATE users SET age = 31 WHERE name = 'Alice';

-- Delete
DELETE FROM users WHERE name = 'Charlie';

-- Exit
EXIT;
```

### Cleanup
```bash
aws rds delete-db-instance \
  --db-instance-identifier $DB_IDENTIFIER \
  --skip-final-snapshot
aws rds wait db-instance-deleted --db-instance-identifier $DB_IDENTIFIER
aws ec2 delete-security-group --group-id $SG_DB
aws rds delete-db-subnet-group --db-subnet-group-name "my-db-subnet-group"
```

### What You Learned
- ✅ Managed database vs self-managed
- ✅ DB subnet groups and security groups
- ✅ Connecting to RDS from local machine
- ✅ Basic SQL CRUD operations

---

## Scenario 5 — Python Script Uploading Files to S3

**Skills**: Python, boto3, S3  
**Time**: 20 minutes  
**Cost**: $0.00 (free tier)

### What You'll Learn
- AWS SDK (boto3)
- Programmatic AWS access
- Automation with Python

### Step-by-Step

```bash
# Install boto3
pip install boto3

# Create a test bucket
BUCKET="python-boto3-demo-$(date +%s)"
aws s3api create-bucket --bucket $BUCKET --region us-east-1
echo "Bucket: $BUCKET"
```

```python
# s3_demo.py
import boto3
import os
import json
from pathlib import Path

# Initialize S3 client
s3 = boto3.client('s3', region_name='us-east-1')
BUCKET = 'python-boto3-demo-XXXXX'  # Replace with your bucket name

# ── 1. Upload a file ──────────────────────────────────────────────────────────
def upload_file(local_path: str, s3_key: str):
    s3.upload_file(local_path, BUCKET, s3_key)
    print(f"✅ Uploaded: {local_path} → s3://{BUCKET}/{s3_key}")

# Create test files
Path('test.txt').write_text('Hello from Python!')
Path('data.json').write_text(json.dumps({'name': 'Alice', 'age': 30}))

upload_file('test.txt', 'uploads/test.txt')
upload_file('data.json', 'uploads/data.json')

# ── 2. List bucket contents ───────────────────────────────────────────────────
def list_objects(prefix: str = ''):
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
    objects = response.get('Contents', [])
    print(f"\n📁 Objects in s3://{BUCKET}/{prefix}:")
    for obj in objects:
        size_kb = obj['Size'] / 1024
        print(f"  {obj['Key']:<40} {size_kb:.2f} KB  {obj['LastModified']}")
    return objects

list_objects('uploads/')

# ── 3. Download a file ────────────────────────────────────────────────────────
def download_file(s3_key: str, local_path: str):
    s3.download_file(BUCKET, s3_key, local_path)
    print(f"✅ Downloaded: s3://{BUCKET}/{s3_key} → {local_path}")

download_file('uploads/test.txt', 'downloaded_test.txt')
print(f"Content: {Path('downloaded_test.txt').read_text()}")

# ── 4. Generate pre-signed URL (temporary access) ────────────────────────────
def get_presigned_url(s3_key: str, expires_in: int = 3600) -> str:
    url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET, 'Key': s3_key},
        ExpiresIn=expires_in
    )
    print(f"\n🔗 Pre-signed URL (valid {expires_in}s):")
    print(f"  {url[:80]}...")
    return url

get_presigned_url('uploads/test.txt')

# ── 5. Upload with metadata ───────────────────────────────────────────────────
s3.put_object(
    Bucket=BUCKET,
    Key='uploads/with-metadata.txt',
    Body=b'File with metadata',
    ContentType='text/plain',
    Metadata={
        'author': 'alice',
        'project': 'demo',
        'version': '1.0'
    }
)

# Read metadata
response = s3.head_object(Bucket=BUCKET, Key='uploads/with-metadata.txt')
print(f"\n📋 Metadata: {response['Metadata']}")

# ── 6. Delete objects ─────────────────────────────────────────────────────────
def delete_all_objects():
    objects = list_objects()
    if objects:
        s3.delete_objects(
            Bucket=BUCKET,
            Delete={'Objects': [{'Key': obj['Key']} for obj in objects]}
        )
        print(f"✅ Deleted {len(objects)} objects")

# Uncomment to cleanup:
# delete_all_objects()

print("\n✅ All S3 operations complete!")
```

```bash
# Run the script
python s3_demo.py

# Cleanup
aws s3 rm s3://$BUCKET --recursive
aws s3api delete-bucket --bucket $BUCKET
```

### What You Learned
- ✅ boto3 client initialization
- ✅ S3 upload, download, list, delete
- ✅ Pre-signed URLs for temporary access
- ✅ Object metadata

---

## Summary — Beginner Level Complete ✅

| Scenario | Services | Key Concept |
|---------|---------|------------|
| 1 | S3 | Object storage, static hosting |
| 2 | EC2, Linux | Cloud servers, SSH, security groups |
| 3 | IAM | Users, roles, least privilege |
| 4 | RDS, SQL | Managed databases, SQL basics |
| 5 | S3, Python | AWS SDK, automation |

**Next**: Move to `18_scenarios_intermediate.md` → Build custom VPC, deploy full-stack app, Docker, ECS, Terraform.
