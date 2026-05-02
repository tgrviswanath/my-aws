# Lab 01: Launch EC2 and Configure Networking

## Objective
Launch an EC2 instance in a custom VPC with proper networking, security groups, and connect via SSM Session Manager (no SSH key needed).

## Prerequisites
- AWS CLI configured (`aws configure`)
- IAM permissions: EC2, VPC, SSM, IAM

## Estimated Time: 45 minutes
## Estimated Cost: ~$0.01 (t3.micro for 1 hour)

---

## Step 1: Create VPC and Subnets

```bash
# Set variables
REGION="us-east-1"
VPC_CIDR="10.100.0.0/16"

# Create VPC
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block $VPC_CIDR \
  --region $REGION \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=lab-vpc}]' \
  --query 'Vpc.VpcId' --output text)
echo "VPC: $VPC_ID"

# Enable DNS hostnames
aws ec2 modify-vpc-attribute \
  --vpc-id $VPC_ID \
  --enable-dns-hostnames

# Create public subnet
PUB_SUBNET=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.100.1.0/24 \
  --availability-zone ${REGION}a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=lab-public}]' \
  --query 'Subnet.SubnetId' --output text)
echo "Public Subnet: $PUB_SUBNET"

# Create private subnet
PRIV_SUBNET=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.100.11.0/24 \
  --availability-zone ${REGION}a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=lab-private}]' \
  --query 'Subnet.SubnetId' --output text)
echo "Private Subnet: $PRIV_SUBNET"
```

## Step 2: Internet Gateway and Routing

```bash
# Create and attach Internet Gateway
IGW_ID=$(aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=lab-igw}]' \
  --query 'InternetGateway.InternetGatewayId' --output text)
aws ec2 attach-internet-gateway \
  --internet-gateway-id $IGW_ID \
  --vpc-id $VPC_ID
echo "IGW: $IGW_ID"

# Create public route table
PUB_RT=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=lab-public-rt}]' \
  --query 'RouteTable.RouteTableId' --output text)

# Add internet route
aws ec2 create-route \
  --route-table-id $PUB_RT \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id $IGW_ID

# Associate with public subnet
aws ec2 associate-route-table \
  --route-table-id $PUB_RT \
  --subnet-id $PUB_SUBNET

# Enable auto-assign public IP
aws ec2 modify-subnet-attribute \
  --subnet-id $PUB_SUBNET \
  --map-public-ip-on-launch

echo "Routing configured"
```

## Step 3: Security Group

```bash
# Create security group (no SSH — using SSM)
SG_ID=$(aws ec2 create-security-group \
  --group-name lab-web-sg \
  --description "Lab web server security group" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

# Allow HTTP inbound
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

# Allow HTTPS inbound
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

echo "Security Group: $SG_ID"
```

## Step 4: IAM Role for SSM

```bash
# Create IAM role for EC2 (SSM access)
aws iam create-role \
  --role-name lab-ec2-ssm-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach SSM managed policy
aws iam attach-role-policy \
  --role-name lab-ec2-ssm-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

# Create instance profile
aws iam create-instance-profile \
  --instance-profile-name lab-ec2-ssm-profile

aws iam add-role-to-instance-profile \
  --instance-profile-name lab-ec2-ssm-profile \
  --role-name lab-ec2-ssm-role

echo "IAM role created"
sleep 10  # Wait for IAM propagation
```

## Step 5: Launch EC2 Instance

```bash
# Get latest Amazon Linux 2023 AMI
AMI_ID=$(aws ec2 describe-images \
  --owners amazon \
  --filters \
    'Name=name,Values=al2023-ami-*-x86_64' \
    'Name=state,Values=available' \
  --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
  --output text)
echo "AMI: $AMI_ID"

# User data script
USER_DATA=$(cat <<'EOF'
#!/bin/bash
yum update -y
yum install -y httpd
systemctl start httpd
systemctl enable httpd

# Get instance metadata (IMDSv2)
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/instance-id)
AZ=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/placement/availability-zone)

cat > /var/www/html/index.html <<HTML
<html>
<body>
<h1>Lab EC2 Instance</h1>
<p>Instance ID: $INSTANCE_ID</p>
<p>Availability Zone: $AZ</p>
</body>
</html>
HTML
EOF
)

# Launch instance
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type t3.micro \
  --subnet-id $PUB_SUBNET \
  --security-group-ids $SG_ID \
  --iam-instance-profile Name=lab-ec2-ssm-profile \
  --user-data "$USER_DATA" \
  --metadata-options HttpTokens=required,HttpEndpoint=enabled \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=lab-web-server}]' \
  --query 'Instances[0].InstanceId' --output text)

echo "Instance: $INSTANCE_ID"

# Wait for instance to be running
echo "Waiting for instance to start..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID
echo "Instance is running!"

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)
echo "Public IP: $PUBLIC_IP"
echo "Test: curl http://$PUBLIC_IP"
```

