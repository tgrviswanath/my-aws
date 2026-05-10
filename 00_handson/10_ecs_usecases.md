# ECS (Fargate) — Real-World Use Cases

## Use Case 1: Deploy a Containerized Web API

**Business Problem**: Deploy a Node.js REST API as a container on Fargate — no EC2 instances to manage, auto-scales, zero downtime deployments.

```bash
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/my-api"

# 1. Create ECR repository
aws ecr create-repository \
  --repository-name "my-api" \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256

# 2. Build and push Docker image
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $ECR_REPO

docker build -t my-api:latest .
docker tag my-api:latest $ECR_REPO:latest
docker push $ECR_REPO:latest

# 3. Create ECS cluster
aws ecs create-cluster \
  --cluster-name "production" \
  --capacity-providers FARGATE FARGATE_SPOT \
  --default-capacity-provider-strategy \
    capacityProvider=FARGATE,weight=1,base=1 \
    capacityProvider=FARGATE_SPOT,weight=4

# 4. Create task definition
aws ecs register-task-definition \
  --family "my-api" \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu 512 \
  --memory 1024 \
  --execution-role-arn arn:aws:iam::$ACCOUNT_ID:role/ecsTaskExecutionRole \
  --task-role-arn arn:aws:iam::$ACCOUNT_ID:role/my-api-task-role \
  --container-definitions "[{
    \"name\": \"my-api\",
    \"image\": \"${ECR_REPO}:latest\",
    \"portMappings\": [{\"containerPort\": 3000, \"protocol\": \"tcp\"}],
    \"environment\": [
      {\"name\": \"NODE_ENV\", \"value\": \"production\"},
      {\"name\": \"PORT\", \"value\": \"3000\"}
    ],
    \"secrets\": [
      {\"name\": \"DB_PASSWORD\", \"valueFrom\": \"arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:prod/db/password\"}
    ],
    \"logConfiguration\": {
      \"logDriver\": \"awslogs\",
      \"options\": {
        \"awslogs-group\": \"/ecs/my-api\",
        \"awslogs-region\": \"${REGION}\",
        \"awslogs-stream-prefix\": \"ecs\"
      }
    },
    \"healthCheck\": {
      \"command\": [\"CMD-SHELL\", \"curl -f http://localhost:3000/health || exit 1\"],
      \"interval\": 30,
      \"timeout\": 5,
      \"retries\": 3,
      \"startPeriod\": 60
    }
  }]"

# 5. Create ECS service with ALB
aws ecs create-service \
  --cluster "production" \
  --service-name "my-api" \
  --task-definition "my-api:1" \
  --desired-count 3 \
  --launch-type FARGATE \
  --network-configuration "{
    \"awsvpcConfiguration\": {
      \"subnets\": [\"$SUBNET_A\", \"$SUBNET_B\", \"$SUBNET_C\"],
      \"securityGroups\": [\"$SG_APP\"],
      \"assignPublicIp\": \"DISABLED\"
    }
  }" \
  --load-balancers "[{
    \"targetGroupArn\": \"$TG_ARN\",
    \"containerName\": \"my-api\",
    \"containerPort\": 3000
  }]" \
  --deployment-configuration '{
    "maximumPercent": 200,
    "minimumHealthyPercent": 100,
    "deploymentCircuitBreaker": {"enable": true, "rollback": true}
  }'

# 6. Deploy new version (rolling update)
aws ecs update-service \
  --cluster "production" \
  --service "my-api" \
  --task-definition "my-api:2" \
  --force-new-deployment

# Watch deployment
aws ecs describe-services \
  --cluster "production" \
  --services "my-api" \
  --query 'services[0].deployments'
```

**What you learn**: ECR, task definitions, Fargate networking, deployment circuit breaker, rolling updates.

---

## Use Case 2: Auto Scaling ECS Service

**Business Problem**: API gets 10x traffic during business hours. Scale from 2 to 50 tasks automatically.

