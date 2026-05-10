# EC2 — Real-World Use Cases

## Use Case 1: Host a Production Web Server

**Business Problem**: Deploy a Node.js API that handles 500 req/sec, needs auto-recovery on failure, and must be reachable only via HTTPS.

**Architecture**:
```
Internet → ALB (HTTPS:443) → EC2 (private subnet, port 3000)
                           → Security Group: only ALB can reach EC2
```

```bash
# Variables
REGION="us-east-1"
VPC_ID="vpc-xxxxxxxx"
SUBNET_PRIVATE="subnet-xxxxxxxx"
SG_ALB="sg-alb-xxxxxxxx"

# 1. Create security group — only allow traffic from ALB
SG_APP=$(aws ec2 create-security-group \
  --group-name "sg-app-server" \
  --description "App server — only from ALB" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

aws ec2 authorize-security-group-ingress \
  --group-id $SG_APP \
  --protocol tcp --port 3000 \
  --source-group $SG_ALB   # Only ALB can reach app

# 2. Create IAM role (SSM access — no SSH needed)
aws iam create-role \
  --role-name "ec2-app-role" \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

aws iam attach-role-policy \
  --role-name "ec2-app-role" \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

aws iam create-instance-profile --instance-profile-name "ec2-app-profile"
aws iam add-role-to-instance-profile \
  --instance-profile-name "ec2-app-profile" \
  --role-name "ec2-app-role"

# 3. Launch EC2 with user data (auto-install app)
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.medium \
  --subnet-id $SUBNET_PRIVATE \
  --security-group-ids $SG_APP \
  --iam-instance-profile Name=ec2-app-profile \
  --metadata-options HttpTokens=required \
  --user-data '#!/bin/bash
    yum update -y
    curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
    yum install -y nodejs
    npm install -g pm2
    mkdir -p /app && cd /app
    cat > server.js << EOF
    const http = require("http");
    http.createServer((req, res) => {
      res.writeHead(200);
      res.end(JSON.stringify({status:"healthy",host:require("os").hostname()}));
    }).listen(3000);
    EOF
    pm2 start server.js --name app
    pm2 startup && pm2 save' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=app-server}]' \
  --query 'Instances[0].InstanceId' --output text)

echo "Instance: $INSTANCE_ID"

# 4. Connect via SSM (no SSH key needed!)
aws ssm start-session --target $INSTANCE_ID
```

**What you learn**: IMDSv2 enforcement, SSM over SSH, security group chaining, user data bootstrapping.

---

## Use Case 2: Spot Instance Batch Processing

**Business Problem**: Process 10,000 images nightly. Cost must be < $5. Interruptions are acceptable.

**Architecture**:
```
S3 (raw images) → SQS Queue → Spot EC2 Fleet → S3 (processed)
                                    ↓ (on interruption)
                              SQS message returns to queue
```

```bash
# 1. Create SQS queue for job distribution
QUEUE_URL=$(aws sqs create-queue \
  --queue-name image-processing-jobs \
  --attributes VisibilityTimeout=300 \
  --query 'QueueUrl' --output text)

# 2. Populate queue with image paths
for i in $(seq 1 100); do
  aws sqs send-message \
    --queue-url $QUEUE_URL \
    --message-body "{\"bucket\":\"my-images\",\"key\":\"raw/image_${i}.jpg\"}"
done

# 3. Launch Spot fleet
aws ec2 request-spot-fleet \
  --spot-fleet-request-config '{
    "IamFleetRole": "arn:aws:iam::123456789:role/AmazonEC2SpotFleetRole",
    "SpotPrice": "0.05",
    "TargetCapacity": 5,
    "LaunchSpecifications": [{
      "ImageId": "ami-0c02fb55956c7d316",
      "InstanceType": "c5.large",
      "SubnetId": "subnet-xxxxxxxx",
      "UserData": "'"$(base64 -w0 << 'SCRIPT'
#!/bin/bash
# Poll SQS and process images until queue empty
while true; do
  MSG=$(aws sqs receive-message --queue-url $QUEUE_URL --max-number-of-messages 1)
  if [ -z "$MSG" ]; then break; fi
  RECEIPT=$(echo $MSG | jq -r '.Messages[0].ReceiptHandle')
  BODY=$(echo $MSG | jq -r '.Messages[0].Body')
  # Process image (your logic here)
  echo "Processing: $BODY"
  aws sqs delete-message --queue-url $QUEUE_URL --receipt-handle $RECEIPT
done
SCRIPT
)"'"
    }],
    "AllocationStrategy": "capacityOptimized"
  }'

# 4. Handle Spot interruption (2-min warning)
# In your app, poll this endpoint every 5 seconds:
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
curl -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/spot/termination-time
# If returns 200 → save state, finish current job, exit gracefully
```

