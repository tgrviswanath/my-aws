# Project 5.6 — Verification Guide: AWS App Runner

---

## Section 1: Infrastructure Verification

### 1.1 App Runner Service in RUNNING State

```bash
AWS_REGION="us-east-1"

aws apprunner list-services \
  --region $AWS_REGION \
  --query 'ServiceSummaryList[?ServiceName==`flask-app-runner`].{Name:ServiceName,Status:Status,URL:ServiceUrl}' \
  --output table
```

Expected: `Status = RUNNING`

### 1.2 Service Configuration is Correct

```bash
SERVICE_ARN=$(aws apprunner list-services \
  --region $AWS_REGION \
  --query "ServiceSummaryList[?ServiceName=='flask-app-runner'].ServiceArn" \
  --output text)

aws apprunner describe-service \
  --service-arn $SERVICE_ARN \
  --region $AWS_REGION \
  --query 'Service.{
    Name: ServiceName,
    Status: Status,
    CPU: InstanceConfiguration.Cpu,
    Memory: InstanceConfiguration.Memory,
    URL: ServiceUrl
  }' \
  --output table
```

Expected: CPU=0.25 vCPU, Memory=0.5 GB, Status=RUNNING

### 1.3 Auto-Scaling Configuration Applied

```bash
aws apprunner list-auto-scaling-configurations \
  --auto-scaling-configuration-name "flask-app-scaling" \
  --region $AWS_REGION \
  --query 'AutoScalingConfigurationSummaryList[0].{Name:AutoScalingConfigurationName,Min:MinSize,Max:MaxSize}' \
  --output table
```

Expected: Min=1, Max=10

### 1.4 ECR Access Role Exists with Correct Policy

```bash
aws iam list-attached-role-policies \
  --role-name AppRunnerECRAccessRole \
  --query 'AttachedPolicies[*].PolicyName' \
  --output text
```

Expected: `AWSAppRunnerServicePolicyForECRAccess`

---

## Section 2: Functionality Verification

### 2.1 Service URL Returns HTTP 200

```bash
SERVICE_URL=$(aws apprunner describe-service \
  --service-arn $SERVICE_ARN \
  --region $AWS_REGION \
  --query 'Service.ServiceUrl' \
  --output text)

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://$SERVICE_URL/health)
echo "Health check response code: $HTTP_CODE"
# Expected: 200
```

### 2.2 HTTPS is Working

```bash
# Verify HTTPS certificate is valid
curl -v https://$SERVICE_URL/ 2>&1 | grep -E "SSL|TLS|certificate|issuer"
# Expected: valid TLS certificate from App Runner's managed CA

# Request metadata
curl -s -I https://$SERVICE_URL/ | head -10
# Expected: HTTP/2 200 with no SSL errors
```

### 2.3 Application Response Content

```bash
curl -s https://$SERVICE_URL/ | python3 -m json.tool
# Expected:
# {
#   "status": "ok",
#   "hostname": "...",
#   "version": "1.0.0"
# }
```

### 2.4 Health Check Path Configured Correctly

```bash
# Check service health check config
aws apprunner describe-service \
  --service-arn $SERVICE_ARN \
  --region $AWS_REGION \
  --query 'Service.HealthCheckConfiguration' \
  --output json
```

Expected: `"Path": "/health"`, `"Protocol": "HTTP"`

### 2.5 Deployment Succeeded (Latest Operation)

```bash
aws apprunner describe-service \
  --service-arn $SERVICE_ARN \
  --region $AWS_REGION \
  --query 'Service.{Status:Status,CreateTime:CreatedAt,UpdateTime:UpdatedAt}' \
  --output table
```

Expected: `Status = RUNNING` with recent timestamps.

---

## Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| `CREATE_FAILED` | Service fails immediately | Check `aws apprunner describe-service` for reason; common cause: ECR pull failure or health check failing at startup |
| Health check keeps failing | Service stuck in `OPERATION_IN_PROGRESS` | App not listening on configured port (8080); verify with local `docker run -p 8080:8080 <image>` |
| `Access denied` pulling from ECR | EventLog shows auth failure | Verify `AppRunnerECRAccessRole` has `AWSAppRunnerServicePolicyForECRAccess` attached and trust policy allows `build.apprunner.amazonaws.com` |
| Service URL returns 502 | After deployment completes | Container crashing at runtime; check Application logs in CloudWatch via App Runner Console |
| Auto-scaling not working | Concurrency stays at 1 | Correct behavior — scaling triggers when concurrent requests exceed maxConcurrency (25); single user won't trigger scale-out |
