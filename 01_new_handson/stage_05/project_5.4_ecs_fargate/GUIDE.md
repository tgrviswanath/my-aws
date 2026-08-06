# Project 5.4 — ECS Fargate: Cluster, Task Definition, Service & ALB

## Overview

Deploy a containerized application on Amazon ECS using the Fargate launch type. Set up a cluster, define a task with 0.25 vCPU and 0.5GB memory, create a service with desired count of 2 for high availability, and front it with an Application Load Balancer.

---

## Prerequisites Check

```bash
# AWS CLI version
aws --version
# Expected: aws-cli/2.x

# Verify credentials
aws sts get-caller-identity
# Note your Account ID and Region

# Set working variables
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $AWS_ACCOUNT_ID | Region: $AWS_REGION"

# Check existing VPC (need a VPC with at least 2 subnets in different AZs)
aws ec2 describe-vpcs \
  --filters "Name=isDefault,Values=true" \
  --query 'Vpcs[0].{VpcId:VpcId,CIDR:CidrBlock}' \
  --output table

# List subnets in default VPC
aws ec2 describe-subnets \
  --filters "Name=defaultForAz,Values=true" \
  --query 'Subnets[*].{SubnetId:SubnetId,AZ:AvailabilityZone}' \
  --output table
```

---

## Decision Point 1: Fargate vs EC2 Launch Type

| Factor | Fargate | EC2 Launch Type |
|--------|---------|----------------|
| Server management | ❌ None required | ✅ You manage EC2 instances |
| Cost model | Per task (vCPU + memory) | Per EC2 instance (running or not) |
| Scaling | Per-task, instant | Must provision EC2 capacity |
| Control | Less (OS, AMI fixed) | Full (choose instance type, AMI) |
| Best for | Simplicity ✅, serverless teams | Cost optimization at scale ✅, GPU workloads |
| Free tier | No free tier | EC2 t2.micro free for 750h/month |

**Decision:** Use **Fargate** — no servers to manage, pay per second of task runtime, ideal for learning and production workloads that don't require EC2 customization.

---

## 1. Create IAM Roles

```bash
# ECS Task Execution Role — allows ECS to pull images and push logs
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' 2>/dev/null || echo "Role may already exist"

# Attach the managed policy
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Verify
aws iam get-role \
  --role-name ecsTaskExecutionRole \
  --query 'Role.Arn' \
  --output text
```

---

## 2. Create the ECS Cluster

```bash
CLUSTER_NAME="my-fargate-cluster"

# Create cluster (Fargate and Fargate Spot capacity providers)
aws ecs create-cluster \
  --cluster-name $CLUSTER_NAME \
  --capacity-providers FARGATE FARGATE_SPOT \
  --default-capacity-provider-strategy \
    capacityProvider=FARGATE,weight=1 \
  --settings name=containerInsights,value=enabled \
  --region $AWS_REGION

# Verify cluster creation
aws ecs describe-clusters \
  --clusters $CLUSTER_NAME \
  --region $AWS_REGION \
  --query 'clusters[0].{Name:clusterName,Status:status,Insights:settings}' \
  --output table
```

---

## 3. Create a CloudWatch Log Group

```bash
# ECS tasks need a log group to send container logs
aws logs create-log-group \
  --log-group-name "/ecs/my-fargate-app" \
  --region $AWS_REGION

# Set retention to 7 days (avoid unbounded cost)
aws logs put-retention-policy \
  --log-group-name "/ecs/my-fargate-app" \
  --retention-in-days 7 \
  --region $AWS_REGION

echo "Log group created: /ecs/my-fargate-app"
```

---

## 4. Register a Task Definition

