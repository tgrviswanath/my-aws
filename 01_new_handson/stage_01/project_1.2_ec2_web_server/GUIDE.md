# Project 1.2 — EC2 Web Server with Nginx

## 1. Overview

**Problem:** You need a server that runs custom application logic — not just static files. S3 can't execute code, handle POST requests, or run server-side processes. You need a real compute instance.

**Solution:** Amazon EC2 (Elastic Compute Cloud) gives you a virtual machine in the cloud. Running Nginx on it turns it into a web server. An Elastic IP gives it a stable public address.

**Objectives:**
- Launch an EC2 t2.micro instance (free tier eligible) with Amazon Linux 2023
- Configure a security group to allow HTTP (80), HTTPS (443), and SSH (22)
- Install and start Nginx as a web server
- Allocate and associate an Elastic IP for a stable public IP address
- Verify the web server is accessible from the internet

**Expected Result:** A public IP address serving the Nginx default page (or your custom HTML) over HTTP/HTTPS.

---

## 2. Architecture

```
Internet User (Browser)
        │
        ▼ HTTP port 80 / HTTPS port 443
┌──────────────────────────┐
│   Elastic IP Address      │  ← Static public IP, stays even if instance restarts
│   (e.g., 54.123.45.67)   │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│   Security Group          │  ← Stateful firewall
│   Inbound:                │    Port 22 (SSH) — from YOUR IP only
│     22 (SSH) — my IP      │    Port 80 (HTTP) — 0.0.0.0/0
│     80 (HTTP) — 0.0.0.0   │    Port 443 (HTTPS) — 0.0.0.0/0
│     443 (HTTPS) — 0.0.0.0 │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│   EC2 Instance (t2.micro) │  ← 1 vCPU, 1 GB RAM, free tier 750 hrs/month
│   Amazon Linux 2023        │
│   Nginx web server         │  ← Serves HTML on port 80
│   EBS 8 GB gp3 root volume │
└──────────────────────────┘
```

**Key AWS Services Used:**
| Service | Role | Free Tier |
|---------|------|-----------|
| EC2 t2.micro | Virtual machine | 750 hrs/month (12 months) |
| EBS gp3 8 GB | Root disk | 30 GB/month (12 months) |
| Elastic IP | Static public IP | Free when attached to running instance |
| Security Group | Firewall rules | Always free |
| Key Pair | SSH authentication | Always free |

---

## 3. Prerequisites

### AWS Account & Permissions
- [ ] AWS account with billing enabled
- [ ] IAM user/role with permissions: `ec2:RunInstances`, `ec2:DescribeInstances`, `ec2:AuthorizeSecurityGroupIngress`, `ec2:AllocateAddress`, `ec2:AssociateAddress`
- [ ] AWS CLI installed and configured (`aws configure`)

### Local Tools
- [ ] AWS CLI v2: `aws --version`
- [ ] SSH client (built into macOS/Linux; use PuTTY or Windows Terminal on Windows)
- [ ] Your public IP address (visit `https://whatismyip.com`)

### Verify AWS CLI is configured:
```bash
aws sts get-caller-identity
aws ec2 describe-regions --output table  # Should list EC2 regions
```

---

## 4. Folder Structure

```
project_1.2_ec2_web_server/
├── GUIDE.md                    ← This file
├── steps_awsconsoleui.md       ← Console walkthrough
├── cost_estimate.md            ← Cost breakdown
├── scripts/
│   ├── launch_ec2.sh           ← CLI launch script
│   ├── install_nginx.sh        ← User data / post-launch setup
│   └── cleanup.sh              ← Teardown script
└── config/
    ├── nginx.conf              ← Custom Nginx configuration
    └── security_group.json     ← Security group rules
```

**Sample `install_nginx.sh` (used as EC2 User Data):**
```bash
#!/bin/bash
yum update -y
yum install nginx -y
systemctl start nginx
systemctl enable nginx
echo "<h1>Hello from EC2 + Nginx!</h1><p>Instance: $(hostname)</p>" \
  > /usr/share/nginx/html/index.html
```

---

## 5. Implementation

### Decision Point 1: Amazon Linux 2023 vs Ubuntu

| Feature | Amazon Linux 2023 | Ubuntu 22.04 LTS |
|---------|------------------|-----------------|
| AWS optimization | ✅ Native AWS tooling, IMDSv2 by default | Standard Linux |
| Package manager | `dnf` / `yum` | `apt` |
| Nginx install | `sudo dnf install nginx -y` | `sudo apt install nginx -y` |
| SSH user | `ec2-user` | `ubuntu` |
| Free tier eligible | ✅ Yes | ✅ Yes |
| AWS support | ✅ AWS-maintained | Community |

**Decision:** Use **Amazon Linux 2023** for AWS-specific features and AWS documentation alignment.

---

### Prerequisites Check