```bash
# 1. Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/production/my-api \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 50

# 2. CPU-based target tracking (scale to maintain 60% CPU)
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/production/my-api \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name "cpu-tracking" \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    },
    "TargetValue": 60.0,
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'

# 3. Request count per target (scale based on ALB requests)
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/production/my-api \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name "request-count-tracking" \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ALBRequestCountPerTarget",
      "ResourceLabel": "app/prod-alb/abc123/targetgroup/my-api-tg/def456"
    },
    "TargetValue": 1000.0,
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 30
  }'

# 4. Scheduled scaling (pre-warm for business hours)
aws application-autoscaling put-scheduled-action \
  --service-namespace ecs \
  --resource-id service/production/my-api \
  --scalable-dimension ecs:service:DesiredCount \
  --scheduled-action-name "scale-up-morning" \
  --schedule "cron(0 8 * * MON-FRI *)" \
  --scalable-target-action MinCapacity=10,MaxCapacity=50

aws application-autoscaling put-scheduled-action \
  --service-namespace ecs \
  --resource-id service/production/my-api \
  --scalable-dimension ecs:service:DesiredCount \
  --scheduled-action-name "scale-down-night" \
  --schedule "cron(0 20 * * MON-FRI *)" \
  --scalable-target-action MinCapacity=2,MaxCapacity=10
```

**What you learn**: ECS auto scaling, target tracking, scheduled scaling, ALB request count metric.

---

## Use Case 3: Blue/Green Deployment with CodeDeploy

**Business Problem**: Deploy new API version with zero downtime. If errors spike, automatically roll back.

```bash
# 1. Create CodeDeploy application
aws deploy create-application \
  --application-name "my-api" \
  --compute-platform ECS

# 2. Create deployment group
aws deploy create-deployment-group \
  --application-name "my-api" \
  --deployment-group-name "production" \
  --service-role-arn arn:aws:iam::$ACCOUNT_ID:role/CodeDeployRole \
  --deployment-config-name CodeDeployDefault.ECSCanary10Percent5Minutes \
  --ecs-services clusterName=production,serviceName=my-api \
  --load-balancer-info '{
    "targetGroupPairInfoList": [{
      "targetGroups": [
        {"name": "my-api-blue-tg"},
        {"name": "my-api-green-tg"}
      ],
      "prodTrafficRoute": {
        "listenerArns": ["arn:aws:elasticloadbalancing:...:listener/prod"]
      },
      "testTrafficRoute": {
        "listenerArns": ["arn:aws:elasticloadbalancing:...:listener/test"]
      }
    }]
  }' \
  --auto-rollback-configuration '{
    "enabled": true,
    "events": ["DEPLOYMENT_FAILURE", "DEPLOYMENT_STOP_ON_ALARM"]
  }' \
  --alarm-configuration '{
    "enabled": true,
    "alarms": [{"name": "high-error-rate"}, {"name": "high-latency"}]
  }'

# 3. appspec.yaml (in your repo)
cat > appspec.yaml << 'EOF'
version: 0.0
Resources:
  - TargetService:
      Type: AWS::ECS::Service
      Properties:
        TaskDefinition: <TASK_DEFINITION>
        LoadBalancerInfo:
          ContainerName: my-api
          ContainerPort: 3000
Hooks:
  - BeforeInstall: "arn:aws:lambda:...:function:pre-deploy-check"
  - AfterAllowTestTraffic: "arn:aws:lambda:...:function:smoke-test"
  - AfterAllowTraffic: "arn:aws:lambda:...:function:post-deploy-verify"
EOF

# 4. Trigger deployment
aws deploy create-deployment \
  --application-name "my-api" \
  --deployment-group-name "production" \
  --revision '{
    "revisionType": "AppSpecContent",
    "appSpecContent": {
      "content": "'"$(cat appspec.yaml | jq -Rs .)"'"
    }
  }'

# 5. Monitor deployment
aws deploy get-deployment --deployment-id d-XXXXXXXX \
  --query 'deploymentInfo.{Status:status,Percentage:deploymentOverview}'
```

**What you learn**: Blue/green with ECS, canary traffic shifting, automatic rollback on alarms.

---

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| No health check on container | Unhealthy tasks serve traffic | Add `healthCheck` to task definition |
| Too short health check grace period | Tasks terminated during startup | Set `startPeriod` ≥ app startup time |
| Not using Fargate Spot for non-critical tasks | 4× higher cost | Mix FARGATE + FARGATE_SPOT (80/20) |
| Storing secrets in environment variables | Visible in console/logs | Use `secrets` field with Secrets Manager |
| No deployment circuit breaker | Bad deploy keeps rolling | Enable `deploymentCircuitBreaker` |
| Single AZ deployment | AZ failure = outage | Spread tasks across 3 AZs |
