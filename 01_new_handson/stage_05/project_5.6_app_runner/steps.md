# Steps — Project 5.6 AWS App Runner Deployment

## Phase 1 — Deploy

```bash
cd terraform
terraform init
terraform apply \
  -var="ecr_image_url=$(cd ../../project_5.3_ecr/terraform && terraform output -raw ecr_url):latest" \
  -auto-approve

APP_URL=$(terraform output -raw app_runner_url)
echo "App URL: $APP_URL"
```

---

## Phase 2 — Test

```bash
# App Runner provides HTTPS automatically
curl $APP_URL/health | python3 -m json.tool
curl $APP_URL/items  | python3 -m json.tool

# Test auto-scaling (App Runner scales on demand)
# Send concurrent requests
for i in {1..20}; do curl -s $APP_URL/health & done; wait
```

---

## Phase 3 — Test Auto-deployment

```bash
# Push a new image to ECR
# App Runner detects the new image and redeploys automatically

# Build new version
cd ../../project_5.1_single_docker_app
sed -i 's/APP_VERSION = "1.0.0"/APP_VERSION = "3.0.0"/' app/app.py
docker build -t flask-api:3.0.0 .
docker tag flask-api:3.0.0 $ECR_URL:latest
docker push $ECR_URL:latest

# Watch App Runner detect and deploy the new image
aws apprunner list-operations \
  --service-arn $(cd ../project_5.6_app_runner/terraform && terraform output -raw service_arn)

# After ~2 minutes, check version
curl $APP_URL/info | python3 -m json.tool
# Should show version: 3.0.0
```

---

## Phase 4 — Compare with ECS Fargate

```bash
# App Runner:
# - URL: https://xxxxx.us-east-1.awsapprunner.com (HTTPS automatic)
# - No VPC config needed
# - No ALB to manage
# - Auto-deploys on ECR push

# ECS Fargate:
# - URL: http://alb-dns-name.us-east-1.elb.amazonaws.com (HTTP, need ACM for HTTPS)
# - Requires VPC, subnets, security groups
# - Requires ALB + target group + listener
# - Manual deployment trigger
```

---

## Phase 5 — Verification & Validation

### 5.1 AWS Console Verification
1. **App Runner** → **Services** → confirm status = Running
2. **App Runner** → **Service** → **Activity** tab → confirm deployment succeeded
3. **App Runner** → **Service** → **Metrics** tab → confirm requests flowing
4. **App Runner** → **Service** → **Configuration** → confirm auto-deploy enabled

### 5.2 CLI Verification Commands
```bash
SERVICE_ARN=$(cd terraform && terraform output -raw service_arn)

# Confirm service is running
aws apprunner describe-service --service-arn $SERVICE_ARN \
  --query "Service.{Status:Status,URL:ServiceUrl,AutoDeploy:SourceConfiguration.AutoDeploymentsEnabled}"
# Expected: Status=RUNNING, AutoDeploymentsEnabled=true

# Confirm HTTPS URL is accessible
APP_URL=$(cd terraform && terraform output -raw app_runner_url)
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $APP_URL/health)
echo "HTTPS health check: $HTTP_STATUS"
# Expected: 200

# Confirm auto-deploy is configured
aws apprunner list-operations --service-arn $SERVICE_ARN \
  --query "OperationSummaryList[:3].{Type:Type,Status:Status,StartedAt:StartedAt}" \
  --output table
# Expected: PROVISION_SERVICE operation with status=SUCCEEDED
```

### 5.3 Functional Tests
```bash
# Test 1: HTTPS works automatically (no certificate setup needed)
curl -s $APP_URL/health | python3 -m json.tool
# Expected: {"status": "ok"} over HTTPS

# Test 2: App Runner URL uses HTTPS (not HTTP)
echo $APP_URL | grep "^https://"
# Expected: URL starts with https://

# Test 3: Auto-scaling — send concurrent requests
echo "Sending 20 concurrent requests..."
for i in $(seq 1 20); do curl -s $APP_URL/health & done
wait
echo "All requests completed"
# Expected: all succeed (App Runner auto-scales)

# Test 4: Auto-deployment — push new image and verify redeployment
# Push v3 image to ECR (see Phase 3 above)
# Then poll until new version appears:
echo "Waiting for auto-deployment..."
for i in $(seq 1 30); do
  VERSION=$(curl -s $APP_URL/info 2>/dev/null | python3 -c \
    "import sys,json; print(json.load(sys.stdin).get('version','unknown'))" 2>/dev/null)
  echo "$(date +%H:%M:%S) - Version: $VERSION"
  [ "$VERSION" = "3.0.0" ] && echo "Auto-deployment complete!" && break
  sleep 10
done
# Expected: version changes to 3.0.0 within ~2 minutes

# Test 5: Compare with ECS — App Runner needs no VPC/ALB config
echo "App Runner URL: $APP_URL (HTTPS, no ALB needed)"
echo "ECS ALB URL: $(cd ../project_5.4_ecs_fargate/terraform && terraform output -raw alb_url 2>/dev/null || echo 'not deployed')"
```

### 5.4 Logs & Monitoring Checks
```bash
# Check App Runner application logs
aws apprunner list-operations --service-arn $SERVICE_ARN \
  --query "OperationSummaryList[0].{Type:Type,Status:Status}"
# Expected: latest operation SUCCEEDED

# Check CloudWatch metrics for App Runner
aws cloudwatch get-metric-statistics \
  --namespace AWS/AppRunner \
  --metric-name RequestCount \
  --dimensions Name=ServiceName,Value=$(aws apprunner describe-service \
    --service-arn $SERVICE_ARN --query "Service.ServiceName" --output text) \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 \
  --statistics Sum \
  --query "Datapoints[*].{Time:Timestamp,Requests:Sum}"
```

### 5.5 Expected Successful Outputs
| Check | Expected Result |
|-------|----------------|
| Service status | RUNNING |
| HTTPS health check | HTTP 200 |
| URL scheme | `https://` |
| Auto-deploy after ECR push | New version within 2 min |
| Concurrent requests | All succeed |

### 5.6 Verification Checklist
- [ ] App Runner service status = RUNNING
- [ ] HTTPS URL accessible (no certificate setup needed)
- [ ] `/health` returns HTTP 200 over HTTPS
- [ ] Auto-deploy enabled in service configuration
- [ ] Pushing new ECR image triggers automatic redeployment
- [ ] New version appears within ~2 minutes of ECR push
- [ ] 20 concurrent requests all succeed (auto-scaling)
- [ ] No manual VPC/ALB/SG configuration required

---

## Screenshots to Take
- [ ] App Runner service in console (Running status)
- [ ] HTTPS URL working in browser
- [ ] Auto-deployment triggered after ECR push
- [ ] App Runner metrics (requests, latency)
- [ ] Side-by-side comparison: App Runner vs ECS setup complexity
