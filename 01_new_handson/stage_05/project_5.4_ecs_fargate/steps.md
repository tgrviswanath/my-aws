# Steps — Project 5.4 ECS Fargate Deployment

## Phase 1 — Prerequisites

```bash
# Ensure image is in ECR (from Project 5.3)
ECR_URL=$(cd ../project_5.3_ecr/terraform && terraform output -raw ecr_url)
echo "ECR: $ECR_URL"

# Verify image exists
aws ecr list-images --repository-name handson-flask-api
```

---

## Phase 2 — Deploy with Terraform

```bash
cd terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"

ALB_URL=$(terraform output -raw alb_url)
echo "App URL: $ALB_URL"
```

---

## Phase 3 — Verify Deployment

```bash
# Wait for tasks to be running (~2 minutes)
aws ecs wait services-stable \
  --cluster handson-cluster \
  --services handson-flask-api-service

# Check service status
aws ecs describe-services \
  --cluster handson-cluster \
  --services handson-flask-api-service \
  --query "services[0].{Status:status,Running:runningCount,Desired:desiredCount,Pending:pendingCount}"

# Test the app
curl $ALB_URL/health | python3 -m json.tool
curl $ALB_URL/items  | python3 -m json.tool
```

---

## Phase 4 — View Container Logs

```bash
# Get log stream names
aws logs describe-log-streams \
  --log-group-name /ecs/handson-flask-api \
  --order-by LastEventTime \
  --descending \
  --query "logStreams[0].logStreamName" \
  --output text

# Tail logs
aws logs tail /ecs/handson-flask-api --follow
```

---

## Phase 5 — Rolling Deployment (Update Image)

```bash
# Build and push a new version
cd ../../project_5.1_single_docker_app
docker build -t flask-api:2.0.0 .
docker tag flask-api:2.0.0 $ECR_URL:2.0.0
docker tag flask-api:2.0.0 $ECR_URL:latest
docker push $ECR_URL:latest
docker push $ECR_URL:2.0.0

# Force new deployment (ECS pulls latest image)
aws ecs update-service \
  --cluster handson-cluster \
  --service handson-flask-api-service \
  --force-new-deployment

# Watch rolling deployment
watch -n 5 "aws ecs describe-services \
  --cluster handson-cluster \
  --services handson-flask-api-service \
  --query 'services[0].{Running:runningCount,Pending:pendingCount,Desired:desiredCount}'"
```

---

## Phase 6 — Scale the Service

```bash
# Scale up to 4 tasks
aws ecs update-service \
  --cluster handson-cluster \
  --service handson-flask-api-service \
  --desired-count 4

# Verify load balancing (different task IDs in hostname)
for i in {1..6}; do
  curl -s $ALB_URL/info | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['hostname'])"
done
```

---

## Phase 7 — Verification & Validation

### 7.1 AWS Console Verification
1. **ECS** → **Clusters** → `handson-cluster` → confirm status = ACTIVE
2. **ECS** → **Services** → `handson-flask-api-service` → Running count = Desired count
3. **ECS** → **Tasks** → confirm tasks show RUNNING with Fargate launch type
4. **EC2** → **Load Balancers** → ALB → confirm state = active
5. **EC2** → **Target Groups** → confirm all targets = healthy
6. **CloudWatch** → **Log groups** → `/ecs/handson-flask-api` → confirm logs flowing

