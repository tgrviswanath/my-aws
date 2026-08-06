# Project 5.4 — Verification Guide: ECS Fargate

---

## Section 1: Infrastructure Verification

### 1.1 ECS Cluster is ACTIVE

```bash
AWS_REGION="us-east-1"
CLUSTER_NAME="my-fargate-cluster"

aws ecs describe-clusters \
  --clusters $CLUSTER_NAME \
  --region $AWS_REGION \
  --query 'clusters[0].{Name:clusterName,Status:status,RunningTasks:runningTasksCount,ActiveServices:activeServicesCount}' \
  --output table
```

Expected: `Status = ACTIVE`, `ActiveServices = 1`, `RunningTasks = 2`

### 1.2 Task Definition Registered

```bash
aws ecs describe-task-definition \
  --task-definition my-fargate-app \
  --region $AWS_REGION \
  --query 'taskDefinition.{Family:family,CPU:cpu,Memory:memory,Revision:revision,Compat:requiresCompatibilities}' \
  --output table
```

Expected: CPU=256, Memory=512, Revision=1+, Compat=FARGATE

### 1.3 Service Running with Desired Count

```bash
aws ecs describe-services \
  --cluster $CLUSTER_NAME \
  --services my-fargate-service \
  --region $AWS_REGION \
  --query 'services[0].{Status:status,Desired:desiredCount,Running:runningCount,Pending:pendingCount,Launch:launchType}' \
  --output table
```

Expected: `Desired=2`, `Running=2`, `Pending=0`, `Launch=FARGATE`

### 1.4 ALB Active and Healthy

```bash
aws elbv2 describe-load-balancers \
  --names my-fargate-alb \
  --region $AWS_REGION \
  --query 'LoadBalancers[0].{Name:LoadBalancerName,State:State.Code,DNS:DNSName}' \
  --output table
```

Expected: `State = active`

### 1.5 Target Group Has Healthy Targets

```bash
TG_ARN=$(aws elbv2 describe-target-groups \
  --names my-fargate-tg \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text --region $AWS_REGION)

aws elbv2 describe-target-health \
  --target-group-arn $TG_ARN \
  --region $AWS_REGION \
  --query 'TargetHealthDescriptions[*].{IP:Target.Id,Port:Target.Port,Health:TargetHealth.State}' \
  --output table
```

Expected: 2 targets with `Health = healthy`

---

## Section 2: Functionality Verification

### 2.1 Application Accessible via ALB

```bash
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names my-fargate-alb \
  --query 'LoadBalancers[0].DNSName' \
  --output text --region $AWS_REGION)

# Health check
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://$ALB_DNS/health)
echo "Health check response: $HTTP_CODE"
# Expected: 200

# Root endpoint
curl -s http://$ALB_DNS/ | python3 -m json.tool
```

### 2.2 Load Balancer Distributes Traffic to Both Tasks

```bash
# Make 10 requests and check hostnames (should alternate between 2 task IPs)
for i in {1..10}; do
  curl -s http://$ALB_DNS/ | python3 -c "import sys,json; print(json.load(sys.stdin).get('hostname','unknown'))"
done
# Expected: mix of 2 different hostnames (task container IDs)
```

### 2.3 Tasks Running on Fargate

```bash
TASK_ARNS=$(aws ecs list-tasks \
  --cluster $CLUSTER_NAME \
  --service-name my-fargate-service \
  --query 'taskArns' \
  --output text --region $AWS_REGION)

aws ecs describe-tasks \
  --cluster $CLUSTER_NAME \
  --tasks $TASK_ARNS \
  --region $AWS_REGION \
  --query 'tasks[*].{TaskID:taskArn,Status:lastStatus,Platform:launchType,Health:healthStatus}' \
  --output table
```

Expected: Both tasks with `Status = RUNNING`, `Platform = FARGATE`, `Health = HEALTHY`

### 2.4 CloudWatch Logs Streaming

```bash
TASK_ID=$(aws ecs list-tasks \
  --cluster $CLUSTER_NAME \
  --service-name my-fargate-service \
  --query 'taskArns[0]' \
  --output text --region $AWS_REGION | awk -F'/' '{print $NF}')

aws logs get-log-events \
  --log-group-name "/ecs/my-fargate-app" \
  --log-stream-name "ecs/app/$TASK_ID" \
  --limit 5 \
  --query 'events[*].message' \
  --output text --region $AWS_REGION
```

Expected: Application startup messages visible

---

## Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| Tasks stuck PENDING | `runningCount = 0` after 5 minutes | Check service events: `aws ecs describe-services --query 'services[0].events[0:3]'` — usually image pull failure or resource limits |
| `CannotPullContainerError` | Task stops with pull error | Verify ECR image URI is correct; ensure `ecsTaskExecutionRole` has `ecr:*` permissions; ensure subnet has internet access |
| ALB 503 Unavailable | Browser shows Service Unavailable | Target group has no healthy targets — wait 2 minutes; check health check path returns 200 |
| Health check failing | Targets show `unhealthy` | App not listening on port 8080; security group blocking ALB→ECS on port 8080; health check path returns non-200 |
| Tasks in different AZs | Tasks both start in same AZ | Use `placementConstraints` or `spreadStrategy`; ECS Fargate normally spreads automatically with 2+ subnets in different AZs |
