# Project 5.5 — Verification Guide: Blue-Green Deployment

---

## Section 1: Infrastructure Verification

### 1.1 CodeDeploy Application Exists

```bash
AWS_REGION="us-east-1"

aws deploy get-application \
  --application-name my-fargate-app \
  --region $AWS_REGION \
  --query 'application.{Name:applicationName,Platform:computePlatform,CreateTime:createTime}' \
  --output table
```

Expected: `Platform = ECS`

### 1.2 Deployment Group Configured

```bash
aws deploy get-deployment-group \
  --application-name my-fargate-app \
  --deployment-group-name my-fargate-dg \
  --region $AWS_REGION \
  --query 'deploymentGroupInfo.{
    Name: deploymentGroupName,
    Style: deploymentStyle.deploymentType,
    Config: deploymentConfigName
  }' \
  --output table
```

Expected: `Style = BLUE_GREEN`

### 1.3 Both Target Groups Exist

```bash
for TG in my-fargate-tg my-fargate-tg-green; do
  aws elbv2 describe-target-groups \
    --names $TG \
    --region $AWS_REGION \
    --query "TargetGroups[0].{Name:TargetGroupName,Port:Port,Type:TargetType}" \
    --output table
done
```

Expected: Both target groups exist with port 8080 and type `ip`.

### 1.4 Both Task Definition Revisions Exist

```bash
aws ecs list-task-definitions \
  --family-prefix my-fargate-app \
  --region $AWS_REGION \
  --query 'taskDefinitionArns' \
  --output table
```

Expected: At least 2 revisions (`my-fargate-app:1` and `my-fargate-app:2`).

### 1.5 CloudWatch Alarm Configured

```bash
aws cloudwatch describe-alarms \
  --alarm-names fargate-app-5xx-alarm \
  --region $AWS_REGION \
  --query 'MetricAlarms[0].{Name:AlarmName,State:StateValue,Metric:MetricName,Threshold:Threshold}' \
  --output table
```

Expected: `Metric = HTTPCode_Target_5XX_Count`, `Threshold = 5.0`

---

## Section 2: Functionality Verification

### 2.1 Latest Deployment Succeeded

```bash
# Get latest deployment ID
DEPLOYMENT_ID=$(aws deploy list-deployments \
  --application-name my-fargate-app \
  --deployment-group-name my-fargate-dg \
  --include-only-statuses Succeeded \
  --region $AWS_REGION \
  --query 'deployments[0]' \
  --output text)

aws deploy get-deployment \
  --deployment-id $DEPLOYMENT_ID \
  --region $AWS_REGION \
  --query 'deploymentInfo.{ID:deploymentId,Status:status,Duration:deploymentOverview}' \
  --output json
```

Expected: `"status": "Succeeded"`

### 2.2 Production Traffic on Green Target Group After Deployment

```bash
ALB_ARN=$(aws elbv2 describe-load-balancers \
  --names my-fargate-alb \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text --region $AWS_REGION)

ALB_DNS=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB_ARN \
  --query 'LoadBalancers[0].DNSName' \
  --output text --region $AWS_REGION)

# Verify response shows v2
curl -s http://$ALB_DNS/ | python3 -c "import sys,json; d=json.load(sys.stdin); print('Version:', d.get('version'))"
# Expected: Version: 2.0.0
```

### 2.3 Old (Blue) Tasks Terminated After Wait Window

```bash
# After the terminationWaitTimeInMinutes has passed:
aws ecs list-tasks \
  --cluster my-fargate-cluster \
  --service-name my-fargate-service \
  --region $AWS_REGION

# Verify all running tasks use revision 2
TASK_ARNS=$(aws ecs list-tasks \
  --cluster my-fargate-cluster \
  --service-name my-fargate-service \
  --query 'taskArns' \
  --output text --region $AWS_REGION)

aws ecs describe-tasks \
  --cluster my-fargate-cluster \
  --tasks $TASK_ARNS \
  --region $AWS_REGION \
  --query 'tasks[*].{Task:taskDefinitionArn,Status:lastStatus}' \
  --output table
```

Expected: All tasks reference `my-fargate-app:2` (revision 2)

### 2.4 Green Target Group Has Healthy Targets

```bash
GREEN_TG_ARN=$(aws elbv2 describe-target-groups \
  --names my-fargate-tg-green \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text --region $AWS_REGION)

aws elbv2 describe-target-health \
  --target-group-arn $GREEN_TG_ARN \
  --region $AWS_REGION \
  --query 'TargetHealthDescriptions[*].{IP:Target.Id,Health:TargetHealth.State}' \
  --output table
```

Expected: 2 targets with `Health = healthy`

---

## Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| Deployment stuck at Step 1 | "Create replacement task set" for >10 minutes | Check ECS service events; new task likely failing to start — check CloudWatch logs for v2 tasks |
| Deployment failed, rollback triggered | Status shows "Rolled back" | Normal if alarm fired; check 5xx errors in CloudWatch during deployment; test v2 image locally first |
| Both blue and green tasks running indefinitely | No traffic shift | Check `deploymentReadyOption.actionOnTimeout` — if set to `STOP_DEPLOYMENT`, it halted at test stage |
| `InvalidRevision` error on `create-deployment` | S3 appspec.json not found | Ensure bucket name is correct and file was uploaded; check bucket region matches deployment region |
| `ECS service is not managed by CodeDeploy` | Error on deployment creation | Service was created with `ECS` (rolling) not `CODE_DEPLOY` controller; must recreate service |