### 7.2 CLI Verification Commands
```bash
# Confirm cluster is active
aws ecs describe-clusters --clusters handson-cluster \
  --query "clusters[0].{Status:status,ActiveServices:activeServicesCount,RunningTasks:runningTasksCount}"
# Expected: status=ACTIVE, activeServicesCount=1, runningTasksCount>=1

# Confirm service is stable
aws ecs describe-services \
  --cluster handson-cluster \
  --services handson-flask-api-service \
  --query "services[0].{Status:status,Running:runningCount,Desired:desiredCount,Pending:pendingCount}"
# Expected: Running == Desired, Pending == 0

# Confirm tasks are using Fargate and awsvpc
TASK_ARN=$(aws ecs list-tasks --cluster handson-cluster \
  --service-name handson-flask-api-service \
  --query "taskArns[0]" --output text)
aws ecs describe-tasks --cluster handson-cluster --tasks $TASK_ARN \
  --query "tasks[0].{LaunchType:launchType,Status:lastStatus,PrivateIP:attachments[0].details[?name=='privateIPv4Address']|[0].value}"
# Expected: LaunchType=FARGATE, Status=RUNNING

# Confirm ALB target health
TG_ARN=$(aws elbv2 describe-target-groups \
  --query "TargetGroups[?contains(TargetGroupName,'handson')].TargetGroupArn" \
  --output text)
aws elbv2 describe-target-health --target-group-arn $TG_ARN \
  --query "TargetHealthDescriptions[*].{Target:Target.Id,Health:TargetHealth.State}"
# Expected: all targets = healthy
```

### 7.3 Functional Tests
```bash
ALB_URL=$(cd terraform && terraform output -raw alb_url)

# Test 1: Health endpoint
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $ALB_URL/health)
echo "Health check: $HTTP_STATUS"
# Expected: 200

# Test 2: App responds with correct data
curl -s $ALB_URL/health | python3 -m json.tool
# Expected: {"status": "ok", "hostname": "...", ...}

# Test 3: Load balancing — multiple requests hit different tasks
echo "Testing load balancing across tasks:"
for i in $(seq 1 6); do
  curl -s $ALB_URL/info | python3 -c "import sys,json; print(json.load(sys.stdin)['hostname'])"
done
# Expected: different hostnames (different task IDs)

# Test 4: Rolling deployment — push new image and verify zero downtime
# While deployment runs, keep hitting the endpoint:
for i in $(seq 1 30); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" $ALB_URL/health)
  echo "$(date +%H:%M:%S) - HTTP $STATUS"
  sleep 2
done
# Expected: all 200 (no downtime during rolling update)
```

### 7.4 Logs & Monitoring Checks
```bash
# Check CloudWatch logs for errors
aws logs filter-log-events \
  --log-group-name /ecs/handson-flask-api \
  --filter-pattern "ERROR" \
  --start-time $(date -d '10 minutes ago' +%s000) \
  --query "events[*].message"
# Expected: no ERROR events

# Confirm logs are flowing (recent events exist)
aws logs describe-log-streams \
  --log-group-name /ecs/handson-flask-api \
  --order-by LastEventTime \
  --descending \
  --query "logStreams[0].{Stream:logStreamName,LastEvent:lastEventTimestamp}"
# Expected: recent timestamp
```

### 7.5 Terraform State Verification
```bash
cd terraform
terraform state list | grep -E "ecs|alb|iam"
# Expected: cluster, service, task_definition, ALB, target_group, IAM role resources

terraform output
# Expected: alb_url, cluster_name, service_name
```

### 7.6 Expected Successful Outputs
| Check | Expected Result |
|-------|----------------|
| ECS cluster status | ACTIVE |
| Service running count | == desired count |
| ALB target health | All healthy |
| `curl /health` | HTTP 200 |
| Load balancing test | Multiple different hostnames |
| CloudWatch logs | No ERROR events |

### 7.7 Verification Checklist
- [ ] ECS cluster ACTIVE
- [ ] Service running count == desired count (no pending tasks)
- [ ] All ALB targets healthy
- [ ] `curl $ALB_URL/health` returns HTTP 200
- [ ] `/info` endpoint returns hostname and version
- [ ] Multiple requests show different hostnames (load balancing works)
- [ ] CloudWatch log group `/ecs/handson-flask-api` has recent events
- [ ] No ERROR lines in CloudWatch logs
- [ ] Rolling deployment completes with zero downtime
- [ ] Terraform state contains all expected resources

---

## Screenshots to Take
- [ ] ECS cluster with running service
- [ ] Task definition showing container config
- [ ] Running tasks with Fargate launch type
- [ ] ALB target group showing healthy tasks
- [ ] App responding at ALB URL
- [ ] CloudWatch logs showing container output
- [ ] Rolling deployment in progress
- [ ] Multiple hostnames from load-balanced requests