```bash
# 1. Verify CLI access
aws sts get-caller-identity

# 2. Check your default VPC exists
aws ec2 describe-vpcs --filters Name=isDefault,Values=true \
  --query 'Vpcs[0].VpcId' --output text

# 3. Find latest Amazon Linux 2023 AMI
aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=al2023-ami-*-x86_64" \
            "Name=state,Values=available" \
  --query 'reverse(sort_by(Images, &CreationDate))[0].ImageId' \
  --output text

# 4. Get your public IP for SSH restriction
curl -s https://checkip.amazonaws.com
```

---

### 5A. Console Implementation

See `steps_awsconsoleui.md` for the full AWS Console walkthrough.

**High-level Console steps:**
1. EC2 → Launch Instance → Name: `web-server-01`
2. AMI: Amazon Linux 2023 (free tier eligible)
3. Instance type: t2.micro
4. Key pair: Create new → download `.pem` file
5. Network settings → Create security group → add rules: HTTP 80 (anywhere), HTTPS 443 (anywhere), SSH 22 (My IP)
6. Advanced details → User data → paste `install_nginx.sh`
7. Launch instance
8. EC2 → Elastic IPs → Allocate → Associate to instance
9. Test: `http://<elastic-ip>` in browser

---

### 5B. CLI Implementation

#### Step 1: Set Variables

```bash
REGION="us-east-1"
KEY_NAME="ec2-web-server-key"
SG_NAME="web-server-sg"
INSTANCE_NAME="web-server-01"

# Get latest Amazon Linux 2023 AMI
AMI_ID=$(aws ec2 describe-images \
  --region $REGION \
  --owners amazon \
  --filters "Name=name,Values=al2023-ami-*-x86_64" \
            "Name=state,Values=available" \
  --query 'reverse(sort_by(Images, &CreationDate))[0].ImageId' \
  --output text)

echo "AMI ID: $AMI_ID"

# Get your default VPC
VPC_ID=$(aws ec2 describe-vpcs \
  --filters Name=isDefault,Values=true \
  --query 'Vpcs[0].VpcId' --output text)

echo "VPC ID: $VPC_ID"

# Get your current public IP
MY_IP=$(curl -s https://checkip.amazonaws.com)
echo "Your IP: $MY_IP"
```

#### Step 2: Create Key Pair

```bash
aws ec2 create-key-pair \
  --key-name $KEY_NAME \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/$KEY_NAME.pem

chmod 400 ~/.ssh/$KEY_NAME.pem
echo "✅ Key pair created: ~/.ssh/$KEY_NAME.pem"
```

#### Step 3: Create Security Group

```bash
SG_ID=$(aws ec2 create-security-group \
  --group-name $SG_NAME \
  --description "Web server security group - HTTP, HTTPS, SSH" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

echo "Security Group ID: $SG_ID"

# Allow SSH from your IP only (security best practice)
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp --port 22 \
  --cidr "$MY_IP/32"

# Allow HTTP from anywhere
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp --port 80 \
  --cidr "0.0.0.0/0"

# Allow HTTPS from anywhere
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp --port 443 \
  --cidr "0.0.0.0/0"

echo "✅ Security group configured"
```

#### Step 4: Launch EC2 Instance

```bash
# User data script to install Nginx on launch
USER_DATA=$(cat << 'EOF'
#!/bin/bash
yum update -y
yum install nginx -y
systemctl start nginx
systemctl enable nginx
echo "<h1>Hello from EC2 + Nginx!</h1><p>Host: $(hostname -f)</p><p>Time: $(date)</p>" \
  > /usr/share/nginx/html/index.html
EOF
)

INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type t2.micro \
  --key-name $KEY_NAME \
  --security-group-ids $SG_ID \
  --user-data "$USER_DATA" \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
  --query 'Instances[0].InstanceId' \
  --output text)

echo "Instance ID: $INSTANCE_ID"
echo "Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID
echo "✅ Instance is running"
```

#### Step 5: Allocate and Associate Elastic IP

```bash
# Allocate an Elastic IP
ALLOCATION_ID=$(aws ec2 allocate-address \
  --domain vpc \
  --query 'AllocationId' --output text)

ELASTIC_IP=$(aws ec2 describe-addresses \
  --allocation-ids $ALLOCATION_ID \
  --query 'Addresses[0].PublicIp' --output text)

echo "Elastic IP: $ELASTIC_IP"

# Associate Elastic IP with the instance
aws ec2 associate-address \
  --instance-id $INSTANCE_ID \
  --allocation-id $ALLOCATION_ID

echo "✅ Elastic IP $ELASTIC_IP associated with $INSTANCE_ID"
```

#### Step 6: SSH into the Instance

```bash
# Wait for SSH to be available (user data may take 1-2 minutes)
sleep 30

ssh -i ~/.ssh/$KEY_NAME.pem \
    -o StrictHostKeyChecking=no \
    ec2-user@$ELASTIC_IP

# Once connected, verify Nginx
sudo systemctl status nginx
curl localhost
```

#### Step 7: Manual Nginx Setup (if not using User Data)