**What you learn**: Spot fleet, SQS for job distribution, graceful interruption handling, capacity-optimized strategy.

---

## Use Case 3: Bastion Host (Secure SSH Jump Server)

**Business Problem**: Developers need SSH access to private EC2 instances without exposing them to the internet.

```bash
# Better alternative: AWS Systems Manager Session Manager (no bastion needed!)
# But if you must use a bastion:

# 1. Launch bastion in PUBLIC subnet
BASTION_ID=$(aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.micro \
  --subnet-id $SUBNET_PUBLIC \
  --security-group-ids $SG_BASTION \
  --key-name my-keypair \
  --associate-public-ip-address \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=bastion}]' \
  --query 'Instances[0].InstanceId' --output text)

# 2. Bastion SG: only allow SSH from your IP
MY_IP=$(curl -s https://checkip.amazonaws.com)
aws ec2 authorize-security-group-ingress \
  --group-id $SG_BASTION \
  --protocol tcp --port 22 \
  --cidr "${MY_IP}/32"

# 3. SSH via bastion to private instance
ssh -J ec2-user@<bastion-public-ip> ec2-user@<private-instance-ip>

# BETTER: Use SSM Session Manager (no bastion, no open ports)
aws ssm start-session --target $PRIVATE_INSTANCE_ID
# Or SSH over SSM tunnel:
aws ssm start-session \
  --target $PRIVATE_INSTANCE_ID \
  --document-name AWS-StartSSHSession \
  --parameters portNumber=22
```

**What you learn**: Public vs private subnets, SSH jump hosts, why SSM is better than bastions.

---

## Use Case 4: Auto Scaling Web Tier

**Business Problem**: E-commerce site gets 10x traffic on Black Friday. Need to scale from 2 to 50 instances automatically.

```bash
# 1. Create Launch Template
LT_ID=$(aws ec2 create-launch-template \
  --launch-template-name "webapp-lt" \
  --version-description "v1" \
  --launch-template-data '{
    "ImageId": "ami-0c02fb55956c7d316",
    "InstanceType": "t3.medium",
    "SecurityGroupIds": ["'$SG_APP'"],
    "IamInstanceProfile": {"Name": "ec2-app-profile"},
    "MetadataOptions": {"HttpTokens": "required"},
    "UserData": "'"$(base64 -w0 bootstrap.sh)"'"
  }' \
  --query 'LaunchTemplate.LaunchTemplateId' --output text)

# 2. Create Auto Scaling Group
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name "webapp-asg" \
  --launch-template LaunchTemplateId=$LT_ID,Version='$Latest' \
  --min-size 2 --max-size 50 --desired-capacity 2 \
  --vpc-zone-identifier "$SUBNET_A,$SUBNET_B,$SUBNET_C" \
  --target-group-arns $TG_ARN \
  --health-check-type ELB \
  --health-check-grace-period 300

# 3. Target tracking: maintain 60% CPU
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name "webapp-asg" \
  --policy-name "cpu-tracking" \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "PredefinedMetricSpecification": {"PredefinedMetricType": "ASGAverageCPUUtilization"},
    "TargetValue": 60.0,
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'

# 4. Scheduled scale-out for Black Friday (pre-warm)
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name "webapp-asg" \
  --scheduled-action-name "black-friday-scaleout" \
  --recurrence "0 6 29 11 5" \
  --min-size 20 --desired-capacity 30

# 5. Monitor scaling activity
aws autoscaling describe-scaling-activities \
  --auto-scaling-group-name "webapp-asg" \
  --max-items 10
```

**What you learn**: Launch templates, target tracking vs step scaling, scheduled scaling, health check grace period.

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Using SSH key pairs instead of SSM | Security risk (open port 22) | Use SSM Session Manager |
| Not enforcing IMDSv2 | SSRF vulnerability | `--metadata-options HttpTokens=required` |
| Stopping instead of terminating dev instances | Still paying for EBS | Terminate + use snapshots |
| Single AZ deployment | AZ failure = outage | Always span 2+ AZs |
| No health check grace period | ASG terminates healthy instances during startup | Set grace period ≥ app startup time |
| Hardcoding credentials in user data | Credential exposure | Use IAM instance profile |
