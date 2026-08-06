# Project 10.5 — Full Microservices Platform
## ECS Fargate (3 Services) + API Gateway + SQS + RDS + ElastiCache + X-Ray

---

## Prerequisites Check

- [ ] AWS CLI configured: `aws sts get-caller-identity`
- [ ] Docker installed: `docker --version` (for building service images)
- [ ] IAM permissions: `ecs:*`, `apigateway:*`, `sqs:*`, `rds:*`, `elasticache:*`
- [ ] ECR repositories for each service
- [ ] VPC with private + public subnets
- [ ] Region: `us-east-1`

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"
```

---

## Decision Point 1

**Monolith vs Microservices — which architecture?**

| Factor | Monolith ✅ | Microservices ✅ |
|--------|-----------|----------------|
| **Operational simplicity** | ✅ Deploy one thing | ❌ 3+ services to manage |
| **Team autonomy** | ❌ Teams share codebase | ✅ Independent teams/deployments |
| **Scaling** | ❌ Scale entire app | ✅ Scale individual services |
| **Fault isolation** | ❌ Bug affects everything | ✅ Failures contained per service |
| **Technology choice** | ❌ One stack | ✅ Best tool per service |
| **Startup speed** | ✅ Faster to build | ❌ More initial complexity |

**Choose Microservices when:**
- Team is > 20 engineers
- Services need to scale independently (e.g., order processing spikes differently from user auth)
- Different release cadences per service
- Clear domain boundaries exist

**For this project:** Microservices ✅ — demonstrates cloud-native architecture patterns.

---

## 1. Architecture Overview

```
Internet
    │
    ▼