```bash
# If you didn't use User Data, install Nginx manually after SSH:
sudo yum update -y
sudo yum install nginx -y
sudo systemctl start nginx
sudo systemctl enable nginx
sudo systemctl status nginx
```

---

## 6. Code Deep Dive

### Security Group Rules Explained

```
Inbound rules:
┌──────────┬──────────┬───────────────┬──────────────────────────────────┐
│ Protocol │ Port     │ Source        │ Purpose                          │
├──────────┼──────────┼───────────────┼──────────────────────────────────┤
│ TCP      │ 22       │ MY_IP/32      │ SSH — restricted to your IP only │
│ TCP      │ 80       │ 0.0.0.0/0     │ HTTP — public web traffic        │
│ TCP      │ 443      │ 0.0.0.0/0     │ HTTPS — public SSL traffic       │
└──────────┴──────────┴───────────────┴──────────────────────────────────┘
```

**Why restrict SSH to your IP?** Open SSH (0.0.0.0/0) on port 22 will attract brute-force bots within minutes. Always restrict SSH to known IPs.

### Nginx Configuration (`/etc/nginx/nginx.conf` key section)

```nginx
server {
    listen       80;
    listen       [::]:80;
    server_name  _;

    root         /usr/share/nginx/html;
    index        index.html;

    # Serve static files
    location / {
        try_files $uri $uri/ =404;
    }

    # Custom error pages
    error_page 404 /404.html;
    error_page 500 502 503 504 /50x.html;
}
```

### Elastic IP vs Dynamic Public IP

| Feature | Dynamic Public IP | Elastic IP |
|---------|------------------|-----------|
| Persists across stop/start | ❌ Changes on restart | ✅ Always same |
| Cost | Free | Free while attached |
| Suitable for DNS | ❌ No | ✅ Yes |
| Maximum per account | N/A | 5 per region (default) |

---

## 7. Verification

```bash
# Check instance is running
aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].State.Name' \
  --output text
# Expected: running

# Check Elastic IP association
aws ec2 describe-addresses \
  --query 'Addresses[?InstanceId!=`null`].[PublicIp,InstanceId]' \
  --output table

# Test HTTP response
curl -I http://$ELASTIC_IP
# Expected: HTTP/1.1 200 OK

# Test from browser: http://<elastic-ip>
# Expected: Nginx welcome page or your custom HTML

# Check Nginx is running (after SSH)
ssh -i ~/.ssh/$KEY_NAME.pem ec2-user@$ELASTIC_IP \
  "sudo systemctl is-active nginx && echo Nginx is running"
```

---

## 8. Observations

### Instance Metadata Service (IMDS)
```bash
# From within the EC2 instance — retrieve instance metadata
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")

curl -s -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/instance-type
# Returns: t2.micro

curl -s -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/public-ipv4
# Returns: your Elastic IP
```

### System Resources on t2.micro
```bash
# After SSH, check resources
free -h          # 1 GB RAM
nproc            # 1 vCPU
df -h            # 8 GB disk
top              # Live resource usage
```

### Nginx Access Logs
```bash
sudo tail -f /var/log/nginx/access.log
# Shows real-time HTTP requests
```

---

## 9. Screenshots

Capture at these key steps:
1. EC2 Launch Instance page with Amazon Linux 2023 AMI selected
2. Security group configuration showing ports 22, 80, 443
3. Key pair creation confirmation dialog
4. EC2 Instances list showing instance in "Running" state
5. Elastic IPs page showing the allocated IP associated with the instance
6. Browser showing the Nginx welcome page at `http://<elastic-ip>`
7. SSH terminal session showing `systemctl status nginx` output

---

## 10. Cleanup

**Important:** Stop costs by deleting resources when done.

### Step 1: Terminate EC2 Instance

```bash
aws ec2 terminate-instances --instance-ids $INSTANCE_ID
echo "Waiting for instance to terminate..."
aws ec2 wait instance-terminated --instance-ids $INSTANCE_ID
echo "✅ Instance terminated"
```

### Step 2: Release Elastic IP

```bash
# IMPORTANT: Release BEFORE terminating (already done above) to avoid $0.005/hr charge
aws ec2 release-address --allocation-id $ALLOCATION_ID
echo "✅ Elastic IP released"
```

### Step 3: Delete Security Group

```bash
# Wait a few seconds after instance terminates
sleep 10
aws ec2 delete-security-group --group-id $SG_ID
echo "✅ Security group deleted"
```

### Step 4: Delete Key Pair

```bash
aws ec2 delete-key-pair --key-name $KEY_NAME
rm ~/.ssh/$KEY_NAME.pem
echo "✅ Key pair deleted"
```

### Verify Cleanup

```bash
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=$INSTANCE_NAME" \
  --query 'Reservations[].Instances[].State.Name' \
  --output text
# Expected: terminated

aws ec2 describe-addresses --query 'Addresses[*].PublicIp' --output text
# Expected: empty (no allocated IPs)
```

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