```bash
# Get ECR URI (assumes flask-app was pushed in project 5.1)
ECR_REPO="flask-app"
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:1.0.0"
EXECUTION_ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/ecsTaskExecutionRole"

# Register task definition
aws ecs register-task-definition \
  --family "my-fargate-app" \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu "256" \
  --memory "512" \
  --execution-role-arn $EXECUTION_ROLE_ARN \
  --container-definitions "[
    {
      \"name\": \"app\",
      \"image\": \"$ECR_URI\",
      \"portMappings\": [{
        \"containerPort\": 8080,
        \"hostPort\": 8080,
        \"protocol\": \"tcp\"
      }],
      \"essential\": true,
      \"environment\": [
        {\"name\": \"APP_VERSION\", \"value\": \"1.0.0\"}
      ],
      \"logConfiguration\": {
        \"logDriver\": \"awslogs\",
        \"options\": {
          \"awslogs-group\": \"/ecs/my-fargate-app\",
          \"awslogs-region\": \"$AWS_REGION\",
          \"awslogs-stream-prefix\": \"ecs\"
        }
      },
      \"healthCheck\": {
        \"command\": [\"CMD-SHELL\", \"curl -f http://localhost:8080/health || exit 1\"],
        \"interval\": 30,
        \"timeout\": 5,
        \"retries\": 3,
        \"startPeriod\": 15
      }
    }
  ]" \
  --region $AWS_REGION

# Verify task definition
aws ecs describe-task-definition \
  --task-definition my-fargate-app \
  --region $AWS_REGION \
  --query 'taskDefinition.{Family:family,CPU:cpu,Memory:memory,Revision:revision}' \
  --output table
```

---

## 5. Set Up Networking and Security Groups

### 5A. AWS Console: Find VPC and Subnet IDs

1. Go to VPC Console → **Subnets**
2. Note subnet IDs in at least 2 different availability zones
3. Note the VPC ID

### 5B. AWS CLI: Get Network Info

```bash
# Get default VPC
VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=isDefault,Values=true" \
  --query 'Vpcs[0].VpcId' \
  --output text \
  --region $AWS_REGION)

echo "VPC ID: $VPC_ID"

# Get 2 public subnets in different AZs
SUBNET_IDS=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=defaultForAz,Values=true" \
  --query 'Subnets[0:2].SubnetId' \
  --output text \
  --region $AWS_REGION)

SUBNET_1=$(echo $SUBNET_IDS | awk '{print $1}')
SUBNET_2=$(echo $SUBNET_IDS | awk '{print $2}')
echo "Subnet 1: $SUBNET_1"
echo "Subnet 2: $SUBNET_2"

# Create security group for ALB
ALB_SG=$(aws ec2 create-security-group \
  --group-name "my-fargate-alb-sg" \
  --description "ALB security group for Fargate app" \
  --vpc-id $VPC_ID \
  --region $AWS_REGION \
  --query 'GroupId' \
  --output text)

# Allow HTTP from anywhere to ALB
aws ec2 authorize-security-group-ingress \
  --group-id $ALB_SG \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0 \
  --region $AWS_REGION

echo "ALB Security Group: $ALB_SG"

# Create security group for ECS tasks
ECS_SG=$(aws ec2 create-security-group \
  --group-name "my-fargate-ecs-sg" \
  --description "ECS tasks security group" \
  --vpc-id $VPC_ID \
  --region $AWS_REGION \
  --query 'GroupId' \
  --output text)

# Allow traffic from ALB only
aws ec2 authorize-security-group-ingress \
  --group-id $ECS_SG \
  --protocol tcp \
  --port 8080 \
  --source-group $ALB_SG \
  --region $AWS_REGION

echo "ECS Security Group: $ECS_SG"
```

---

## 6. Create the Application Load Balancer

```bash
# Create ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name "my-fargate-alb" \
  --subnets $SUBNET_1 $SUBNET_2 \
  --security-groups $ALB_SG \
  --scheme internet-facing \
  --type application \
  --ip-address-type ipv4 \
  --region $AWS_REGION \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text)

echo "ALB ARN: $ALB_ARN"

# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB_ARN \
  --query 'LoadBalancers[0].DNSName' \
  --output text \
  --region $AWS_REGION)

echo "ALB DNS: $ALB_DNS"

# Create target group
TG_ARN=$(aws elbv2 create-target-group \
  --name "my-fargate-tg" \
  --protocol HTTP \
  --port 8080 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path "/health" \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --region $AWS_REGION \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

echo "Target Group ARN: $TG_ARN"

# Create listener (HTTP:80 → forward to target group)
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN \
  --region $AWS_REGION
```

---

## 7. Create the ECS Service

