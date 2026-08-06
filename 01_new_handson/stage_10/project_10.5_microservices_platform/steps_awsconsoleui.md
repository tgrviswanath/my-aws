# Project 10.5 — Full Microservices Platform: Console UI Steps
## Visual Walkthrough for AWS Management Console

---

## Prerequisites Check

- [ ] Docker images built and pushed to ECR (or use public test images)
- [ ] VPC with private and public subnets in at least 2 AZs
- [ ] IAM permissions: `ecs:*`, `apigateway:*`, `sqs:*`, `elasticache:*`
- [ ] Region: **US East (N. Virginia) us-east-1**
- [ ] ALB created in public subnets for each service

---

## Step 1 — Create ECS Cluster

1. Navigate to **Amazon ECS** in the console
2. Click **Clusters** → **Create cluster**
3. **Cluster name**: `myapp-microservices`
4. **Infrastructure**:
   - ✅ **AWS Fargate (serverless)** — no servers to manage
   - Optionally: ✅ **Amazon EC2 instances** for cost savings
5. **Monitoring**:
   - ✅ **Use Container Insights** — CloudWatch monitoring
6. Click **Create**

📸 Screenshot: ECS cluster creation with Fargate and Container Insights enabled

---

## Step 2 — Create SQS Queues

1. Navigate to **Amazon SQS** → **Create queue**
2. **Step 1 — DLQ (dead-letter queue):**
   - **Type**: Standard
   - **Name**: `order-events-dlq`
   - Keep default settings
   - Click **Create queue** → Copy the ARN
3. **Step 2 — Main queue:**
   - Click **Create queue** again
   - **Name**: `order-events`
   - **Visibility timeout**: 300 seconds
   - **Message retention**: 1 day
   - Scroll to **Dead-letter queue** → Enable → paste DLQ ARN
   - **Maximum receives**: 3
4. Click **Create queue**

📸 Screenshot: SQS queue creation showing dead-letter queue configuration

---

## Step 3 — Create ElastiCache Redis

1. Navigate to **ElastiCache** → **Get Started** → **Create cluster**
2. **Cluster mode**: Disabled (single node for dev)
3. **Name**: `myapp-redis`
4. **Engine**: Redis OSS
5. **Version**: 7.x
6. **Node type**: `cache.t3.micro` (free tier eligible for 12 months)
7. **Number of replicas**: 0 (dev) or 1 (production)
8. **Subnet group**: Create new → select private subnets
9. **Security groups**: Add one that allows TCP 6379 from ECS tasks
10. Click **Create**

📸 Screenshot: ElastiCache Redis cluster creation with cache.t3.micro selected

**Decision Point: Single node vs cluster mode?**
- **Single node**: $0.017/hr, no HA, good for dev/cache
- **Cluster mode**: Multi-shard, HA, more expensive — use for production

---

## Step 4 — Create Task Definitions

For each service (user, order, analytics), create a task definition:

1. Navigate to **ECS** → **Task definitions** → **Create new task definition**
2. **Infrastructure**: AWS Fargate
3. **Task definition family**: `user-service-task`
4. **Task role**: Select or create role with Secrets Manager + SQS + S3 access
5. **Task execution role**: `ecsTaskExecutionRole`
6. **Add container — user-service:**
   - **Name**: `user-service`
   - **Image URI**: `ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/myapp/user-service:latest`
   - **Port**: 8080
   - **Log collection**: ✅ Enable, log group `/ecs/myapp/user-service`
   - **Environment variables**:
     - `PORT`: `8080`
   - **Secrets**: `DATABASE_URL` from Secrets Manager
7. **Add X-Ray sidecar** (second container):
   - **Name**: `xray-daemon`
   - **Image**: `public.ecr.aws/xray/aws-xray-daemon:latest`
   - **Port**: 2000 (UDP)
8. **Task size**: 0.5 vCPU, 1 GB memory
9. Click **Create**

Repeat for `order-service-task` and `analytics-service-task`.

📸 Screenshot: Task definition container configuration with X-Ray sidecar container

---

## Step 5 — Deploy User Service

1. Navigate to cluster `myapp-microservices` → **Services** tab
2. Click **Create**
3. **Deployment configuration**:
   - **Application type**: Service
   - **Task definition**: `user-service-task:1`
   - **Service name**: `user-service`
   - **Desired tasks**: 2
4. **Deployment options**: Rolling update
5. **Networking**:
   - VPC and subnets: **private subnets**
   - **Assign public IP**: Disabled
   - Security group: `user-service-sg` (allow 8080 from ALB)
6. **Load balancing**:
   - Load balancer: Select ALB
   - Target group: Create new → port 8080
   - Health check path: `/health`
7. Click **Create**

Repeat for `order-service` and `analytics-service`.

📸 Screenshot: ECS service creation showing 2 desired tasks and ALB load balancing

---

## Step 6 — Create API Gateway