API Gateway (REST API)
    │
    ├── /users/* → ALB → User Service (ECS Fargate)
    │                         └── RDS PostgreSQL (users DB)
    │
    ├── /orders/* → ALB → Order Service (ECS Fargate)
    │                         ├── RDS PostgreSQL (orders DB)
    │                         ├── ElastiCache Redis (sessions/cache)
    │                         └── → SQS: order-events queue
    │
    └── /analytics/* → ALB → Analytics Service (ECS Fargate)
                               ├── Reads from SQS: order-events
                               └── Writes to S3 (aggregated data)

All services:
    ├── Secrets Manager (DB credentials)
    ├── X-Ray (distributed tracing)
    └── CloudWatch (logs, metrics)
```

---

## 2. Create ECR Repositories and Push Images

```bash
# Create ECR repos for each service
for SERVICE in user-service order-service analytics-service; do
  aws ecr create-repository \
    --repository-name "myapp/${SERVICE}" \
    --image-scanning-configuration scanOnPush=true \
    --region $REGION
done

# Login to ECR
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin \
  "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# Build and push (example for user-service)
cat > /tmp/Dockerfile.user << 'EOF'
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
EOF

docker build -t user-service -f /tmp/Dockerfile.user .
docker tag user-service:latest \
  "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/myapp/user-service:latest"
docker push "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/myapp/user-service:latest"
```

---

## 3. Create SQS Queues

```bash
# Create order-events queue with DLQ
DLQ_ARN=$(aws sqs create-queue \
  --queue-name "order-events-dlq" \
  --attributes '{
    "MessageRetentionPeriod": "604800",
    "Tags": {"Service": "analytics", "Environment": "production"}
  }' \
  --query 'QueueUrl' --output text)

DLQ_ARN_VALUE=$(aws sqs get-queue-attributes \
  --queue-url $DLQ_ARN \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' --output text)

# Main queue with dead-letter queue
ORDER_QUEUE_URL=$(aws sqs create-queue \
  --queue-name "order-events" \
  --attributes "{
    \"VisibilityTimeout\": \"300\",
    \"MessageRetentionPeriod\": \"86400\",
    \"ReceiveMessageWaitTimeSeconds\": \"20\",
    \"RedrivePolicy\": \"{\\\"deadLetterTargetArn\\\":\\\"$DLQ_ARN_VALUE\\\",\\\"maxReceiveCount\\\":\\\"3\\\"}\"
  }" \
  --query 'QueueUrl' --output text)

ORDER_QUEUE_ARN=$(aws sqs get-queue-attributes \
  --queue-url $ORDER_QUEUE_URL \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' --output text)

echo "Order Queue: $ORDER_QUEUE_URL"
```

---

## 4. Create ECS Cluster and Services

```bash
# Create ECS Cluster
aws ecs create-cluster \
  --cluster-name "myapp-microservices" \
  --capacity-providers FARGATE FARGATE_SPOT \
  --default-capacity-provider-strategy \
    capacityProvider=FARGATE,weight=1 \
    capacityProvider=FARGATE_SPOT,weight=3 \
  --settings name=containerInsights,value=enabled \
  --tags key=Project,value=microservices

# Create ECS task execution role
EXECUTION_ROLE_ARN=$(aws iam create-role \
  --role-name ecsTaskExecutionRoleCustom \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"}]}' \
  --query 'Role.Arn' --output text)

aws iam attach-role-policy \
  --role-name ecsTaskExecutionRoleCustom \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Additional: Secrets Manager access for task execution role
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRoleCustom \
  --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite

# Create CloudWatch log groups
for SERVICE in user-service order-service analytics-service; do
  aws logs create-log-group \
    --log-group-name "/ecs/myapp/${SERVICE}" \
    --retention-in-days 30
done
```

---

## 5A. Console: Deploy User Service to ECS Fargate

1. Navigate to **Amazon ECS** → **Task definitions** → **Create new task definition**
2. **Infrastructure**: Fargate
3. **Task definition family**: `user-service-task`
4. **Container**:
   - Name: `user-service`
   - Image URI: `ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/myapp/user-service:latest`
   - Port mappings: 8080 (TCP)
   - **Environment variables**:
     - `DATABASE_URL` → from Secrets Manager: `prod/myapp/user-db`
     - `AWS_XRAY_DAEMON_ADDRESS` → `xray-daemon:2000`
5. **X-Ray sidecar container** (add second container):
   - Name: `xray-daemon`
   - Image: `public.ecr.aws/xray/aws-xray-daemon:latest`
   - Port: 2000 UDP
6. **Task size**: 0.5 vCPU, 1 GB memory
7. Create task definition

**Create Service:**
1. ECS → select cluster `myapp-microservices` → **Services** tab → **Create**
2. Task definition: `user-service-task:1`
3. Service name: `user-service`
4. Replicas: 2
5. Network: VPC, private subnets, security group
6. Load balancing: ALB → target group → listener rule

---

## 5B. CLI: Register Task Definitions and Create All Services

```bash
# Register task definition for user-service
aws ecs register-task-definition \
  --family "user-service-task" \
  --requires-compatibilities FARGATE \
  --network-mode awsvpc \
  --cpu 512 \
  --memory 1024 \
  --execution-role-arn $EXECUTION_ROLE_ARN \
  --task-role-arn $EXECUTION_ROLE_ARN \
  --container-definitions "[
    {
      \"name\": \"user-service\",
      \"image\": \"${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/myapp/user-service:latest\",
      \"portMappings\": [{\"containerPort\": 8080, \"protocol\": \"tcp\"}],
      \"environment\": [
        {\"name\": \"PORT\", \"value\": \"8080\"},
        {\"name\": \"AWS_DEFAULT_REGION\", \"value\": \"${REGION}\"}
      ],
      \"secrets\": [
        {\"name\": \"DATABASE_URL\",
         \"valueFrom\": \"arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:prod/myapp/user-db\"}
      ],
      \"logConfiguration\": {
        \"logDriver\": \"awslogs\",
        \"options\": {
          \"awslogs-group\": \"/ecs/myapp/user-service\",
          \"awslogs-region\": \"${REGION}\",
          \"awslogs-stream-prefix\": \"ecs\"
        }
      }
    },
    {
      \"name\": \"xray-daemon\",
      \"image\": \"public.ecr.aws/xray/aws-xray-daemon:latest\",
      \"portMappings\": [{\"containerPort\": 2000, \"protocol\": \"udp\"}],
      \"cpu\": 32,
      \"memoryReservation\": 256
    }
  ]"

# Create user-service ECS service
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=myapp-vpc" \
  --query 'Vpcs[0].VpcId' --output text)

PRIVATE_SUBNETS=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Type,Values=private" \
  --query 'Subnets[*].SubnetId' --output text | tr '\t' ',')

SG_ID=$(aws ec2 create-security-group \
  --group-name "user-service-sg" \
  --description "User service security group" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

aws ecs create-service \
  --cluster "myapp-microservices" \
  --service-name "user-service" \
  --task-definition "user-service-task:1" \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[$PRIVATE_SUBNETS],
    securityGroups=[$SG_ID],
    assignPublicIp=DISABLED
  }" \
  --deployment-configuration "minimumHealthyPercent=50,maximumPercent=200"

# Repeat for order-service and analytics-service
# (similar pattern — add SQS env vars for order and analytics services)
echo "Services created"
```

---

## 6. Create API Gateway

```bash
# Create REST API
API_ID=$(aws apigateway create-rest-api \
  --name "myapp-api" \
  --description "Microservices API Gateway" \
  --endpoint-configuration types=REGIONAL \
  --tags '{"Project":"microservices"}' \
  --query 'id' --output text)

# Get root resource ID
ROOT_RESOURCE_ID=$(aws apigateway get-resources \
  --rest-api-id $API_ID \
  --query 'items[?path==`/`].id' \
  --output text)

# Create /users resource
USERS_RESOURCE_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $ROOT_RESOURCE_ID \
  --path-part "users" \
  --query 'id' --output text)

# Add GET /users method → ALB integration
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $USERS_RESOURCE_ID \
  --http-method GET \
  --authorization-type NONE

USER_ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names user-service-alb \
  --query 'LoadBalancers[0].DNSName' --output text)

aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $USERS_RESOURCE_ID \
  --http-method GET \
  --type HTTP_PROXY \
  --integration-http-method GET \
  --uri "http://${USER_ALB_DNS}/users"

# Deploy API
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --stage-description "Production stage"

echo "API Gateway URL: https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod"
```

---

## 7. Enable X-Ray Distributed Tracing

```bash
# X-Ray group for microservices
aws xray create-group \
  --group-name "myapp-microservices" \
  --filter-expression "service(\"myapp*\")"

# X-Ray sampling rule (trace 5% of requests)
aws xray create-sampling-rule \
  --sampling-rule '{
    "RuleName": "myapp-default",
    "ResourceARN": "*",
    "Priority": 1000,
    "FixedRate": 0.05,
    "ReservoirSize": 5,
    "ServiceName": "myapp*",
    "ServiceType": "*",
    "Host": "*",
    "HTTPMethod": "*",
    "URLPath": "*",
    "Version": 1
  }'

# Get X-Ray traces
aws xray get-trace-summaries \
  --time-range-type EventTime \
  --start-time $(date -d '1 hour ago' --utc +%s) \
  --end-time $(date --utc +%s) \
  --filter-expression "service(\"user-service\")" \
  --query 'TraceSummaries[0:5].{TraceId:Id,Duration:Duration,HasError:HasError}'
```

---

## 8. ElastiCache Redis for Order Service Cache

```bash
# Create ElastiCache subnet group
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name "myapp-redis-subnets" \
  --cache-subnet-group-description "Redis subnet group for myapp" \
  --subnet-ids $(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Type,Values=private" \
    --query 'Subnets[*].SubnetId' --output text)

# Create Redis cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id "myapp-redis" \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1 \
  --cache-subnet-group-name "myapp-redis-subnets" \
  --security-group-ids $SG_ID \
  --preferred-maintenance-window "sun:05:00-sun:06:00"

# Get Redis endpoint
REDIS_ENDPOINT=$(aws elasticache describe-cache-clusters \
  --cache-cluster-id "myapp-redis" \
  --show-cache-node-info \
  --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' \
  --output text)

echo "Redis endpoint: $REDIS_ENDPOINT"
```

---

## 9. Service Discovery with Cloud Map

```bash
# Create Cloud Map namespace for service discovery
NAMESPACE_ID=$(aws servicediscovery create-private-dns-namespace \
  --name "myapp.local" \
  --vpc $VPC_ID \
  --description "Microservices private DNS namespace" \
  --query 'OperationId' --output text)

# Services can now discover each other via:
# user-service.myapp.local
# order-service.myapp.local
# analytics-service.myapp.local
```

---

## 10. Verify Complete Microservices Platform

```bash
echo "=== Microservices Platform Verification ==="

# 1. ECS cluster healthy
aws ecs describe-clusters \
  --clusters "myapp-microservices" \
  --query 'clusters[0].{Status:status,RunningTasks:runningTasksCount}'

# 2. All services running
aws ecs list-services \
  --cluster "myapp-microservices" \
  --query 'serviceArns[]' | \
  xargs aws ecs describe-services \
  --cluster "myapp-microservices" \
  --query 'services[].{Name:serviceName,Status:status,Running:runningCount}'

# 3. SQS queue operational
aws sqs get-queue-attributes \
  --queue-url $ORDER_QUEUE_URL \
  --attribute-names ApproximateNumberOfMessages,QueueArn

# 4. API Gateway deployed
aws apigateway get-stages \
  --rest-api-id $API_ID \
  --query 'item[].{Stage:stageName,Deployed:createdDate}'

# 5. Redis available
aws elasticache describe-cache-clusters \
  --cache-cluster-id "myapp-redis" \
  --query 'CacheClusters[0].{Status:CacheClusterStatus,Type:CacheNodeType}'

# 6. X-Ray tracing data
aws xray get-service-graph \
  --start-time $(date -d '1 hour ago' --utc +%s) \
  --end-time $(date --utc +%s) \
  --query 'Services[].{Name:Name,Type:Type}'

API_URL="https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod"
curl -s "$API_URL/users" | jq . || echo "API not yet accessible"

echo "=== Platform Verification Complete ==="
```

---

## Troubleshooting

**ECS task failing to start:**
```bash
aws ecs describe-tasks \
  --cluster myapp-microservices \
  --tasks $(aws ecs list-tasks --cluster myapp-microservices \
    --query 'taskArns[0]' --output text) \
  --query 'tasks[0].{Status:lastStatus,StopCode:stopCode,StopReason:stoppedReason}'
```

**API Gateway 502 errors:**
```bash
# Check API Gateway access logs
aws logs filter-log-events \
  --log-group-name "API-Gateway-Execution-Logs_${API_ID}/prod" \
  --filter-pattern "5XX"
# Common cause: ALB not reachable from API Gateway, or ALB returning errors
```

**SQS messages not processed:**
```bash
aws sqs get-queue-attributes \
  --queue-url $ORDER_QUEUE_URL \
  --attribute-names ApproximateNumberOfMessagesNotVisible,ApproximateNumberOfMessages
# Check DLQ for failed messages
```

**Redis connection refused:**
```bash
# Verify security group allows Redis port 6379 from ECS tasks
aws ec2 describe-security-groups --group-ids $SG_ID \
  --query 'SecurityGroups[0].IpPermissions[?ToPort==`6379`]'
```

---

## Expected Outcome

- ✅ 3 ECS Fargate services running (user, order, analytics)
- ✅ API Gateway routing requests to each service via ALB
- ✅ SQS decoupling order-service from analytics-service
- ✅ ElastiCache Redis caching sessions/data for order-service
- ✅ X-Ray distributed traces showing request flow across services
- ✅ Secrets Manager providing DB credentials (no hardcoded secrets)
- ✅ CloudWatch logs aggregated per service
- ✅ ~$100-200/month platform cost

---

## Cleanup

```bash
# Delete ECS services (this stops tasks — biggest cost)
for SERVICE in user-service order-service analytics-service; do
  aws ecs update-service \
    --cluster myapp-microservices \
    --service $SERVICE \
    --desired-count 0
  aws ecs delete-service \
    --cluster myapp-microservices \
    --service $SERVICE
done

# Delete API Gateway
aws apigateway delete-rest-api --rest-api-id $API_ID

# Delete SQS queues
aws sqs delete-queue --queue-url $ORDER_QUEUE_URL
aws sqs delete-queue --queue-url $DLQ_ARN

# Delete ElastiCache
aws elasticache delete-cache-cluster --cache-cluster-id "myapp-redis"

# Delete ECS cluster
aws ecs delete-cluster --cluster myapp-microservices

# Delete CloudWatch log groups
for SERVICE in user-service order-service analytics-service; do
  aws logs delete-log-group --log-group-name "/ecs/myapp/${SERVICE}"
done

# Delete ECR repos
for SERVICE in user-service order-service analytics-service; do
  aws ecr delete-repository \
    --repository-name "myapp/${SERVICE}" \
    --force
done

echo "Microservices platform cleanup complete"
```

---

## 5. Hands-on Implementation

### 5A. AWS Console Method
Follow the steps_awsconsoleui.md guide for step-by-step console walkthrough.

**Summary:**
1. Navigate to the relevant AWS service console
2. Create required resources using the wizard
3. Configure settings per the architecture
4. Test the deployment

### 5B. AWS CLI Method
Follow the steps.md guide for complete CLI command reference.

`ash
# Set region
export AWS_DEFAULT_REGION=us-east-1

# Verify identity
aws sts get-caller-identity

# Create main resource (see steps.md for full commands)
aws ec2 describe-vpcs --output table
`

**Prerequisites Check:**
- âœ… AWS CLI configured with ws configure
- âœ… Correct region set to us-east-1
- âœ… IAM permissions verified

**Decision Point 1:** Console vs CLI implementation
| Option | Pros | For This Project |
|--------|------|-----------------|
| AWS Console | Visual, beginner-friendly | âœ… First time |
| AWS CLI | Repeatable, scriptable | âœ… Automation |

**Expected Outcome:** All resources deployed and healthy in AWS Console.

**Troubleshooting:** If deployment fails, check IAM permissions and CloudWatch Logs.