## Step 6: Connect via SSM Session Manager

```bash
# Wait for SSM agent to register (1-2 minutes)
echo "Waiting for SSM registration..."
sleep 60

# Connect to instance (no SSH key needed!)
aws ssm start-session --target $INSTANCE_ID

# Inside the session:
# sudo su -
# cat /var/log/cloud-init-output.log  # Check user data execution
# systemctl status httpd
# curl localhost
```

## Step 7: Verify and Test

```bash
# Check instance status
aws ec2 describe-instance-status \
  --instance-ids $INSTANCE_ID \
  --query 'InstanceStatuses[0].{System:SystemStatus.Status,Instance:InstanceStatus.Status}'

# Test web server
curl -s http://$PUBLIC_IP | grep -o '<h1>.*</h1>'

# Check SSM registration
aws ssm describe-instance-information \
  --filters Key=InstanceIds,Values=$INSTANCE_ID \
  --query 'InstanceInformationList[0].{ID:InstanceId,Status:PingStatus}'
```

## Step 8: Cleanup

```bash
# Terminate instance
aws ec2 terminate-instances --instance-ids $INSTANCE_ID
aws ec2 wait instance-terminated --instance-ids $INSTANCE_ID

# Delete security group
aws ec2 delete-security-group --group-id $SG_ID

# Delete subnets
aws ec2 delete-subnet --subnet-id $PUB_SUBNET
aws ec2 delete-subnet --subnet-id $PRIV_SUBNET

# Detach and delete IGW
aws ec2 detach-internet-gateway \
  --internet-gateway-id $IGW_ID \
  --vpc-id $VPC_ID
aws ec2 delete-internet-gateway --internet-gateway-id $IGW_ID

# Delete route table
aws ec2 delete-route-table --route-table-id $PUB_RT

# Delete VPC
aws ec2 delete-vpc --vpc-id $VPC_ID

# Clean up IAM
aws iam remove-role-from-instance-profile \
  --instance-profile-name lab-ec2-ssm-profile \
  --role-name lab-ec2-ssm-role
aws iam delete-instance-profile \
  --instance-profile-name lab-ec2-ssm-profile
aws iam detach-role-policy \
  --role-name lab-ec2-ssm-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
aws iam delete-role --role-name lab-ec2-ssm-role

echo "Cleanup complete!"
```

---

## Expected Output

```
VPC: vpc-0abc123def456789
Public Subnet: subnet-0abc123def456789
Private Subnet: subnet-0def456789abc123
IGW: igw-0abc123def456789
Security Group: sg-0abc123def456789
AMI: ami-0c02fb55956c7d316
Instance: i-0abc123def456789
Public IP: 54.123.45.67
Test: curl http://54.123.45.67
→ <h1>Lab EC2 Instance</h1>
```

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Instance not reachable | Security group missing HTTP rule | Add inbound rule port 80 |
| SSM session fails | IAM role not attached or SSM agent not running | Wait 2 min, check IAM profile |
| User data didn't run | Script error | Check /var/log/cloud-init-output.log |
| No public IP | Subnet auto-assign disabled | Enable MapPublicIpOnLaunch |
| VPC delete fails | Resources still exist | Delete all resources in order |

---

## What You Learned

✅ Create a custom VPC with public and private subnets
✅ Configure Internet Gateway and route tables
✅ Create security groups with least-privilege rules
✅ Launch EC2 with IAM instance profile
✅ Use IMDSv2 for instance metadata
✅ Connect securely via SSM (no SSH keys)
✅ Clean up all resources to avoid charges