1. Navigate to **API Gateway** → **Create API**
2. **Choose API type**: REST API → **Build**
3. **API name**: `myapp-api`
4. **Endpoint type**: Regional
5. Click **Create API**

**Add /users resource and method:**
1. Click **Actions** → **Create Resource**
   - **Resource name**: `users`
   - **Resource path**: `/users`
2. Select `/users` → **Actions** → **Create Method** → GET
3. **Integration type**: HTTP (pointing to ALB)
   - **Endpoint URL**: `http://user-service-alb.us-east-1.elb.amazonaws.com/users`
   - **Use Proxy Integration**: ✅
4. Click **Save**

Repeat for `/orders` (order service ALB) and `/analytics`.

**Deploy API:**
1. **Actions** → **Deploy API**
2. **Deployment stage**: New stage → `prod`
3. Click **Deploy**
4. Note the **Invoke URL**: `https://xxxxx.execute-api.us-east-1.amazonaws.com/prod`

📸 Screenshot: API Gateway resource tree showing /users, /orders, /analytics with methods

---

## Step 7 — Enable X-Ray Tracing

**In API Gateway:**
1. API Gateway → Stages → `prod` → **Logs/Tracing** tab
2. ✅ **Enable X-Ray Tracing**
3. Click **Save Changes**

**In ECS Task Definition:**
- X-Ray daemon sidecar is already included (Step 4)
- Tasks automatically send traces via X-Ray SDK in application code

**View traces:**
1. Navigate to **AWS X-Ray** → **Traces**
2. See trace map showing API Gateway → ECS services → RDS → Redis
3. Click any trace to see end-to-end timeline

📸 Screenshot: X-Ray service map showing all microservices connected with latency annotations

---

## Step 8 — Connect Order Service to SQS

In order-service task definition, add environment variable:
- `SQS_QUEUE_URL`: (your order-events queue URL)

The order service code publishes events to SQS:
```python
# Order service publishes event
sqs.send_message(
    QueueUrl=os.environ['SQS_QUEUE_URL'],
    MessageBody=json.dumps({
        'event': 'ORDER_CREATED',
        'order_id': order.id,
        'user_id': order.user_id
    })
)
```

Analytics service polls SQS and consumes messages.

📸 Screenshot: SQS queue showing messages in flight from order service

---

## Step 9 — Set Up Auto Scaling for Services

1. Navigate to **ECS** → cluster → service → **Update service**
2. Click **Service auto scaling** → **Edit**
3. **Auto scaling**:
   - **Minimum tasks**: 2
   - **Maximum tasks**: 20
   - **Scaling policies**: Add target tracking
     - **Metric type**: ECS service average CPU utilization
     - **Target value**: 70%
     - **Scale-out cooldown**: 60 seconds
     - **Scale-in cooldown**: 300 seconds
4. Click **Update**

📸 Screenshot: ECS service auto scaling configuration with target tracking policy

---

## Step 10 — Monitor with CloudWatch Container Insights + X-Ray

**CloudWatch Container Insights:**
1. Navigate to **CloudWatch** → **Container Insights**
2. Select **ECS Services** → `myapp-microservices`
3. View:
   - CPU/Memory per service
   - Task counts over time
   - Network I/O per service
4. Click **View application logs** → see structured service logs

**X-Ray Service Map:**
1. Navigate to **X-Ray** → **Service map**
2. See full request flow: API GW → User/Order/Analytics Services → RDS/Redis/SQS
3. Red nodes = errors, yellow = throttling, green = healthy
4. Click a node to see latency histogram and error rates

📸 Screenshot: Combined view of CloudWatch Container Insights and X-Ray service map

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| ECS tasks failing to start | ECR image not found | Verify image URI and ECR permissions on task execution role |
| Tasks starting then stopping | Application crash | Check CloudWatch logs: `/ecs/myapp/user-service` |
| API Gateway 502 | ALB returning errors | Check ALB target group health (targets should be healthy) |
| SQS messages not consumed | Analytics service down | Check ECS analytics-service status and logs |
| Redis connection refused | Wrong security group | Allow TCP 6379 from ECS task security group to Redis SG |
| X-Ray not showing traces | X-Ray daemon not running | Verify xray-daemon sidecar container is running in task |

---

## Console Navigation Quick Reference

```
AWS Console Microservices Checklist
├── ECS → Clusters → myapp-microservices
│   ├── Services tab     → user/order/analytics services
│   ├── Tasks tab        → running tasks per service
│   └── [Service] → Logs → CloudWatch log streams
├── SQS                  → order-events queue metrics
├── ElastiCache          → myapp-redis cluster status
├── API Gateway          → myapp-api → stages → prod URL
├── X-Ray → Service map  → end-to-end trace visualization
├── CloudWatch
│   ├── Container Insights → ECS service metrics
│   └── Log groups       → /ecs/myapp/* logs
└── ECR                  → Container image repositories
```