```bash
# Create service with desired count 2 (high availability across AZs)
aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name "my-fargate-service" \
  --task-definition "my-fargate-app:1" \
  --desired-count 2 \
  --launch-type FARGATE \
  --platform-version LATEST \
  --network-configuration "awsvpcConfiguration={
    subnets=[$SUBNET_1,$SUBNET_2],
    securityGroups=[$ECS_SG],
    assignPublicIp=ENABLED
  }" \
  --load-balancers "targetGroupArn=$TG_ARN,containerName=app,containerPort=8080" \
  --deployment-configuration "maximumPercent=200,minimumHealthyPercent=100" \
  --region $AWS_REGION

echo "Service created. Waiting for tasks to become RUNNING..."

# Wait for service to stabilize
aws ecs wait services-stable \
  --cluster $CLUSTER_NAME \
  --services my-fargate-service \
  --region $AWS_REGION

echo "Service is stable!"
```

---

## 8. Verify the Deployment

```bash
# Check service status
aws ecs describe-services \
  --cluster $CLUSTER_NAME \
  --services my-fargate-service \
  --region $AWS_REGION \
  --query 'services[0].{
    Status: status,
    Running: runningCount,
    Desired: desiredCount,
    Pending: pendingCount
  }' \
  --output table

# List running tasks
aws ecs list-tasks \
  --cluster $CLUSTER_NAME \
  --service-name my-fargate-service \
  --region $AWS_REGION \
  --query 'taskArns' \
  --output text

# Test via ALB
echo "Testing ALB endpoint..."
curl -s http://$ALB_DNS/health | python3 -m json.tool
curl -s http://$ALB_DNS/
```

---

## 9. View Logs

```bash
# Get log stream for first task
TASK_ARN=$(aws ecs list-tasks \
  --cluster $CLUSTER_NAME \
  --service-name my-fargate-service \
  --query 'taskArns[0]' \
  --output text \
  --region $AWS_REGION)

TASK_ID=$(echo $TASK_ARN | awk -F'/' '{print $NF}')

# View logs
aws logs get-log-events \
  --log-group-name "/ecs/my-fargate-app" \
  --log-stream-name "ecs/app/$TASK_ID" \
  --region $AWS_REGION \
  --limit 20 \
  --query 'events[*].message' \
  --output text
```

---

## 10. Cleanup

```bash
# Scale down service (stop all tasks)
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service my-fargate-service \
  --desired-count 0 \
  --region $AWS_REGION

# Wait for tasks to stop
sleep 30

# Delete service
aws ecs delete-service \
  --cluster $CLUSTER_NAME \
  --service my-fargate-service \
  --region $AWS_REGION

# Delete ALB and target group
aws elbv2 delete-load-balancer --load-balancer-arn $ALB_ARN --region $AWS_REGION
sleep 10
aws elbv2 delete-target-group --target-group-arn $TG_ARN --region $AWS_REGION

# Delete cluster
aws ecs delete-cluster --cluster $CLUSTER_NAME --region $AWS_REGION

# Delete security groups
aws ec2 delete-security-group --group-id $ECS_SG --region $AWS_REGION
aws ec2 delete-security-group --group-id $ALB_SG --region $AWS_REGION

# Delete log group
aws logs delete-log-group --log-group-name "/ecs/my-fargate-app" --region $AWS_REGION
```

---

## Troubleshooting

**Tasks stuck in PENDING:**
```bash
# Check task stopped reason
aws ecs describe-tasks \
  --cluster $CLUSTER_NAME \
  --tasks $(aws ecs list-tasks --cluster $CLUSTER_NAME --query 'taskArns[0]' --output text) \
  --query 'tasks[0].containers[0].reason' \
  --region $AWS_REGION
```

**Service events show "unable to pull image":**
- Verify ECR image URI in task definition is correct
- Ensure `ecsTaskExecutionRole` has ECR permissions
- Ensure task subnets have internet access (NAT Gateway or public subnet with `assignPublicIp=ENABLED`)

**ALB returns 502 Bad Gateway:**
- Container health check failing — check app is listening on correct port (8080)
- Review CloudWatch logs for container startup errors
- Target group health check path must return HTTP 200

**Tasks failing health checks:**
- Add `startPeriod: 15` to container health check to give app time to start
- Verify the `/health` endpoint returns 200 (not 301 or 404)

---

## Expected Outcome

After completing this guide:

- ✅ ECS Fargate cluster running with Container Insights enabled
- ✅ Task definition with 0.25 vCPU / 0.5GB memory registered
- ✅ Service running 2 tasks spread across 2 availability zones
- ✅ ALB DNS responds with 200 on `/health`
- ✅ CloudWatch logs streaming from both tasks
- ✅ Security groups restrict ECS tasks to receive traffic only from ALB
